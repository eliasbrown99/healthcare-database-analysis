# Browser reports

The browser edition uses the same Markdown narratives and figures as the GitHub repository. It adds navigation, a table of contents, responsive tables, and a consistent reading layout. It does not run or alter the analysis.

## Build and preview

Install Python 3.10+ and [Pandoc](https://pandoc.org/installing.html) or [Quarto](https://quarto.org/docs/get-started/). Then run from the repository root:

```bash
python3 scripts/build_portfolio_site.py
python3 -m http.server 8000 --directory _site
```

Open `http://localhost:8000`. You can also open `_site/index.html` directly. The build works without network access, reports missing local links as errors, and includes only files in `publication-files.txt`. Links to excluded files fail the build. Rebuilding replaces only the dedicated `_site` output folder.

Change the reading content in the existing Markdown files; change the presentation in `site/report.css`. The title, short description, navigation, and optional verified repository URL are in `site-config.json`. Do not invent repository or published-site addresses.

Rebuild the analytical reports using their existing commands before rebuilding the site when the underlying data or models change. The browser build converts the committed reports; it does not establish that their results are current.

## Publish with GitHub Pages

The included `Publish browser reports` workflow is **manual**. It does not publish on a push. After publication scope and repository visibility have been decided, enable GitHub Pages with **GitHub Actions** as its source, then run that workflow from the repository's Actions tab. It builds the static site from the committed reports and deploys the `_site` artifact.

GitHub Pages sites are publicly accessible under the usual Pages configuration, including when a supported private repository supplies the content. Confirm the intended audience before deployment.

After GitHub returns a working Pages address, add that verified address to the repository's About field and near the top of its README. The generated files are ignored locally; the workflow builds them for deployment.

[GitHub Pages publishing documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) · [Pandoc conversion documentation](https://pandoc.org/MANUAL.html)

## Publication file list

`publication-files.txt` lists the reviewed public files. The site builder excludes every other file, including unlinked Markdown and files in linked directories. Run `python3 scripts/check_publication_files.py` before committing or deploying. Add new public files to this list deliberately; keep personal notes in the ignored `private/` folder. The list controls publication, not analytical execution.
