#!/usr/bin/env python3
"""Send opt-in push only for changed news, after successful Pages deployment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def news_content(edition):
    # UI, image and generation-time changes must not send news alerts.
    keys = ('id', 'headline', 'summary', 'key_insights', 'impact', 'source')
    return {'date': edition['edition_date'], 'stories': {
        region: [{key: story.get(key) for key in keys} for story in edition['stories'][region]]
        for region in ('global', 'india')}}


def payload(edition, app_id, base_url):
    content = news_content(edition)
    digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).digest()[:16]
    identity = str(uuid.UUID(bytes=digest, version=4))
    count = sum(len(stories) for stories in edition['stories'].values())
    return {'app_id': app_id, 'target_channel': 'push', 'included_segments': ['Subscribed Users'],
            'headings': {'en': 'JARVIS · AI news update'},
            'contents': {'en': f"{edition['edition_date']}: {count} verified stories. Open your brief."},
            'url': base_url + 'index.html?news=' + identity,
            'idempotency_key': identity}


def main():
    config = json.loads((ROOT / 'assets/push-config.json').read_text())
    key = os.environ.get('ONESIGNAL_REST_API_KEY')
    if not config.get('appId') or not key:
        print('SKIP: device push is not configured.'); return 0
    latest = json.loads((ROOT / 'data/index.json').read_text())['latest']
    path = f'data/{latest}.json'
    edition = json.loads((ROOT / path).read_text())
    # Build exports the pre-run commit (scheduled), or first parent (push).
    previous = os.environ.get('NEWS_BASE_SHA', '')
    if not previous:
        print('SKIP: no comparison revision; refusing an unverified broadcast.'); return 0
    old = subprocess.run(['git', 'show', f'{previous}:{path}'], cwd=ROOT, capture_output=True, text=True)
    if old.returncode == 0 and news_content(json.loads(old.stdout)) == news_content(edition):
        print('SKIP: no news content changes.'); return 0
    if old.returncode != 0:
        # A missing edition is valid only when the comparison commit exists.
        subprocess.run(['git', 'cat-file', '-e', previous + '^{commit}'], cwd=ROOT, check=True, capture_output=True)
    site = json.loads((ROOT / 'scripts/config.json').read_text())['site']
    body = payload(edition, config['appId'], site['base_url'])
    request = urllib.request.Request('https://api.onesignal.com/notifications',
        data=json.dumps(body).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'Authorization': 'Key ' + key})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        if not result.get('id'):
            print('No push sent: no eligible subscribers or provider rejected delivery.'); return 1
        print('Push accepted by provider; device delivery depends on subscription and OS settings.')
        return 0
    except urllib.error.HTTPError as error:
        print(f'Push failed: provider HTTP {error.code}.'); return 1
    except urllib.error.URLError:
        print('Push failed: provider unreachable.'); return 1


if __name__ == '__main__':
    sys.exit(main())
