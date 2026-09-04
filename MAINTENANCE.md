# Profile maintenance

The profile is generated from three Markdown templates. Graphics and data live in this repository. No external image-card service, separate deployment, paid hosting, fork, or new personal access token is required.

## Choose a design

Set `design` in `profile.json` to `editorial`, `terminal`, or `workshop`, then run:

```sh
python3 scripts/update_profile.py --offline
```

Commit `profile.json`, `README.md`, and any updated files. All three alternatives remain in `designs/`. Their relative asset links work on GitHub and in the root README. Edit the matching file under `templates/` to change profile wording, since the daily job regenerates the output.

## Daily updates

`Refresh profile` runs daily at 06:23 UTC on the default branch, manually from Actions, and after source/configuration changes. It refreshes all designs in one job:

- GitHub: public repositories only, using the built-in `GITHUB_TOKEN`. Primary languages count non-fork public repositories, not bytes, private activity, or proficiency.
- WakaTime: all-time tracked editor time using the existing `WAKATIME_API_KEY` secret. Only date range, aggregate duration, and five language/category totals are saved. Project names, paths, machines, and raw API responses are not saved.
- Blog: the two latest RSS entries from the existing blog.
- Snake: both light and dark SVGs written to the paths used in the README.

A provider failure leaves the previous saved snapshot in place and creates a workflow warning. The displayed dates remain unchanged so old data is not presented as fresh. A failed snake generation restores both committed files. Static content and images remain available between runs and during provider outages.

The old `GH_TOKEN` secret is no longer used by this profile workflow. Existing artwork and 3D contribution output are retained in the repository, but the unused 3D job has been removed. The snake is tucked into a disclosure to keep the main profile focused.

GitHub may suspend scheduled workflows after prolonged inactivity in a public repository. Re-enable the workflow in Actions if needed. The existing files still render while updates are paused.

## What was fixed

- The shared stats endpoint returned HTTP 503 on 2026-09-04 UTC. The trophy endpoint returned HTTP 402. Both were replaced with repository-owned assets and useful text.
- Featured projects depended on the same failing image service. They now use native links and descriptions checked against the repositories.
- The old snake job generated `dist/github-snake*.svg` but committed `snake-output/github-contribution-grid-snake*.svg`, allowing successful runs without updating the displayed files.
- The Twitter button linked to `#`. It was omitted because no real handle was provided.
- The blog heading was inside an unclosed, nested HTML comment. It now has a normal visible heading.
- The fixed-width WakaTime code block caused horizontal scrolling. A short Markdown table replaces it.
- Heavy separators, badge stacks, duplicate headings, and the large empty stats column were removed.

## Checks

`python3 scripts/update_profile.py --offline` validates every generated README, relative image path, SVG document, unresolved template token, and prohibited dash punctuation. The generated images use plain SVG with system fonts, no scripts, external fonts, or HTML embedded inside SVG.

Source references: [GitHub README images](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files), [WakaTime API](https://wakatime.com/developers), [contribution snake](https://github.com/Platane/snk).

## Edit the design directly on GitHub

Open [profile.json in the GitHub editor](https://github.com/berniemackie97/berniemackie97/edit/main/profile.json) while signed into the account. Change only the `design` value to `editorial`, `terminal`, or `workshop`, keeping the quotation marks. Click **Commit changes**, then commit directly to `main` to update the live profile. The `Refresh profile` workflow regenerates the README automatically; no local tools are required. If you choose a new branch instead, the live profile changes after that branch is merged.

The file chooses a layout. To edit the actual words, change [templates/editorial.md](https://github.com/berniemackie97/berniemackie97/edit/main/templates/editorial.md) or the matching template for the selected design. Template changes also trigger regeneration. Avoid editing generated `README.md` directly, because the next refresh replaces it.

The refined Editorial layout uses a personal name header, full-width featured projects, and a saved WakaTime graphic. Bar lengths compare the tracked times of the top five categories, relative to the largest category. They do not represent percentages of all tracked time. Exact totals and the date range remain available as native text beneath the graphic.
