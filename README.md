# Proposal Deadline Calendar

A static website for tracking proposal call deadlines from large research facilities.

## Local update

Run all scrapers and regenerate website data:

```powershell
python scripts/scrape_all.py
```

Open `index.html` in a browser to view the calendar.

## GitHub Pages deployment

1. Create a GitHub repository and push this project to the `main` branch.
2. In the repository, open `Settings` -> `Pages`.
3. Under `Build and deployment`, set `Source` to `GitHub Actions`.
4. Open the `Actions` tab and run `Update data and deploy Pages` manually once.

The workflow also runs every day at 20:00 UTC, which is 04:00 China Standard Time.

## Data update workflow

The GitHub Actions workflow:

1. Runs `python scripts/scrape_all.py`.
2. Updates files under `data/`.
3. Commits changed data files back to the repository.
4. Deploys the static site to GitHub Pages.

All DDL times shown on the site are in each facility's local time.
