"""Build a portable reading site from the repository's existing Markdown reports.

Requires Python 3.10+ and Pandoc (or Quarto). Does not execute analyses or fetch
remote resources. Generated output belongs in _site/ and is ignored by Git.
"""
from pathlib import Path
from html import escape, unescape
from urllib.parse import urlsplit, unquote, quote
import argparse
import json
import os
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = set((ROOT / 'publication-files.txt').read_text().splitlines())
EXCLUDED = {'.git', '.venv', '.R-library', '.quarto', '__pycache__', '_site', 'site'}


def pandoc_command():
    if shutil.which('pandoc'):
        return ['pandoc']
    if shutil.which('quarto'):
        return ['quarto', 'pandoc']
    bundled = Path('/Applications/RStudio.app/Contents/Resources/app/quarto/bin/quarto')
    if bundled.is_file():
        return [str(bundled), 'pandoc']
    raise SystemExit('Install Pandoc or Quarto, then rerun this command.')


def visible(path):
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED or part.startswith('.') for part in rel.parts):
        return False
    name = rel.as_posix()
    return name in PUBLIC_FILES or (path.is_dir() and any(p.startswith(name + '/') for p in PUBLIC_FILES))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='_site', help='Output folder; must be named _site.')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    if out.name != '_site' or out == ROOT or ROOT.is_relative_to(out):
        raise SystemExit('Output must be a dedicated folder named _site, outside the source tree or at its root.')
    config = json.loads((ROOT / 'site-config.json').read_text())
    command = pandoc_command()
    sources = sorted(p for p in ROOT.rglob('*.md') if visible(p) and not p.is_relative_to(out))
    pages = {}
    for source in sources:
        rel = source.relative_to(ROOT)
        target = rel.with_name('index.html') if rel.name == 'README.md' else rel.with_suffix('.html')
        pages[source.resolve()] = out / target
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / '.nojekyll').write_text('')
    shutil.copy2(ROOT / 'site/report.css', out / 'report.css')
    directory_queue = set()
    assets = set()

    def href(target, current):
        return quote(os.path.relpath(target, current.parent).replace(os.sep, '/'), safe='/#')

    def resolve_link(url, source, current):
        parsed = urlsplit(unescape(url))
        if parsed.scheme or parsed.netloc or not parsed.path:
            return url
        target = (source.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(ROOT) or not visible(target):
            raise ValueError(f'Out-of-scope link in {source.relative_to(ROOT)}: {url}')
        # Existing rendered Quarto HTML has an equivalent Markdown reading page.
        if target.suffix == '.html' and target.with_suffix('.md') in pages:
            target = target.with_suffix('.md')
        if target in pages:
            dest = pages[target]
        elif target.is_dir():
            dest = out / '_source' / target.relative_to(ROOT) / 'index.html'
            directory_queue.add(target)
        elif target.is_file():
            dest = out / '_source' / target.relative_to(ROOT)
            if dest not in assets:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, dest)
                assets.add(dest)
        else:
            raise FileNotFoundError(f'Broken local link in {source.relative_to(ROOT)}: {url}')
        suffix = ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')
        return escape(href(dest, current) + suffix, quote=True)

    def frame(title, body, current, section_links='', source=None):
        nav = []
        for label, rel in config['nav']:
            dest = pages[(ROOT / rel).resolve()]
            active = ' aria-current="page"' if dest == current else ''
            nav.append(f'<a href="{href(dest, current)}"{active}>{escape(label)}</a>')
        repo = config.get('repository_url')
        repo_link = f'<a href="{escape(repo)}">Repository</a>' if repo else ''
        footer = 'Coursework and later portfolio revisions are credited in the project documentation.'
        return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Elias Brown</title><meta name="description" content="{escape(config['description'], quote=True)}">
<link rel="stylesheet" href="{href(out / 'report.css', current)}"></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="masthead"><a class="identity" href="https://eliasbrown.io/">ELIAS BROWN <span>Selected analytical work</span></a><div class="masthead-links"><span class="discipline">{escape(config['category'])}</span><a class="home-link" href="https://eliasbrown.io/">← Back to eliasbrown.io</a></div></header>
<div class="projectbar"><a class="projectname" href="{href(out / 'index.html', current)}">{escape(config['title'])}</a><nav class="site-nav" aria-label="Project">{''.join(nav)}{repo_link}</nav></div>
<div class="layout"><aside class="contents"><p class="eyebrow">ON THIS PAGE</p><nav aria-label="Sections">{section_links or '<a href="#main">Read the page</a>'}</nav></aside>
<main id="main"><article>{body}</article><footer><strong>Elias Brown</strong><p>{footer}</p><a href="https://eliasbrown.io/">Personal website</a> · <a href="{href(out / 'index.html', current)}">Project overview</a> · <a href="#main">Back to top ↑</a></footer></main></div></body></html>'''

    for source, current in pages.items():
        # Currency-heavy reports disable dollar-delimited math; statistics keeps equations.
        markdown_format = config.get('markdown_format', 'gfm+tex_math_dollars')
        result = subprocess.run(command + [f'--from={markdown_format}', '--to=html5', '--mathml', str(source)], text=True, capture_output=True, check=True)
        body = result.stdout
        # Repository READMEs link to this same browser edition; omit the circular link here.
        body = re.sub(r'<p><a href="https://eliasbrown99\.github\.io/[^\"]+">Read the browser report</a></p>\s*', "", body)
        body = re.sub(r'\b(href|src)="([^"]*)"', lambda m: f'{m[1]}="{resolve_link(m[2], source, current)}"', body)
        body = re.sub(r'<table>', '<div class="table-wrap" role="region" aria-label="Data table" tabindex="0"><table>', body)
        body = body.replace('</table>', '</table></div>')
        body = re.sub(r'(<div class="sourceCode"[^>]*>.*?</div>)', r'<details class="code"><summary>View code</summary>\1</details>', body, flags=re.S)
        headings = re.findall(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', body, re.S)
        links = ''.join(f'<a href="#{escape(anchor)}">{re.sub("<[^>]+>", "", label)}</a>' for anchor, label in headings)
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S)
        title = unescape(re.sub('<[^>]+>', '', title_match[1])) if title_match else source.stem
        current.parent.mkdir(parents=True, exist_ok=True)
        current.write_text(frame(title, body, current, links, source))

    done = set()
    while directory_queue - done:
        folder = sorted(directory_queue - done)[0]
        done.add(folder)
        current = out / '_source' / folder.relative_to(ROOT) / 'index.html'
        entries = []
        for item in sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if not visible(item) or item.is_relative_to(out) or item.suffix == '.pyc':
                continue
            # Directory pages expose only the selected repository contents.
            link = resolve_link(str(item.relative_to(folder)), folder / '_listing.md', current)
            label = item.name + ('/' if item.is_dir() else '')
            entries.append(f'<li><a href="{link}">{escape(label)}</a></li>')
        title = str(folder.relative_to(ROOT))
        body = f'<h1>{escape(title)}</h1><p>Source files and generated evidence for this project.</p><ul class="file-list">{"".join(entries)}</ul>'
        current.parent.mkdir(parents=True, exist_ok=True)
        current.write_text(frame(title, body, current))
    print(f'Built {len(pages)} reading pages, {len(done)} file indexes, and {len(assets)} linked files in {out}')


if __name__ == '__main__':
    main()
