# Publish to GitHub and Host for Learn-Along Readers

Use this sequence from the project root.

## 1) Create repository and push

```bash
git add docs/index.md docs/linkedin
git commit -m "Add 14-day SOTA agentic AI learn-along publishing kit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

If the branch is not `main`:

```bash
git branch -M main
git push -u origin main
```

## 2) Enable GitHub Pages

1. Open repository `Settings` -> `Pages`.
2. Source: `Deploy from a branch`.
3. Branch: `main`.
4. Folder: `/docs`.
5. Save.

Published URL format:

`https://<github-user>.github.io/<repo>/`

## 3) Import the tracker into Google Sheets

1. Open Google Sheets -> `File` -> `Import`.
2. Upload `docs/linkedin/LINKEDIN_14_DAY_TRACKER.csv`.
3. Choose `Replace current sheet` or `Insert new sheet`.

## 4) Share Colab links for notebooks

Use this template:

`https://colab.research.google.com/github/<github-user>/<repo>/blob/main/notebooks/<notebook-name>.ipynb`

Also share the ready-to-run setup/code guide:

- `docs/linkedin/COLAB_NOTEBOOK_EXECUTION_GUIDE.md`

## 5) Suggested publishing cadence

- Post one day topic per day for 14 days.
- Add the live LinkedIn URL in the `Post_URL` column.
- Publish one weekend recap with artifacts and lessons.
