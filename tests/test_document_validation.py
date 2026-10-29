import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app_server import db
from app_server.main import Document, read_and_save_document, submit_document


class DocumentValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(db, 'DB_PATH', str(Path(self.temp.name) / 'test.db'))
        patcher.start()
        self.addCleanup(patcher.stop)
        matcher = patch('app_server.validation.slm.match_names', return_value={
            'verdict': 'uncertain', 'reason': 'Name needs review.',
        })
        self.matcher = matcher.start()
        self.addCleanup(matcher.stop)
        db.init_db()
        self.analysis = dict(document_type='salary_slip', person_name='Asha Verma', monthly_income=85000)

    def submit(self, **changes):
        return db.add_document('LOS-1001', {**self.analysis, **changes})

    def test_match_and_normalization(self):
        self.assertEqual(self.submit(person_name='  ASHA   verma ')['outcome'], 'accepted')
        self.assertIn('salary_slip', db.get_application('LOS-1001')['submitted_documents'])
        self.matcher.assert_not_called()

    def test_wrong_missing_and_partial_names_do_not_count(self):
        for name in ('Priya Das', '', None, 'A Verma', 'Verma Asha'):
            with self.subTest(name=name):
                self.assertEqual(self.submit(person_name=name)['outcome'], 'rejected')
                self.assertEqual(db.get_application('LOS-1001')['submitted_documents'], ['identity_proof'])

    def test_slm_match_accepts_variation(self):
        self.matcher.return_value = {'verdict': 'match', 'reason': 'Same full name in reversed order.'}
        result = self.submit(person_name='Verma Asha')
        self.assertEqual(result['outcome'], 'accepted')
        self.matcher.assert_called_once_with('Asha Verma', 'Verma Asha')
        self.assertEqual(result['validation_checks'][0]['comparison']['method'], 'slm')

    def test_slm_mismatch_blocks_submission(self):
        self.matcher.return_value = {'verdict': 'mismatch', 'reason': 'Different full names.'}
        self.assertEqual(self.submit(person_name='Priya Das')['outcome'], 'rejected')

    def test_missing_name_skips_slm(self):
        self.assertEqual(self.submit(person_name='')['outcome'], 'rejected')
        self.matcher.assert_not_called()

    def test_unavailable_slm_requires_review(self):
        import httpx
        for error in (httpx.ConnectError('offline'), ValueError('invalid output')):
            self.matcher.side_effect = error
            result = self.submit(person_name='A Verma')
            self.assertEqual(result['outcome'], 'rejected')
            self.assertEqual(result['validation_checks'][0]['comparison']['verdict'], 'uncertain')
            self.assertIn('salary_slip', db.get_application('LOS-1001')['missing_documents'])

    def test_slm_match_does_not_override_income(self):
        self.matcher.return_value = {'verdict': 'match', 'reason': 'Same name.'}
        self.assertEqual(self.submit(person_name='Verma Asha', monthly_income=1)['outcome'], 'rejected')

    def test_income_mismatch_or_missing_does_not_count(self):
        for income in (65000, None, 0, '85000', True):
            with self.subTest(income=income):
                self.assertEqual(self.submit(monthly_income=income)['outcome'], 'rejected')
                self.assertIn('salary_slip', db.get_application('LOS-1001')['missing_documents'])

    def test_non_salary_does_not_require_income(self):
        self.assertEqual(self.submit(document_type='bank_statement', monthly_income=None)['outcome'], 'accepted')

    def test_filename_conflict_and_neutral_filename(self):
        for filename, outcome in [('bank-statement.pdf', 'rejected'), ('salary-slip.pdf', 'accepted'), ('scan123.pdf', 'accepted')]:
            with self.subTest(filename=filename):
                with db.connect() as connection:
                    connection.execute("UPDATE applications SET submitted_documents = ? WHERE application_id = ?", ('["identity_proof"]', 'LOS-1001'))
                result = db.add_document('LOS-1001', self.analysis, filename)
                self.assertEqual(result['outcome'], outcome)

    def test_duplicate_does_not_change_checklist(self):
        self.assertEqual(self.submit()['outcome'], 'accepted')
        before = db.get_application('LOS-1001')
        result = self.submit()
        self.assertEqual(result['code'], 'duplicate_document')
        self.assertEqual(result['outcome'], 'rejected')
        self.assertEqual(db.get_application('LOS-1001'), before)

    def test_simultaneous_duplicates_only_accept_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.submit(), range(2)))
        self.assertCountEqual([r['outcome'] for r in results], ['accepted', 'rejected'])
        self.assertEqual(db.get_application('LOS-1001')['submitted_documents'].count('salary_slip'), 1)

    def test_duplicate_via_text_route(self):
        with patch('app_server.main.slm.read_document', return_value=self.analysis):
            self.assertEqual(submit_document('LOS-1001', Document(document_text='text'))['outcome'], 'accepted')
            self.assertEqual(submit_document('LOS-1001', Document(document_text='text'))['code'], 'duplicate_document')

    def test_other_application_can_submit_same_type(self):
        self.assertEqual(self.submit()['outcome'], 'accepted')
        analysis = dict(document_type='salary_slip', person_name='Priya Das', monthly_income=65000)
        self.assertEqual(db.add_document('LOS-1003', analysis)['outcome'], 'accepted')

    def test_unsupported_type(self):
        self.assertEqual(self.submit(document_type='other')['outcome'], 'rejected')

    def test_text_route_also_checks_owner(self):
        with patch('app_server.main.slm.read_document', return_value={**self.analysis, 'person_name': 'Priya Das'}):
            result = submit_document('LOS-1001', Document(document_text='synthetic text'))
        self.assertEqual(result['outcome'], 'rejected')
        self.assertIn('salary_slip', db.get_application('LOS-1001')['missing_documents'])

    def test_pipeline_passes_filename(self):
        with patch('app_server.main.slm.read_document', return_value=self.analysis):
            result = read_and_save_document('LOS-1001', 'synthetic text', 'bank-statement.pdf')
        self.assertEqual(result['outcome'], 'rejected')


if __name__ == '__main__':
    unittest.main()
