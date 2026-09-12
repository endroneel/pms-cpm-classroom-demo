from __future__ import annotations

from statistics import NormalDist

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cpm_engine import calculate_cpm, fast_cpm_metrics


st.set_page_config(
    page_title="CPM / PERT Classroom Demonstrator",
    page_icon="📊",
    layout="wide",
)


BASELINE = pd.DataFrame(
    [
        ["A", "Procure new machine", 12.0, "", 9.0],
        ["B", "Run electric lines", 10.0, "", 1.0],
        ["C", "Remove old machine", 8.0, "", 0.0],
        ["D", "Prepare mounting pad", 4.0, "C", 1.0],
        ["E", "Prepare material handling connections", 5.0, "D", 4.0],
        ["F", "Install new machine", 3.0, "A,E", 3.0],
        ["G", "Install wiring harness", 4.0, "F,B", 2.0],
        ["H", "Connect material handling", 8.0, "F", 9.0],
        ["I", "Pretest", 5.0, "G", 10.0],
        ["J", "Final test", 5.0, "H,I", 10.0],
    ],
    columns=["ID", "Activity", "Duration", "Predecessors", "Variance"],
)


SCENARIOS = {
    "Baseline lecture case": {},
    "Delay E by 2 days (5 → 7)": {"E": 7.0},
    "Extend H by 2 days (8 → 10)": {"H": 10.0},
    "Extend A by 6 days (12 → 18)": {"A": 18.0},
    "Shorten E by 2 days (5 → 3)": {"E": 3.0},
}


def fmt_num(x: float) -> str:
    if abs(float(x) - round(float(x))) < 1e-9:
        return str(int(round(float(x))))
    return f"{float(x):.2f}"


def scenario_df(name: str) -> pd.DataFrame:
    df = BASELINE.copy()
    for task_id, new_duration in SCENARIOS[name].items():
        df.loc[df["ID"] == task_id, "Duration"] = new_duration
    return df


def layered_positions(graph: nx.DiGraph):
    generations = list(nx.topological_generations(graph))
    pos = {}
    for x, generation in enumerate(generations):
        nodes = list(generation)
        n = len(nodes)
        if n == 1:
            ys = [0.0]
        else:
            ys = np.linspace((n - 1) / 2, -(n - 1) / 2, n)
        for y, node in zip(ys, nodes):
            pos[node] = (x, float(y))
    return pos


def network_figure(result, reveal=True):
    graph = result.graph
    pos = layered_positions(graph)
    table = result.table.set_index("ID")

    fig = go.Figure()

    # Non-critical and critical edges are separate traces so Plotly's default visual sequence differentiates them.
    noncritical_x, noncritical_y = [], []
    critical_x, critical_y = [], []
    for u, v in graph.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        is_critical_edge = (
            bool(table.loc[u, "Critical"])
            and bool(table.loc[v, "Critical"])
            and abs(float(table.loc[u, "EF"]) - float(table.loc[v, "ES"])) < 1e-9
        )
        target_x, target_y = (critical_x, critical_y) if is_critical_edge else (noncritical_x, noncritical_y)
        target_x.extend([x0, x1, None])
        target_y.extend([y0, y1, None])
        # Arrowhead via annotation; no explicit color set.
        fig.add_annotation(
            x=x1,
            y=y1,
            ax=x0,
            ay=y0,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2.6 if is_critical_edge else 1.2,
            opacity=0.75,
            text="",
        )

    if noncritical_x:
        fig.add_trace(
            go.Scatter(
                x=noncritical_x,
                y=noncritical_y,
                mode="lines",
                name="Other dependency",
                line=dict(width=1.3, dash="dot"),
                hoverinfo="skip",
            )
        )
    if critical_x:
        fig.add_trace(
            go.Scatter(
                x=critical_x,
                y=critical_y,
                mode="lines",
                name="Critical dependency",
                line=dict(width=3.2),
                hoverinfo="skip",
            )
        )

    for status, symbol in [(False, "circle"), (True, "diamond")]:
        subset = table[table["Critical"] == status]
        xs, ys, labels, hovers = [], [], [], []
        for node, row in subset.iterrows():
            x, y = pos[node]
            xs.append(x)
            ys.append(y)
            labels.append(f"{node}<br>{fmt_num(row['Duration'])}d")
            if reveal:
                hovers.append(
                    f"<b>{node}: {row['Activity']}</b><br>"
                    f"Duration: {fmt_num(row['Duration'])}<br>"
                    f"ES/EF: {fmt_num(row['ES'])}/{fmt_num(row['EF'])}<br>"
                    f"LS/LF: {fmt_num(row['LS'])}/{fmt_num(row['LF'])}<br>"
                    f"Slack: {fmt_num(row['Slack'])}"
                )
            else:
                hovers.append(f"<b>{node}: {row['Activity']}</b><br>Duration: {fmt_num(row['Duration'])}")
        if xs:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers+text",
                    name="Critical activity" if status else "Non-critical activity",
                    marker=dict(size=48 if status else 42, symbol=symbol, line=dict(width=1.5)),
                    text=labels,
                    textposition="middle center",
                    hovertext=hovers,
                    hoverinfo="text",
                )
            )

    fig.update_layout(
        height=520,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(orientation="h"),
        hovermode="closest",
    )
    return fig


def gantt_figure(result):
    df = result.table.copy().sort_values(["ES", "ID"], ascending=[True, True])
    df["Status"] = np.where(df["Critical"], "Critical", "Non-critical")
    fig = px.bar(
        df,
        x="Duration",
        y="ID",
        base="ES",
        color="Status",
        orientation="h",
        hover_data={
            "Activity": True,
            "ES": True,
            "EF": True,
            "LS": True,
            "LF": True,
            "Slack": True,
            "Duration": True,
        },
        labels={"Duration": "Working days", "ID": "Activity"},
    )
    fig.update_yaxes(categoryorder="array", categoryarray=list(reversed(df["ID"].tolist())))
    fig.update_layout(height=480, barmode="overlay", xaxis_title="Project day")
    return fig


def critical_path_text(result):
    if not result.critical_paths:
        return "No unique structural critical path detected."
    return " | ".join(" → ".join(p) for p in result.critical_paths)


def forward_step_text(row, result):
    node = row.name
    preds = list(result.graph.predecessors(node))
    if not preds:
        return f"{node}: no predecessors ⇒ ES = 0; EF = 0 + {fmt_num(row['Duration'])} = {fmt_num(row['EF'])}."
    pred_text = ", ".join(f"EF({p})={fmt_num(result.table.set_index('ID').loc[p, 'EF'])}" for p in preds)
    return (
        f"{node}: predecessors {', '.join(preds)} ⇒ ES = max({pred_text}) = {fmt_num(row['ES'])}; "
        f"EF = {fmt_num(row['ES'])} + {fmt_num(row['Duration'])} = {fmt_num(row['EF'])}."
    )


def backward_step_text(row, result):
    node = row.name
    succs = list(result.graph.successors(node))
    indexed = result.table.set_index("ID")
    if not succs:
        return (
            f"{node}: terminal activity ⇒ LF = project duration = {fmt_num(result.project_duration)}; "
            f"LS = {fmt_num(row['LF'])} − {fmt_num(row['Duration'])} = {fmt_num(row['LS'])}."
        )
    succ_text = ", ".join(f"LS({s})={fmt_num(indexed.loc[s, 'LS'])}" for s in succs)
    return (
        f"{node}: successors {', '.join(succs)} ⇒ LF = min({succ_text}) = {fmt_num(row['LF'])}; "
        f"LS = {fmt_num(row['LF'])} − {fmt_num(row['Duration'])} = {fmt_num(row['LS'])}."
    )


if "tasks" not in st.session_state:
    st.session_state.tasks = BASELINE.copy()
if "reveal" not in st.session_state:
    st.session_state.reveal = True

st.title("Project Management Systems: CPM / PERT Classroom Demonstrator")
st.caption("A browser-based teaching app for Activity-on-Node, forward/backward pass, slack, critical path, what-if analysis, and naïve PERT.")

with st.sidebar:
    st.header("Class controls")
    st.session_state.reveal = st.toggle("Reveal CPM solution", value=st.session_state.reveal)
    selected_scenario = st.selectbox("Load a teaching scenario", list(SCENARIOS.keys()))
    if st.button("Apply scenario", use_container_width=True):
        st.session_state.tasks = scenario_df(selected_scenario)
        st.rerun()
    if st.button("Reset to lecture baseline", use_container_width=True):
        st.session_state.tasks = BASELINE.copy()
        st.rerun()
    st.divider()
    st.markdown("**Baseline checkpoint**")
    st.markdown("Expected duration: **34 days**")
    st.markdown("Expected critical path: **C → D → E → F → G → I → J**")


setup_tab, network_tab, cpm_tab, whatif_tab, pert_tab, teach_tab = st.tabs(
    ["1. Project setup", "2. AON network", "3. CPM walkthrough", "4. What-if lab", "5. PERT & simulation", "6. Teaching plan"]
)

with setup_tab:
    st.subheader("Enter the activities, durations, and immediate predecessors")
    st.write(
        "Edit the table directly. Predecessors use activity IDs separated by commas (for example `A,E`). "
        "Variance is used only in the uncertainty tab."
    )
    edited = st.data_editor(
        st.session_state.tasks,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", required=True),
            "Activity": st.column_config.TextColumn("Activity", required=True, width="large"),
            "Duration": st.column_config.NumberColumn("Duration (days)", min_value=0.0, step=1.0, required=True),
            "Predecessors": st.column_config.TextColumn("Immediate predecessor(s)"),
            "Variance": st.column_config.NumberColumn("Variance", min_value=0.0, step=1.0),
        },
        key="task_editor",
    )
    st.session_state.tasks = edited

    try:
        result = calculate_cpm(edited)
        c1, c2, c3 = st.columns(3)
        c1.metric("Project duration", f"{fmt_num(result.project_duration)} days")
        c2.metric("Critical activities", int(result.table["Critical"].sum()))
        c3.metric("Critical path(s)", len(result.critical_paths))
        if st.session_state.reveal:
            st.success(f"Critical path: {critical_path_text(result)}")
        else:
            st.info("Prediction mode is on. Ask students to identify the critical path before revealing it.")
    except Exception as exc:
        st.error(str(exc))

with network_tab:
    st.subheader("Activity-on-Node network")
    try:
        result = calculate_cpm(st.session_state.tasks)
        st.plotly_chart(network_figure(result, reveal=st.session_state.reveal), use_container_width=True)
        st.markdown(
            "**Ask the class:** Why can A, B, and C start in parallel? Why must F wait for both A and E? "
            "Why must J wait for both H and I?"
        )
        if st.session_state.reveal:
            st.info(f"Controlling path: {critical_path_text(result)}")
    except Exception as exc:
        st.error(str(exc))

with cpm_tab:
    st.subheader("Forward pass → backward pass → slack → critical path")
    try:
        result = calculate_cpm(st.session_state.tasks)
        if st.session_state.reveal:
            display_cols = ["ID", "Activity", "Duration", "Predecessors", "ES", "EF", "LS", "LF", "Slack", "Critical"]
            display_df = result.table[display_cols].copy()
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.markdown("### Forward pass")
            indexed = result.table.set_index("ID")
            for node in result.topological_order:
                with st.expander(f"Activity {node}: {indexed.loc[node, 'Activity']}"):
                    st.write(forward_step_text(indexed.loc[node], result))

            st.markdown("### Backward pass")
            for node in reversed(result.topological_order):
                with st.expander(f"Activity {node}: {indexed.loc[node, 'Activity']}"):
                    st.write(backward_step_text(indexed.loc[node], result))

            st.markdown("### Slack and critical path")
            st.write("Total Slack = LS − ES = LF − EF. Activities with zero total slack form the controlling path(s).")
            st.success(f"Project duration = {fmt_num(result.project_duration)} days; critical path = {critical_path_text(result)}")
            st.plotly_chart(gantt_figure(result), use_container_width=True)
        else:
            st.warning("Solution is hidden. Use the project table and AON network to calculate ES, EF, LS, LF, and slack manually. Then toggle 'Reveal CPM solution'.")
            st.dataframe(
                result.table[["ID", "Activity", "Duration", "Predecessors"]],
                use_container_width=True,
                hide_index=True,
            )
    except Exception as exc:
        st.error(str(exc))

with whatif_tab:
    st.subheader("What-if laboratory: change one duration and watch the network respond")
    try:
        baseline_result = calculate_cpm(st.session_state.tasks)
        ids = baseline_result.table["ID"].tolist()
        selected = st.selectbox("Activity to change", ids, key="whatif_activity")
        old_duration = float(baseline_result.table.set_index("ID").loc[selected, "Duration"])
        new_duration = st.number_input(
            "New duration (days)",
            min_value=0.0,
            value=old_duration,
            step=1.0,
            key="whatif_duration",
        )

        trial_df = st.session_state.tasks.copy()
        trial_df.loc[trial_df["ID"].astype(str).str.upper() == selected, "Duration"] = float(new_duration)
        trial_result = calculate_cpm(trial_df)

        c1, c2, c3 = st.columns(3)
        delta = trial_result.project_duration - baseline_result.project_duration
        c1.metric("Current project duration", f"{fmt_num(baseline_result.project_duration)} days")
        c2.metric("Scenario duration", f"{fmt_num(trial_result.project_duration)} days", delta=f"{fmt_num(delta)} days")
        c3.metric("Scenario critical path", critical_path_text(trial_result))

        left, right = st.columns(2)
        with left:
            st.markdown("**Current network**")
            st.plotly_chart(network_figure(baseline_result, reveal=True), use_container_width=True, key="network_current")
        with right:
            st.markdown("**Scenario network**")
            st.plotly_chart(network_figure(trial_result, reveal=True), use_container_width=True, key="network_trial")

        if abs(delta) < 1e-9:
            st.info("The activity duration changed, but project completion did not. Ask students which slack or competing path absorbed the change.")
        elif delta > 0:
            st.warning("The project is now longer. Ask whether the changed activity consumed slack, became critical, or extended an already-critical path.")
        else:
            st.success("The project is now shorter. Ask whether a different path is becoming critical and limiting further improvement.")
    except Exception as exc:
        st.error(str(exc))

with pert_tab:
    st.subheader("Naïve PERT approximation and Monte Carlo challenge")
    st.write(
        "The lecture's naïve analysis assumes the expected-time critical path remains critical and that activity durations on that path are independent. "
        "This tab reproduces that approximation, then lets you challenge it with simulation."
    )
    try:
        result = calculate_cpm(st.session_state.tasks)
        if not result.critical_paths:
            st.error("A structural critical path is needed for the naïve PERT calculation.")
        else:
            path = result.critical_paths[0]
            indexed = result.table.set_index("ID")
            mu = float(sum(indexed.loc[n, "Duration"] for n in path))
            var = float(sum(indexed.loc[n, "Variance"] for n in path))
            sigma = var ** 0.5

            c1, c2, c3 = st.columns(3)
            c1.metric("Naïve mean", f"{mu:.2f} days")
            c2.metric("Naïve variance", f"{var:.2f}")
            c3.metric("Naïve standard deviation", f"{sigma:.3f} days")
            st.caption(f"Path used: {' → '.join(path)}")

            target = st.number_input("Target completion time (days)", min_value=0.0, value=43.0, step=1.0)
            if sigma > 0:
                probability = NormalDist(mu=mu, sigma=sigma).cdf(float(target))
                t95 = NormalDist(mu=mu, sigma=sigma).inv_cdf(0.95)
            else:
                probability = 1.0 if target >= mu else 0.0
                t95 = mu
            st.write(f"Naïve probability of completion by day {target:g}: **{probability:.2%}**")
            st.write(f"Naïve 95% completion time: **{t95:.2f} days**")

            st.divider()
            st.markdown("### Monte Carlo demonstration")
            st.caption(
                "Assumption for demonstration: each activity duration is independent Normal(mean = expected duration, variance = lecture variance), truncated at 0.1 day. "
                "This is a teaching simulation, not an assertion that real activity durations are Normal."
            )
            iterations = st.slider("Simulation iterations", 500, 10000, 3000, 500)
            seed = st.number_input("Random seed", min_value=0, value=42, step=1)
            if st.button("Run Monte Carlo", type="primary"):
                rng = np.random.default_rng(int(seed))
                nodes = result.topological_order
                means = indexed.loc[nodes, "Duration"].to_numpy(dtype=float)
                variances = indexed.loc[nodes, "Variance"].to_numpy(dtype=float)
                sds = np.sqrt(variances)

                durations_out = []
                critical_counts = {n: 0 for n in nodes}
                for _ in range(int(iterations)):
                    sampled = rng.normal(means, sds)
                    sampled = np.maximum(sampled, 0.1)
                    d = dict(zip(nodes, sampled))
                    project_time, _, _, critical = fast_cpm_metrics(result.graph, nodes, d)
                    durations_out.append(project_time)
                    for n in nodes:
                        if critical[n]:
                            critical_counts[n] += 1

                sim = np.asarray(durations_out)
                sim_prob = float(np.mean(sim <= target))
                sim_mean = float(np.mean(sim))
                sim_p95 = float(np.quantile(sim, 0.95))

                m1, m2, m3 = st.columns(3)
                m1.metric("Simulation mean", f"{sim_mean:.2f} days", delta=f"{sim_mean - mu:+.2f} vs naïve")
                m2.metric("P(finish by target)", f"{sim_prob:.2%}", delta=f"{sim_prob - probability:+.2%} vs naïve")
                m3.metric("Simulation 95th percentile", f"{sim_p95:.2f} days", delta=f"{sim_p95 - t95:+.2f} vs naïve")

                hist_df = pd.DataFrame({"Project duration": sim})
                fig = px.histogram(hist_df, x="Project duration", nbins=35)
                fig.update_layout(height=380)
                st.plotly_chart(fig, use_container_width=True)

                crit_df = pd.DataFrame(
                    {
                        "Activity": nodes,
                        "Criticality frequency": [critical_counts[n] / iterations for n in nodes],
                    }
                )
                fig2 = px.bar(crit_df, x="Activity", y="Criticality frequency")
                fig2.update_yaxes(tickformat=".0%")
                st.plotly_chart(fig2, use_container_width=True)
                st.info(
                    "Teaching point: if non-baseline activities become critical in some simulations, the assumption that one fixed critical path always controls the project is violated."
                )
    except Exception as exc:
        st.error(str(exc))

with teach_tab:
    st.subheader("Suggested 60-minute classroom flow")
    st.markdown(
        """
1. **Predict (0–10 min).** Show only activities, durations, and predecessors. Ask students to draw the AON network and predict the controlling path.
2. **Build the logic (10–20 min).** Use the AON tab to discuss parallel tasks, merge points, and why the longest completed path controls project completion.
3. **Reveal CPM (20–35 min).** Toggle *Reveal CPM solution*. Walk through ES/EF first, then LS/LF, then slack.
4. **Challenge intuition (35–50 min).** Use the What-if Lab. Recommended sequence: E 5→7, H 8→10, A 12→18, E 5→3.
5. **Introduce uncertainty (50–60 min).** Compare the naïve PERT approximation with Monte Carlo. Ask why project risk can be understated when the critical path can switch.
        """
    )
    st.markdown("### Recommended questions to ask aloud")
    st.markdown(
        """
- Why is A not critical even though F cannot start without A?
- Why does B have substantial slack even though G requires B?
- H is non-critical in the baseline. How much delay can it absorb before it changes project completion?
- If E is shortened, will the project always shorten by the same amount?
- Why can the expected completion time of a stochastic project exceed the sum of expected durations on the baseline critical path?
        """
    )
    st.markdown("### Baseline answer key")
    st.markdown("**Duration:** 34 days  \n**Critical path:** C → D → E → F → G → I → J  \n**Slack:** A=5, B=10, H=1, critical activities=0")
