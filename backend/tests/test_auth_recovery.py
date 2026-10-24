import unittest
from fastapi.testclient import TestClient
from inner_landscape.api import create_app
import test_service as service

class AuthRestartTests(unittest.TestCase):
    def setUp(self):service.ServiceTests.setUp(self)
    def tearDown(self):service.ServiceTests.tearDown(self)
    def test_restart_rejects_old_cookie_and_root_renews_without_losing_workspace(self):
        restarted=TestClient(create_app(self.app.state.settings))
        try:
            restarted.cookies.update(self.client.cookies)
            self.assertEqual(restarted.get('/api/workspace').status_code,401)
            restarted.get('/').raise_for_status()
            response=restarted.get('/api/workspace')
            self.assertEqual(response.status_code,200)
            session=response.json()['workspace']['sessions'][0]
            self.assertEqual(session['id'],'session-test')
            self.assertEqual(session['status'],'paused')
            self.assertEqual(session['preNotes'],'PRIVATE BEFORE')
        finally:restarted.close()
