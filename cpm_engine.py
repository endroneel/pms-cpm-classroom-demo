from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import networkx as nx
import pandas as pd


REQUIRED_COLUMNS = ["ID", "Activity", "Duration", "Predecessors", "Variance"]


@dataclass
class CPMResult:
    table: pd.DataFrame
    graph: nx.DiGraph
    topological_order: List[str]
    project_duration: float
    critical_paths: List[List[str]]


def _normalise_id(value) -> str:
    return str(value).strip().upper()


def parse_predecessors(value) -> List[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "-"}:
        return []
    return [_normalise_id(x) for x in text.split(",") if str(x).strip()]


def validate_and_prepare(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, nx.DiGraph]:
    missing = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    df = raw_df[REQUIRED_COLUMNS].copy()
    df["ID"] = df["ID"].map(_normalise_id)
    df["Activity"] = df["Activity"].astype(str).str.strip()
    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce")
    df["Variance"] = pd.to_numeric(df["Variance"], errors="coerce").fillna(0.0)
    df["Predecessors"] = df["Predecessors"].fillna("").astype(str)

    if (df["ID"] == "").any():
        raise ValueError("Every activity must have a non-empty ID.")
    if df["ID"].duplicated().any():
        dups = df.loc[df["ID"].duplicated(keep=False), "ID"].tolist()
        raise ValueError(f"Duplicate activity ID(s): {', '.join(sorted(set(dups)))}")
    if df["Duration"].isna().any():
        bad = df.loc[df["Duration"].isna(), "ID"].tolist()
        raise ValueError(f"Duration must be numeric for: {', '.join(bad)}")
    if (df["Duration"] < 0).any():
        bad = df.loc[df["Duration"] < 0, "ID"].tolist()
        raise ValueError(f"Duration cannot be negative for: {', '.join(bad)}")
    if (df["Variance"] < 0).any():
        bad = df.loc[df["Variance"] < 0, "ID"].tolist()
        raise ValueError(f"Variance cannot be negative for: {', '.join(bad)}")

    ids = set(df["ID"])
    graph = nx.DiGraph()
    for task_id in df["ID"]:
        graph.add_node(task_id)

    parsed = {}
    for _, row in df.iterrows():
        task_id = row["ID"]
        preds = parse_predecessors(row["Predecessors"])
        parsed[task_id] = preds
        for pred in preds:
            if pred not in ids:
                raise ValueError(f"Activity {task_id} refers to unknown predecessor {pred}.")
            if pred == task_id:
                raise ValueError(f"Activity {task_id} cannot be its own predecessor.")
            graph.add_edge(pred, task_id)

    if not nx.is_directed_acyclic_graph(graph):
        try:
            cycle = nx.find_cycle(graph)
            cycle_text = " → ".join([a for a, _ in cycle] + [cycle[0][0]])
        except Exception:
            cycle_text = "a cycle"
        raise ValueError(
            "The predecessor logic contains a loop, so the classical CPM forward/backward pass "
            f"is not defined. Detected: {cycle_text}."
        )

    df["ParsedPredecessors"] = df["ID"].map(parsed)
    return df, graph


def calculate_cpm(raw_df: pd.DataFrame) -> CPMResult:
    df, graph = validate_and_prepare(raw_df)
    duration = dict(zip(df["ID"], df["Duration"].astype(float)))
    topo = list(nx.topological_sort(graph))

    es: Dict[str, float] = {}
    ef: Dict[str, float] = {}
    for node in topo:
        preds = list(graph.predecessors(node))
        es[node] = max((ef[p] for p in preds), default=0.0)
        ef[node] = es[node] + duration[node]

    terminal_nodes = [n for n in topo if graph.out_degree(n) == 0]
    project_duration = max((ef[n] for n in terminal_nodes), default=0.0)

    lf: Dict[str, float] = {}
    ls: Dict[str, float] = {}
    for node in reversed(topo):
        succs = list(graph.successors(node))
        lf[node] = min((ls[s] for s in succs), default=project_duration)
        ls[node] = lf[node] - duration[node]

    slack = {n: ls[n] - es[n] for n in topo}
    critical = {n: abs(slack[n]) < 1e-9 for n in topo}

    result = df.copy()
    result["ES"] = result["ID"].map(es)
    result["EF"] = result["ID"].map(ef)
    result["LS"] = result["ID"].map(ls)
    result["LF"] = result["ID"].map(lf)
    result["Slack"] = result["ID"].map(slack)
    result["Critical"] = result["ID"].map(critical)

    # Critical edges preserve both zero-slack status and the binding finish-to-start relation.
    critical_edges = {
        (u, v)
        for u, v in graph.edges()
        if critical[u] and critical[v] and abs(ef[u] - es[v]) < 1e-9
    }
    crit_graph = nx.DiGraph()
    crit_graph.add_nodes_from([n for n in topo if critical[n]])
    crit_graph.add_edges_from(critical_edges)

    starts = [n for n in crit_graph.nodes if crit_graph.in_degree(n) == 0 and abs(es[n]) < 1e-9]
    ends = [
        n for n in crit_graph.nodes
        if crit_graph.out_degree(n) == 0 and abs(ef[n] - project_duration) < 1e-9
    ]

    critical_paths: List[List[str]] = []
    for s in starts:
        for t in ends:
            if s == t:
                critical_paths.append([s])
            elif nx.has_path(crit_graph, s, t):
                critical_paths.extend(list(nx.all_simple_paths(crit_graph, s, t)))

    # Deduplicate while preserving order.
    seen = set()
    unique_paths = []
    for path in critical_paths:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)

    return CPMResult(
        table=result,
        graph=graph,
        topological_order=topo,
        project_duration=project_duration,
        critical_paths=unique_paths,
    )


def fast_cpm_metrics(
    graph: nx.DiGraph,
    topological_order: List[str],
    duration: Dict[str, float],
) -> Tuple[float, Dict[str, float], Dict[str, float], Dict[str, bool]]:
    """Fast CPM calculation for Monte Carlo loops."""
    es: Dict[str, float] = {}
    ef: Dict[str, float] = {}
    for node in topological_order:
        preds = list(graph.predecessors(node))
        es[node] = max((ef[p] for p in preds), default=0.0)
        ef[node] = es[node] + float(duration[node])

    terminal_nodes = [n for n in topological_order if graph.out_degree(n) == 0]
    project_duration = max(ef[n] for n in terminal_nodes)

    lf: Dict[str, float] = {}
    ls: Dict[str, float] = {}
    for node in reversed(topological_order):
        succs = list(graph.successors(node))
        lf[node] = min((ls[s] for s in succs), default=project_duration)
        ls[node] = lf[node] - float(duration[node])

    critical = {n: abs((ls[n] - es[n])) < 1e-8 for n in topological_order}
    return project_duration, es, ef, critical
