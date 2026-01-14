"""
Integration tests for Flask API endpoints.

Run with: python -m pytest tests/test_api.py -v
"""

import pytest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    """Create Flask test client."""
    # Import here to avoid initialization issues
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""
    
    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get('/api/health')
        assert response.status_code == 200
    
    def test_health_has_required_fields(self, client):
        """Test health response has required fields."""
        response = client.get('/api/health')
        data = json.loads(response.data)
        
        assert 'status' in data
        assert 'version' in data
        assert 'timestamp' in data
        assert 'checks' in data
    
    def test_health_checks_present(self, client):
        """Test all health checks are present."""
        response = client.get('/api/health')
        data = json.loads(response.data)
        
        checks = data.get('checks', {})
        expected_checks = ['azure_credentials', 'blob_storage', 'policies', 'environment']
        
        for check in expected_checks:
            assert check in checks, f"Missing check: {check}"


class TestStatusEndpoint:
    """Tests for /api/status endpoint."""
    
    def test_status_returns_200(self, client):
        """Test status endpoint returns 200."""
        response = client.get('/api/status')
        assert response.status_code == 200
    
    def test_status_has_status_field(self, client):
        """Test status response has status field."""
        response = client.get('/api/status')
        data = json.loads(response.data)
        
        assert 'status' in data


class TestPoliciesEndpoint:
    """Tests for /api/policies endpoint."""
    
    def test_policies_returns_200(self, client):
        """Test policies endpoint returns 200."""
        response = client.get('/api/policies')
        assert response.status_code == 200
    
    def test_policies_returns_list(self, client):
        """Test policies endpoint returns list structure."""
        response = client.get('/api/policies')
        data = json.loads(response.data)
        
        assert 'policies' in data
        assert isinstance(data['policies'], list)


class TestPolicyValidationEndpoint:
    """Tests for /api/policies/validate endpoint."""
    
    def test_validate_valid_policy(self, client):
        """Test validation of valid policy."""
        valid_policy = {
            "name": "test-policy",
            "description": "Test policy",
            "resource": "azure.vm",
            "enabled": True,
            "filters": [{"type": "last_used", "days": 7}],
            "actions": [{"type": "stop"}]
        }
        
        response = client.post(
            '/api/policies/validate',
            data=json.dumps(valid_policy),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['valid'] == True
    
    def test_validate_missing_required_field(self, client):
        """Test validation catches missing required field."""
        invalid_policy = {
            "name": "test-policy",
            # Missing 'resource' and 'actions'
        }
        
        response = client.post(
            '/api/policies/validate',
            data=json.dumps(invalid_policy),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['valid'] == False
        assert len(data['errors']) > 0
    
    def test_validate_invalid_resource_type(self, client):
        """Test validation catches invalid resource type."""
        invalid_policy = {
            "name": "test-policy",
            "resource": "azure.invalid",
            "filters": [],
            "actions": [{"type": "stop"}]
        }
        
        response = client.post(
            '/api/policies/validate',
            data=json.dumps(invalid_policy),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['valid'] == False
        
        # Check for resource error
        resource_errors = [e for e in data['errors'] if e['field'] == 'resource']
        assert len(resource_errors) > 0
    
    def test_validate_invalid_action_type(self, client):
        """Test validation catches invalid action type."""
        invalid_policy = {
            "name": "test-policy",
            "resource": "azure.vm",
            "filters": [],
            "actions": [{"type": "explode"}]
        }
        
        response = client.post(
            '/api/policies/validate',
            data=json.dumps(invalid_policy),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['valid'] == False
    
    def test_validate_empty_body(self, client):
        """Test validation handles empty body."""
        response = client.post(
            '/api/policies/validate',
            data='{}',
            content_type='application/json'
        )
        
        assert response.status_code == 400


class TestRequestLogging:
    """Tests for request logging middleware."""
    
    def test_request_id_header_present(self, client):
        """Test X-Request-ID header is present in response."""
        response = client.get('/api/status')
        
        assert 'X-Request-ID' in response.headers
        assert len(response.headers['X-Request-ID']) == 8  # Short UUID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
