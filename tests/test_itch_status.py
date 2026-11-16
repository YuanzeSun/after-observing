import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from itch_status import channel_status


class ItchStatusChecks(unittest.TestCase):
    def setUp(self):
        self.result = {'target': 'luca-66/after-observation', 'channels': [
            {'name': name, 'head': {'id': i, 'state': 'completed', 'userVersion': '1.1'}}
            for i, name in enumerate(('windows', 'linux'), 1)]}

    def ready(self, result):
        return channel_status(result, 'luca-66/after-observation', '1.1')[0]

    def test_both_matching_completed_channels_are_required(self):
        self.assertTrue(self.ready(self.result))
        for key, value in [('state', 'processing'), ('userVersion', '1.0')]:
            result = copy.deepcopy(self.result)
            result['channels'][1]['head'][key] = value
            self.assertFalse(self.ready(result))
        self.result['channels'].pop()
        self.assertFalse(self.ready(self.result))

    def test_pending_replacement_does_not_verify_an_old_head(self):
        self.result['channels'][0]['pending'] = {'state': 'queued', 'userVersion': '1.1'}
        self.assertFalse(self.ready(self.result))

    def test_processing_failure_is_reported(self):
        self.result['channels'][1]['head']['state'] = 'failed'
        with self.assertRaises(ValueError):
            self.ready(self.result)

    def test_wrong_project_is_rejected(self):
        self.result['target'] = 'someone/else'
        with self.assertRaises(ValueError):
            self.ready(self.result)


if __name__ == '__main__':
    unittest.main()
