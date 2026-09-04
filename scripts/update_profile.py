#!/usr/bin/env python3
"""Build the profile using Python's standard library and public repository data."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
DESIGNS = ('editorial', 'terminal', 'workshop')
PALETTES = {
    'editorial': {'dark': ('#0d1117', '#e6edf3', '#9daebb', '#65c7c3', '#263340'), 'light': ('#f5f8fa', '#162b37', '#536977', '#087b7c', '#d7e2e8')},
    'terminal': {'dark': ('#0c1412', '#e3f2e9', '#a0b6a9', '#83dba5', '#2a4035'), 'light': ('#f0f6f2', '#183127', '#526b5f', '#26784b', '#cfdfd4')},
    'workshop': {'dark': ('#191613', '#f3eadf', '#bdac99', '#e8ad71', '#40362c'), 'light': ('#fbf6ed', '#34291e', '#776653', '#99602d', '#e1d5c4')},
}

def fetch(url, authorization=None, xml=False):
    headers = {'User-Agent': 'berniemackie97-profile', 'Accept': 'application/json'}
    if authorization:
        headers['Authorization'] = authorization
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        if response.status != 200:
            raise ValueError('Data is not ready')
        body = response.read()
    return ET.fromstring(body) if xml else json.loads(body)


def github_snapshot(username):
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    auth = 'Bearer ' + token if token else None
    repos = []
    page = 1
    while True:
        batch = fetch(f'https://api.github.com/users/{username}/repos?type=owner&per_page=100&page={page}', auth)
        repos.extend(r for r in batch if not r.get('private'))
        if len(batch) < 100:
            break
        page += 1
    original = [r for r in repos if not r['fork']]
    languages = Counter(r['language'] for r in original if r.get('language'))
    return {'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'), 'repositories': len(repos),
            'original': len(original), 'languages': dict(languages.most_common()),
            'stars': sum(r['stargazers_count'] for r in repos)}


def waka_snapshot():
    key = os.environ.get('WAKATIME_API_KEY')
    if not key:
        raise ValueError('No WakaTime key in this environment')
    auth = 'Basic ' + base64.b64encode((key + ':').encode()).decode()
    data = fetch('https://api.wakatime.com/api/v1/users/current/stats/all_time', auth)['data']
    if data.get('is_up_to_date') is False or not data.get('start') or not data.get('end'):
        raise ValueError('WakaTime is still calculating the snapshot')
    def date(value):
        return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%d %b %Y')
    # Deliberately store only aggregate language totals, never project/file/machine data.
    return {'period': date(data['start']) + ' to ' + date(data['end']),
            'total': data['human_readable_total'],
            'languages': [{'name': l['name'], 'text': l['text']} for l in data['languages'][:5]]}


def blog_snapshot():
    feed = fetch('https://the-rack.vercel.app/rss.xml', xml=True)
    posts = []
    for item in feed.findall('./channel/item'):
        title, url = item.findtext('title', '').strip(), item.findtext('link', '').strip()
        parsed = urllib.parse.urlparse(url)
        if title and parsed.scheme == 'https' and parsed.hostname == 'the-rack.vercel.app':
            posts.append({'title': title, 'url': url})
        if len(posts) == 2:
            break
    if not posts:
        raise ValueError('RSS feed has no usable articles')
    return posts


def cached(name, producer, refresh):
    path = ASSETS / (name + '.json')
    if refresh:
        try:
            data = producer()
        except Exception as error:
            # Do not print exception messages that could contain an authenticated request.
            print(f'::warning::{name}: keeping the previous snapshot ({type(error).__name__})')
            if not path.exists():
                raise RuntimeError(f'No saved {name} snapshot') from None
        else:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n')
    return json.loads(path.read_text())


def text(x, y, value, size, color, weight='400', family='Arial, Helvetica, sans-serif', extra=''):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" font-family="{family}" {extra}>{html.escape(str(value))}</text>'


def svg(body, height, title, description='', width=960):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(description)}</desc>{body}</svg>\n'


def header(design, mode):
    bg, fg, muted, accent, border = PALETTES[design][mode]
    body = f'<rect width="960" height="260" rx="14" fill="{bg}"/>'
    if design == 'editorial':
        body += f'<path d="M38 36H922M38 223H922" stroke="{border}"/>'
        body += text(40, 65, 'BERNIE LORENTE', 14, accent, '700', extra='letter-spacing="3"')
        body += text(38, 139, 'Curious by default.', 58, fg, '700')
        body += text(40, 180, '.NET engineer. Reverse engineering. Emulation.', 21, muted)
        body += text(40, 245, 'CODE / GAMES / THE DETAILS IN BETWEEN', 11, muted, extra='letter-spacing="2"')
        body += f'<g fill="none" stroke="{accent}" stroke-width="2"><rect x="826" y="78" width="70" height="70" rx="8"/><rect x="847" y="99" width="70" height="70" rx="8"/></g>'
    elif design == 'terminal':
        body += f'<path d="M0 44H960" stroke="{border}"/>'
        for x in (25,43,61):
            body += f'<circle cx="{x}" cy="23" r="4" fill="{muted}"/>'
        body += text(91, 28, 'bernie / workspace', 13, muted, family='monospace')
        body += text(38, 95, '$ whoami', 19, accent, family='monospace')
        body += text(36, 154, 'Bernie Lorente', 48, fg, '700', family='monospace')
        body += text(38, 194, 'C# at work. Binaries and emulators after hours.', 19, muted, family='monospace')
        body += text(38, 234, '~/projects', 15, accent, family='monospace')
        body += f'<path d="M802 78L850 121L802 164M867 165H911" stroke="{accent}" stroke-width="7" fill="none"/>'
    else:
        body += f'<path d="M34 30V230M34 230H922" stroke="{accent}" stroke-width="2"/>'
        body += text(62, 65, 'THE WORKBENCH / BERNIE LORENTE', 13, accent, '700', extra='letter-spacing="2"')
        body += text(58, 133, 'Built out of curiosity.', 55, fg, '400', family='Georgia, serif')
        body += text(62, 181, 'Software, old games, and things worth taking apart.', 21, muted)
        body += text(62, 214, 'C# / .NET     REVERSE ENGINEERING     EMULATION', 12, muted, extra='letter-spacing="1"')
        body += f'<g fill="none" stroke="{border}" stroke-width="2"><circle cx="866" cy="78" r="32"/><path d="M822 78H910M866 34V122"/></g>'
    return svg(body, 260, 'Bernie Lorente', '.NET engineer with an interest in reverse engineering and emulation.')


def stats_card(data, design, mode):
    bg, fg, muted, accent, border = PALETTES[design][mode]
    body = f'<rect width="960" height="246" rx="12" fill="{bg}"/>'
    metrics = [(data['repositories'], 'public repos'), (data['original'], 'non-fork repos'), (len(data['languages']), 'primary languages')]
    for index, (number, label) in enumerate(metrics):
        x = 32 + index * 320
        body += text(x, 53, number, 32, fg, '700') + text(x + 62, 51, label, 16, muted)
    body += f'<path d="M32 77H928" stroke="{border}"/>'
    body += text(32, 107, 'PRIMARY LANGUAGES IN NON-FORK PUBLIC REPOS', 12, muted, '700', extra='letter-spacing="1"')
    languages = list(data['languages'].items())[:6]
    for index, (name, count) in enumerate(languages):
        x, y = 32 + (index % 3) * 320, 146 + (index // 3) * 40
        body += f'<rect x="{x}" y="{y-12}" width="3" height="16" rx="1" fill="{accent}"/>'
        body += text(x + 13, y, name, 17, fg, '700') + text(x + 180, y, f'{count} repos', 15, muted)
    body += text(32, 225, 'Public data only. Refreshed ' + data['updated'] + ' UTC.', 12, muted)
    return svg(body, 246, 'Public repository snapshot', 'Counts by repository primary language, excluding forks. Not a measure of proficiency or coding time.')


def mobile_header(design, mode):
    bg, fg, muted, accent, border = PALETTES[design][mode]
    body = f'<rect width="480" height="240" rx="12" fill="{bg}"/>'
    body += f'<path d="M24 51H456M24 214H456" stroke="{border}"/>'
    body += text(24, 33, 'BERNIE LORENTE', 14, accent, '700', extra='letter-spacing="2"')
    lines = {'editorial': ('Curious', 'by default.'), 'terminal': ('$ whoami', 'Bernie Lorente'), 'workshop': ('Built out', 'of curiosity.')}[design]
    family = 'monospace' if design == 'terminal' else 'Georgia, serif' if design == 'workshop' else 'Arial, sans-serif'
    size = 42 if design == 'terminal' else 48
    body += text(24, 111, lines[0], size, fg, '700', family)
    body += text(24, 167, lines[1], size, fg, '700', family)
    body += text(24, 199, '.NET / REVERSE ENGINEERING / EMULATION', 12, muted)
    return svg(body, 240, 'Bernie Lorente', width=480)


def mobile_stats(data, design, mode):
    bg, fg, muted, accent, border = PALETTES[design][mode]
    body = f'<rect width="480" height="348" rx="12" fill="{bg}"/>'
    for index, (number, label) in enumerate([(data['repositories'], 'public repos'), (data['original'], 'non-fork repos')]):
        x = 24 + index * 240
        body += text(x, 53, number, 34, fg, '700') + text(x, 80, label, 18, muted)
    body += f'<path d="M24 102H456" stroke="{border}"/>'
    body += text(24, 132, 'PRIMARY LANGUAGES / NON-FORK REPOS', 12, muted, '700')
    for index, (name, count) in enumerate(list(data['languages'].items())[:6]):
        x, y = 24 + (index % 2) * 240, 173 + (index // 2) * 53
        body += text(x, y, name, 21, fg, '700')
        body += text(x, y + 21, f'{count} repositories', 15, muted)
    body += text(24, 329, 'Public data / ' + data['updated'] + ' UTC', 13, muted)
    return svg(body, 348, 'Public repository snapshot', width=480)


def clean(value):
    # Escape feed/API text for Markdown and HTML, and keep profile punctuation simple.
    value = str(value).replace('\u2014', ', ').replace('\u2013', '-')
    return re.sub(r'([\\`*{}\[\]()#+!|_])', r'\\\1', html.escape(value)).replace('\n', ' ')


def render(data, waka, blog, selected):
    for design in DESIGNS:
        for mode in ('dark', 'light'):
            (ASSETS / f'header-{design}-{mode}.svg').write_text(header(design, mode))
            (ASSETS / f'header-{design}-{mode}-mobile.svg').write_text(mobile_header(design, mode))
            (ASSETS / f'stats-{design}-{mode}-mobile.svg').write_text(mobile_stats(data, design, mode))
            (ASSETS / f'stats-{design}-{mode}.svg').write_text(stats_card(data, design, mode))
    waka_md = f"**{clean(waka['total'])} tracked** · {clean(waka['period'])}\n\n| Language | Time |\n| :--- | ---: |\n"
    waka_md += '\n'.join(f"| {clean(l['name'])} | {clean(l['text'])} |" for l in waka['languages'])
    waka_md += '\n\nSource: WakaTime. Tracked editor time; the table shows the top five categories.'
    blog_md = '\n'.join(f"- [{clean(p['title'])}]({p['url']})" for p in blog)
    stat_details = ', '.join(f'{clean(n)}: {c}' for n,c in data['languages'].items())
    stat_text = f"<details>\n<summary>Snapshot details</summary>\n\nUpdated {data['updated']} UTC. {data['repositories']} public repositories, {data['original']} excluding forks, and {len(data['languages'])} primary languages.\n\n{stat_details}.\n\nEach non-fork public repository with a detected primary language is counted once. These are repository counts, not time spent or proficiency scores.\n\n</details>"
    for design in DESIGNS:
        template = (ROOT / 'templates' / f'{design}.md').read_text()
        content = template.replace('{{DESIGN}}', design).replace('{{WAKA}}', waka_md).replace('{{BLOG}}', blog_md).replace('{{STATS_TEXT}}', stat_text)
        path = ROOT / 'designs' / design / 'README.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.replace('{{ASSET}}', '../../assets').replace('{{SNAKE}}', '../../snake-output'))
        if design == selected:
            (ROOT / 'README.md').write_text(content.replace('{{ASSET}}', 'assets').replace('{{SNAKE}}', 'snake-output'))


def validate():
    for path in [ROOT/'README.md', *ROOT.glob('designs/*/README.md')]:
        content = path.read_text()
        if '{{' in content or '\u2014' in content or '\u2013' in content or 'href="#"' in content:
            raise ValueError(f'Unresolved content in {path}')
        for resource in re.findall(r'(?:src|srcset)="([^"]+)"', content):
            target = (path.parent / resource).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                raise ValueError(f'Missing local image: {resource}')
    for path in ASSETS.glob('*.svg'):
        tree = ET.parse(path)
        if any(e.tag.endswith(('script', 'foreignObject')) for e in tree.iter()):
            raise ValueError(f'Unsupported SVG in {path}')
    count = len(list(ASSETS.glob('*.svg')))
    print(f'Validated all four READMEs and {count} local SVG assets.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Render only from saved snapshots')
    args = parser.parse_args()
    config = json.loads((ROOT/'profile.json').read_text())
    if config['design'] not in DESIGNS:
        raise ValueError('Unknown design')
    data = cached('github', lambda: github_snapshot(config['username']), not args.offline)
    waka = cached('wakatime', waka_snapshot, not args.offline)
    blog = cached('blog', blog_snapshot, not args.offline)
    render(data, waka, blog, config['design'])
    validate()


if __name__ == '__main__':
    main()
