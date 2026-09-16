# CPM / PERT Classroom Lab — HTML version

The browser-only app is in **[docs/index.html](docs/index.html)**. Download the repository ZIP, extract it, and open that file in a browser. It works offline with no installations.

To host it, open **Settings → Pages → Deploy from a branch**, select **main /docs**, and save. See [HTML deployment guide](docs/README.md).

## Original Streamlit version

# CPM / PERT Classroom Demonstrator

Interactive project-management teaching app with editable activities, an Activity-on-Node network, CPM forward and backward passes, slack, what-if scenarios, and PERT/Monte Carlo simulation.

## Deploy on Streamlit Community Cloud

Sign in at https://share.streamlit.io and create an app with:

- Repository: `endroneel/pms-cpm-classroom-demo`
- Branch: `main`
- Main file path: `streamlit_app.py`
- Python: 3.11

Click Deploy. No API keys or external data files are required.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Lecture checkpoint

The baseline project lasts **34 days**, with critical path **C → D → E → F → G → I → J**. Slack: A = 5, B = 10, H = 1 day.

Built-in duration scenarios: E = 7 gives 36 days; H = 10 gives 35 days; A = 18 gives 35 days; E = 3 gives 32 days.

The uncertainty demonstration assumes independent activity durations. The simulation floors Normal draws at 0.1 day; its results are illustrative.
