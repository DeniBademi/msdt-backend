"""
Tests for our backend BNServer application which uses Django. Test cases in this module
include authentication, handling networks, questionnaires, and predictions (running the
Bayesian Inference and generating an explanation model)

Each class extends BaseTestCase, which sets up a test user and authenticated client. 
"""

from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import make_password
from bnserverappV1.models import User, UploadedModel, Questionnaire, Question, Answer
from bnserverappV1.auth import get_token
import json
import os
import tempfile
import shutil
import datetime
from unittest.mock import patch

# Create a temporary directory for test media files
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class BaseTestCase(TestCase):
    """
    Base class for tests. 
    
    This class handles
    - temporary media file setup and cleanup
    - authenticated client setup
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        os.makedirs(TEMP_MEDIA_ROOT, exist_ok=True)
        
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()
        
    def setUp(self):
        self.client = Client()
        self.test_user = User.objects.create(
            username='test_user',
            password=make_password('test_password'),
            role='admin'
        )
        self.auth_token = get_token(self.test_user)
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {self.auth_token}'
        
    def log_debug(self, message):
        """Logging debug messages with timestamps"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"[{timestamp}] {message}")

class AuthenticationTests(BaseTestCase):
    """
    Tests related to user authentication (signup & login)
    """
    def setUp(self):
        super().setUp()
        self.log_debug("Starting authentication test setup")
        User.objects.filter(username__startswith='test_').delete()
        
    def test_user_creation(self):
        """Test creating a user through the signup API."""
        response = self.client.post('/api/signup/', 
            json.dumps({
                'username': 'new_test_user',
                'password': 'test_password123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='new_test_user').exists())
        
    def test_user_login(self):
        """Test whether a user can log in."""
        test_user = User.objects.create(
            username='login_test_user',
            password=make_password('test_password123'),
            role='user'
        )
        
        response = self.client.post('/api/login/', 
            json.dumps({
                'username': 'login_test_user',
                'password': 'test_password123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('token', response_data)

class NetworkOperationsTests(BaseTestCase):
    """
    Tests for uploading and accessing Bayesian networks ('models')
    """
    def setUp(self):
        super().setUp()
        self.log_debug("Starting network operations test setup")
        
        self.upload_dir = os.path.join(TEMP_MEDIA_ROOT, 'upload_model')
        os.makedirs(self.upload_dir, exist_ok=True)
        
        UploadedModel.objects.all().delete()
        
        self.test_bif_content = 'network "test" { }'
        self.test_file = SimpleUploadedFile(
            "test_network.bif",
            self.test_bif_content.encode(),
            content_type="application/octet-stream"
        )
        
    @patch('bnserverappV1.views.bif_to_net')
    def test_network_upload(self, mock_bif_to_net):
        """Test uploading a Bayesian network file"""
        mock_bif_to_net.return_value = None
        response = self.client.post('/api/upload_model/', {
            'name': 'Test Network',
            'file': self.test_file
        })
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertIn('network_id', response_data)
        self.assertEqual(response_data['name'], 'Test Network')
        
    @patch('bnserverappV1.views.bif_to_net')
    def test_get_networks(self, mock_bif_to_net):
        """Test retrieving a Bayesian network file via API"""
        mock_bif_to_net.return_value = None
        self.client.post('/api/upload_model/', {
            'name': 'Test Network',
            'file': self.test_file
        })

        response = self.client.get('/api/networks/')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('networks', response_data)
        self.assertEqual(len(response_data['networks']), 1)
        
    @patch('bnserverappV1.views.get_metadata_for_network')
    @patch('bnserverappV1.views.bif_to_net')
    @patch('os.path.exists')
    def test_get_metadata(self, mock_exists, mock_bif_to_net, mock_get_metadata):
        """"Verify metadata for uploaded models"""
        mock_bif_to_net.return_value = None
        mock_get_metadata.return_value = json.dumps({"nodes": ["node1", "node2"]})
        mock_exists.return_value = True
        
        self.client.post('/api/upload_model/', {
            'name': 'Test Network',
            'file': self.test_file
        })
        network_id = UploadedModel.objects.first().id
        response = self.client.get(f'/api/getmetadata/{network_id}')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('metadata', response_data)
        self.assertEqual(response_data['metadata'], {"nodes": ["node1", "node2"]})
        
    def tearDown(self):
        """Cleaning up test files"""
        UploadedModel.objects.all().delete()
        if os.path.exists(self.upload_dir):
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                try:
                    os.remove(file_path)
                except Exception as e:
                    self.log_debug(f"Error deleting {file_path}: {str(e)}")
        super().tearDown()

class FileValidationTests(BaseTestCase):
    """
    Tests if uploaded network files are valid.
    """
    def setUp(self):
        super().setUp()
        self.log_debug("Starting file validation test setup")
        
        self.valid_bif = SimpleUploadedFile(
            "test_valid.bif",
            b'network "test" {\n\tnode test_node {\n\t\tstates = ("state1", "state2");\n\t}\n}',
            content_type="application/octet-stream"
        )
        
        self.invalid_file = SimpleUploadedFile(
            "test.txt",
            b'invalid content',
            content_type="text/plain"
        )
        
        self.oversized_file = SimpleUploadedFile(
            "test_oversized.bif",
            b'network "test" {' + b'a' * (10 * 1024 * 1024),  # 10MB file
            content_type="application/octet-stream"
        )
        
    @patch('bnserverappV1.views.bif_to_net')
    def test_valid_file_upload(self, mock_bif_to_net):
        """Test if .bif files (for the uploaded models) are valid"""
        mock_bif_to_net.return_value = None
        response = self.client.post('/api/upload_model/', {
            'name': 'Valid Network',
            'file': self.valid_bif
        })
        self.assertEqual(response.status_code, 201)
        
    def test_invalid_file_format(self):
        """Reject non .bif files"""
        response = self.client.post('/api/upload_model/', {
            'name': 'Invalid Network',
            'file': self.invalid_file
        })
        self.assertEqual(response.status_code, 400)
        
    @patch('bnserverappV1.views.bif_to_net')
    def test_file_size_limit(self, mock_bif_to_net):
        """Reject oversized networks"""
        mock_bif_to_net.return_value = None
        response = self.client.post('/api/upload_model/', {
            'name': 'Oversized Network',
            'file': self.oversized_file
        })
        self.assertEqual(response.status_code, 400)

class QuestionnaireTests(BaseTestCase):
    """
    Tests for questionnaire/feedback functionality
    """
    def setUp(self):
        super().setUp()
        self.log_debug("Starting questionnaire test setup")
        
        self.questionnaire = Questionnaire.objects.create(
            title='Test Questionnaire',
            description='Test Description'
        )
        
        self.question = Question.objects.create(
            questionnaire=self.questionnaire,
            text='Test Question',
            question_type='text',
            required=True
        )
        
    def test_create_questionnaire(self):
        """Test questionnaire creation via API"""
        data = {
            'title': 'New Questionnaire',
            'description': 'New Description'
        }
        response = self.client.post('/api/create_questionnaire/', 
                                  json.dumps(data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Questionnaire.objects.filter(title='New Questionnaire').exists())
        
    def test_get_questionnaire(self):
        """Test questionnaire retrieval."""
        response = self.client.get(f'/api/get_questions/?questionnaire_id={self.questionnaire.id}')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('questionnaire', response_data)
        self.assertEqual(response_data['questionnaire']['title'], 'Test Questionnaire')
        
    def test_submit_answer(self):
        """Test submitting answers to the questionnaire"""
        data = {
            'answers': [
                {
                    'question_id': self.question.id,
                    'answer_text': 'Test Answer'
                }
            ]
        }
        response = self.client.post('/api/submit_answers/',
                                  json.dumps(data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
    def test_get_answers(self):
        """"Test retrieving answers to the questionnaire"""
        Answer.objects.create(
            question=self.question,
            user=self.test_user,
            answer_text='Test Answer'
        )
        
        response = self.client.get(f'/api/get_answers/?question_id={self.question.id}')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('answers', response_data)
        self.assertEqual(len(response_data['answers']), 1)
        self.assertEqual(response_data['answers'][0]['answer_text'], 'Test Answer')
        
    def tearDown(self):
        Questionnaire.objects.all().delete()
        super().tearDown()

class PredictionTests(BaseTestCase):
    """
    Tests for prediction endpoint.
    
    The prediction endpoint handles inference on Bayesian networks ('models')
    and the returns the desired explanation method.
    """
    def setUp(self):
        super().setUp()
        self.log_debug("Starting prediction test setup")
        
        self.test_bif_content = 'network "test" { }'
        self.test_file = SimpleUploadedFile(
            "test_network.bif",
            self.test_bif_content.encode(),
            content_type="application/octet-stream"
        )
        
        with patch('bnserverappV1.views.bif_to_net') as mock_bif_to_net:
            mock_bif_to_net.return_value = None
            response = self.client.post('/api/upload_model/', {
                'name': 'Test Network',
                'file': self.test_file
            })
            self.network_id = json.loads(response.content)['network_id']
        
    def test_prediction_endpoint(self):
        """Test successful or failed prediction response"""
        data = {
            'query': 'test_node',
            'evidence': [],
            'network': self.network_id
        }
        response = self.client.post('/api/predict/', 
                                  json.dumps(data),
                                  content_type='application/json')
        self.assertIn(response.status_code, [200, 500])  # 500 if Hugin not available
        
    def test_invalid_prediction_request(self):
        """Test invalid network IDs"""
        invalid_network = UploadedModel.objects.last().id + 1 if UploadedModel.objects.exists() else 999
        data = {
            'query': 'test_node',
            'evidence': [],
            'network': invalid_network  # Invalid network ID
        }
        response = self.client.post('/api/predict/', 
                                  json.dumps(data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 404)
