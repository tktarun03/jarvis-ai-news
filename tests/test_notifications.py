import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('notify_news', ROOT / 'scripts/notify-news.py')
notify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify)

class NotificationTest(unittest.TestCase):
    def setUp(self):
        self.ed = json.loads(next((ROOT / 'data').glob('????-??-??.json')).read_text())

    def test_cosmetic_changes_do_not_create_another_alert(self):
        other = copy.deepcopy(self.ed)
        other['generated_at'] = 'changed'
        other['stories']['global'][0]['image'] = {'src': 'changed'}
        self.assertEqual(notify.news_content(self.ed), notify.news_content(other))

    def test_same_content_retries_have_same_id(self):
        a = notify.payload(self.ed, 'test-app', 'https://example.com/')
        b = notify.payload(copy.deepcopy(self.ed), 'test-app', 'https://example.com/')
        self.assertEqual(a['idempotency_key'], b['idempotency_key'])
        self.assertEqual(a['included_segments'], ['Subscribed Users'])

    def test_corrected_news_has_new_id(self):
        other = copy.deepcopy(self.ed)
        other['stories']['global'][0]['summary'] += ' Correction.'
        a = notify.payload(self.ed, 'test-app', 'https://example.com/')
        b = notify.payload(other, 'test-app', 'https://example.com/')
        self.assertNotEqual(a['idempotency_key'], b['idempotency_key'])
