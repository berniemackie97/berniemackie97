# Editing this profile

**Edit [README.md](https://github.com/berniemackie97/berniemackie97/edit/main/README.md) directly on GitHub.** Change the words, project descriptions, links, or section order, then click **Commit changes** and commit to `main`. Your changes appear on the profile immediately.

There is one live layout. No `profile.json`, design switch, or template copying is needed.

## What updates automatically

The daily job updates the saved graphics and three clearly marked data blocks:

- `AUTO:coding-time`: WakaTime dates and language totals.
- `AUTO:github-stats`: public repository counts and the snapshot date.
- `AUTO:blog-posts`: the two latest blog links.

Leave the `<!-- AUTO:...:START -->` and `<!-- AUTO:...:END -->` comments intact. Everything outside these blocks is yours to edit, including the project grid, biography, headings, and contact links. The automation never replaces the whole README from another file.

If you accidentally remove a marker, the refresh stops with a specific error instead of rebuilding or overwriting your writing. Restoring the missing comment fixes it.

## Refresh data now

Open [Refresh profile](https://github.com/berniemackie97/berniemackie97/actions/workflows/refresh-profile.yml), select **Run workflow**, leave the branch as `main`, and run it. It also runs daily at 06:23 UTC and after README or updater changes.

Graphics stay in this repository, so no image-card hosting service, deployment, fork, or new token is required. An unavailable provider leaves the last saved data and its original date intact. The existing `WAKATIME_API_KEY` secret supplies coding totals; GitHub uses its built-in token.

The job never force-pushes. If a simultaneous edit prevents a clean merge, it stops rather than overwriting the newer change; rerun the workflow after resolving the conflict.

## What the numbers mean

- **At the keyboard:** all-time tracked WakaTime editor activity. Bars compare the five largest categories relative to the largest category. They are not percentages of all coding time.
- **Around the repos:** public repository counts. Primary-language counts exclude forks and count each repository once. They are not measures of experience or proficiency.

Only aggregate language totals are saved from WakaTime, never file paths, machine names, or private project details.

## Saved concepts

`designs/` contains the earlier design examples for reference. They do not control or overwrite the live README and are no longer refreshed. The original artwork and 3D outputs are also retained as unused assets.

## Local checks

```sh
python3 scripts/test_update_profile.py
python3 scripts/update_profile.py --offline
```

These check that refreshes preserve your personal text and layout, malformed data markers fail safely, provider outages retain saved data, images exist, and SVGs parse. Repeating an offline refresh makes no further changes.
