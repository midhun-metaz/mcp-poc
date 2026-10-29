import json
import unittest
from unittest.mock import Mock, patch

from app_server import slm


class NameMatcherTests(unittest.TestCase):
    @patch('app_server.slm.httpx.post')
    def test_request_and_structured_result(self, post):
        post.return_value = Mock()
        post.return_value.json.return_value = {'message': {'content': json.dumps({
            'verdict': 'match', 'reason': 'Same full name in reversed order.',
        })}}
        result = slm.match_names('Asha Verma', 'Verma Asha')
        self.assertEqual(result['verdict'], 'match')
        request = post.call_args.kwargs['json']
        self.assertEqual(request['model'], slm.OLLAMA_MODEL)
        self.assertEqual(request['format'], slm.NAME_MATCH_SCHEMA)
        self.assertEqual(json.loads(request['messages'][1]['content']), {
            'application_name': 'Asha Verma', 'document_name': 'Verma Asha',
        })

    @patch('app_server.slm.httpx.post')
    def test_invalid_responses_are_not_accepted(self, post):
        for output in ('not json', '[]', '{"verdict":"match"}',
                       '{"verdict":"yes","reason":"ok"}', '{"verdict":"match","reason":" "}'):
            with self.subTest(output=output):
                post.return_value.json.return_value = {'message': {'content': output}}
                with self.assertRaises(ValueError):
                    slm.match_names('Asha Verma', 'A Verma')
