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
        body = f'<rect x="1" y="1" width="958" height="242" rx="12" fill="{bg}" stroke="{border}"/>'
        body += f'<path d="M34 34V209" stroke="{accent}" stroke-width="3"/>'
        body += text(58, 61, 'C# / .NET ENGINEER', 14, accent, '700', extra='letter-spacing="2"')
        body += text(55, 131, 'Bernie Lorente', 62, fg, '700', extra='letter-spacing="-2"')
        body += text(58, 173, 'Reverse engineering, emulation, and game tooling.', 20, muted)
        body += text(58, 209, 'berniemackie97', 13, muted, family='monospace')
        # A small byte-grid motif ties the header to the binary work without a fake terminal.
        for row in range(6):
            for col in range(8):
                active = (row, col) in {(0, 1), (0, 2), (1, 1), (1, 4), (1, 5), (2, 4), (2, 5), (3, 0), (3, 3), (3, 4), (4, 0), (4, 1), (4, 6), (5, 6), (5, 7)}
                fill = accent if active else border
                body += f'<rect x="{772+col*17}" y="{57+row*20}" width="10" height="13" rx="2" fill="{fill}" opacity="{0.8 if active else 0.55}"/>'
        return svg(body, 244, 'Bernie Lorente', 'C# and .NET engineer. Reverse engineering, emulation, and game tooling.')
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
    if design == 'editorial':
        body = f'<rect x="1" y="1" width="478" height="218" rx="12" fill="{bg}" stroke="{border}"/>'
        body += f'<path d="M25 26V191" stroke="{accent}" stroke-width="3"/>'
        body += text(45, 47, 'C# / .NET ENGINEER', 15, accent, '700', extra='letter-spacing="1"')
        body += text(42, 105, 'Bernie Lorente', 44, fg, '700', extra='letter-spacing="-1"')
        body += text(45, 145, 'Reverse engineering, emulation,', 18, muted)
        body += text(45, 172, 'and game tooling.', 18, muted)
        body += text(45, 198, 'berniemackie97', 13, muted, family='monospace')
        return svg(body, 220, 'Bernie Lorente', width=480)
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


def duration_seconds(value):
    units = {'day': 86400, 'days': 86400, 'hr': 3600, 'hrs': 3600, 'hour': 3600, 'hours': 3600, 'min': 60, 'mins': 60, 'minute': 60, 'minutes': 60, 'sec': 1, 'secs': 1, 'second': 1, 'seconds': 1}
    return sum(float(number) * units[unit] for number, unit in re.findall(r'(\d+(?:\.\d+)?)\s+(days?|hrs?|hours?|mins?|minutes?|secs?|seconds?)\b', value))


def coding_card(waka, mode, mobile=False):
    bg, fg, muted, accent, border = PALETTES['editorial'][mode]
    width, height = (480, 434) if mobile else (960, 260)
    body = f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="12" fill="{bg}" stroke="{border}"/>'
    total = waka['total'].replace(' hrs', 'h').replace(' hr', 'h').replace(' mins', 'm').replace(' min', 'm')
    body += text(26 if mobile else 30, 34 if mobile else 43, 'TRACKED CODING TIME', 13, muted, '700', extra='letter-spacing="1"')
    body += text(26 if mobile else 28, 89 if mobile else 119, total, 42 if mobile else 46, fg, '700', extra='letter-spacing="-1"')
    body += text(26 if mobile else 30, 119 if mobile else 153, waka['period'], 15 if mobile else 14, muted)
    if mobile:
        body += f'<path d="M26 140H454" stroke="{border}"/>'
    else:
        body += text(30, 207, 'WakaTime / top five categories', 13, muted)
        body += text(30, 229, 'Bars show relative tracked time.', 12, muted)
    languages = waka['languages'][:5]
    times = [duration_seconds(l['text']) for l in languages]
    maximum = max(times, default=0) or 1
    for i, (language, seconds) in enumerate(zip(languages, times)):
        x, y, available = (26, 173+i*48, 428) if mobile else (450, 36+i*47, 478)
        body += text(x, y, language['name'], 19 if mobile else 16, fg, '700')
        label = language['text'].replace(' hrs', 'h').replace(' hr', 'h').replace(' mins', 'm').replace(' min', 'm')
        body += text(x+available, y, label, 16 if mobile else 14, muted, extra='text-anchor="end"')
        body += f'<rect x="{x}" y="{y+10}" width="{available}" height="5" rx="2.5" fill="{border}"/>'
        body += f'<rect x="{x}" y="{y+10}" width="{available*seconds/maximum:.2f}" height="5" rx="2.5" fill="{accent}"/>'
    if mobile:
        body += text(26, 416, 'WakaTime / top five categories / relative time', 13, muted)
    return svg(body, height, 'Tracked coding time', 'WakaTime totals for ' + waka['period'] + '. Bars compare the tracked time of the top five categories.', width=width)


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
    for mode in ('dark', 'light'):
        (ASSETS / f'coding-editorial-{mode}.svg').write_text(coding_card(waka, mode))
        (ASSETS / f'coding-editorial-{mode}-mobile.svg').write_text(coding_card(waka, mode, mobile=True))
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
