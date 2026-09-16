# CPM / PERT HTML Classroom Lab

Open `index.html` in a modern browser. This standalone file works offline, with no Python, Streamlit, npm, CDN, or installation.

## Publish on GitHub Pages

In `endroneel/pms-cpm-classroom-demo`, open Settings → Pages. Under Build and deployment, choose **Deploy from a branch**, then **main** and **/docs**, and click Save.

Once GitHub reports deployment success, the expected address is:
https://endroneel.github.io/pms-cpm-classroom-demo/

Uploading these files alone does not enable GitHub Pages. The repository owner must select the publishing source.

## Classroom features

- Editable activities, durations, predecessor relationships and variances; add/remove activities.
- AON network, critical paths, ES/EF/LS/LF, slack, forward/backward explanations and earliest-start schedule.
- Reveal switch hides answers across the lab, including network styling and teaching answer key.
- Four lecture scenarios and a one-activity what-if comparison.
- Fixed-path Normal PERT approximation and seeded Monte Carlo, with a histogram and criticality frequencies.
- Save/open project JSON files. Changes remain in memory until the page closes; save before closing.

Baseline: 34 days; critical path C–D–E–F–G–I–J; slack A=5, B=10, H=1. Duration scenarios E=7, H=10, A=18 and E=3 give 36, 35, 35 and 32 days respectively.

Maximum 100 activities. Display of critical paths is capped at 100. Simulation assumes independent Normal durations floored at 0.1 day. Multiple critical paths make the single-path PERT approximation less informative; the app states which path it uses.
