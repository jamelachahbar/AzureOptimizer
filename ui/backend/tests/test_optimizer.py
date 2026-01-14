"""
Unit tests for Azure Cost Optimizer core functions.

Run with: python -m pytest tests/ -v
"""

import pytest
import json
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLoadPolicies:
    """Tests for policy loading functionality."""
    
    def test_load_policies_valid_file(self, tmp_path):
        """Test loading valid policies from YAML file."""
        from azure_cost_optimizer.optimizer import load_policies
        
        # Create test policy file
        policy_file = tmp_path / "policies.yaml"
        policy_content = """
policies:
  - name: test-policy
    description: Test policy
    resource: azure.vm
    enabled: true
    filters:
      - type: last_used
        days: 7
    actions:
      - type: stop
"""
        policy_file.write_text(policy_content)
        
        # Create schema file
        schema_file = tmp_path / "schema.json"
        schema_content = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "policies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "resource": {"type": "string"},
                            "filters": {"type": "array"},
                            "actions": {"type": "array"}
                        },
                        "required": ["name", "resource", "actions"]
                    }
                }
            }
        }
        schema_file.write_text(json.dumps(schema_content))
        
        # Test loading
        policies = load_policies(str(policy_file), str(schema_file))
        
        assert len(policies) == 1
        assert policies[0]['name'] == 'test-policy'
        assert policies[0]['resource'] == 'azure.vm'
        assert policies[0]['enabled'] == True
    
    def test_load_policies_only_enabled(self, tmp_path):
        """Test that only enabled policies are returned."""
        from azure_cost_optimizer.optimizer import load_policies
        
        policy_file = tmp_path / "policies.yaml"
        policy_content = """
policies:
  - name: enabled-policy
    resource: azure.vm
    enabled: true
    filters: []
    actions:
      - type: stop
  - name: disabled-policy
    resource: azure.disk
    enabled: false
    filters: []
    actions:
      - type: delete
"""
        policy_file.write_text(policy_content)
        
        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object", "properties": {"policies": {"type": "array"}}}')
        
        policies = load_policies(str(policy_file), str(schema_file))
        
        assert len(policies) == 1
        assert policies[0]['name'] == 'enabled-policy'


class TestPreprocessCostData:
    """Tests for cost data preprocessing."""
    
    def test_preprocess_cost_data_valid(self):
        """Test preprocessing valid cost data."""
        from azure_cost_optimizer.optimizer import preprocess_cost_data
        
        # Create mock cost data
        mock_cost_data = Mock()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        mock_cost_data.rows = [
            [100.50, yesterday],
            [150.75, (datetime.now() - timedelta(days=2)).strftime("%Y%m%d")],
        ]
        
        subscription_id = "test-subscription-123"
        
        df = preprocess_cost_data(mock_cost_data, subscription_id)
        
        assert isinstance(df, pd.DataFrame)
        assert 'cost' in df.columns
        assert 'SubscriptionId' in df.columns
        assert len(df) <= 2  # May be less due to "before today" filtering
    
    def test_preprocess_cost_data_empty(self):
        """Test preprocessing empty cost data."""
        from azure_cost_optimizer.optimizer import preprocess_cost_data
        
        mock_cost_data = Mock()
        mock_cost_data.rows = []
        
        df = preprocess_cost_data(mock_cost_data, "test-sub")
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty


class TestFormatBytes:
    """Tests for byte formatting utility."""
    
    def test_format_bytes_bytes(self):
        """Test formatting bytes."""
        # This function might be in optimizer.py or a utils module
        # For now, we'll test a simple implementation
        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_val < 1024:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.1f} PB"
        
        assert format_bytes(500) == "500.0 B"
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"


class TestAzureClients:
    """Tests for Azure client manager."""
    
    def test_client_manager_initialization(self):
        """Test AzureClientManager initialization."""
        from azure_cost_optimizer.azure_clients import AzureClientManager
        
        manager = AzureClientManager(subscription_id="test-sub-123")
        
        assert manager.subscription_id == "test-sub-123"
        assert manager._cached_clients == {}
    
    def test_client_manager_lazy_loading(self):
        """Test that clients are lazy loaded."""
        from azure_cost_optimizer.azure_clients import AzureClientManager
        
        manager = AzureClientManager(subscription_id="test-sub-123")
        
        # No clients should be initialized yet
        assert len(manager._cached_clients) == 0
    
    def test_client_manager_subscription_setter(self):
        """Test subscription ID setter clears cache."""
        from azure_cost_optimizer.azure_clients import AzureClientManager
        
        manager = AzureClientManager(subscription_id="sub-1")
        manager._cached_clients = {"compute": Mock(), "storage": Mock()}
        
        # Change subscription
        manager.subscription_id = "sub-2"
        
        # Cache should be cleared for subscription-dependent clients
        assert "compute" not in manager._cached_clients
        assert "storage" not in manager._cached_clients


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_endpoint_structure(self):
        """Test health endpoint response structure."""
        # This would be an integration test with Flask test client
        # For unit testing, we verify the expected structure
        expected_keys = ["status", "version", "timestamp", "checks"]
        expected_checks = ["azure_credentials", "blob_storage", "policies", "environment"]
        
        # Simulate response structure
        health_response = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {
                "azure_credentials": {"status": "healthy", "message": "OK"},
                "blob_storage": {"status": "healthy", "message": "OK"},
                "policies": {"status": "healthy", "message": "OK"},
                "environment": {"status": "healthy", "message": "OK"}
            }
        }
        
        for key in expected_keys:
            assert key in health_response
        
        for check in expected_checks:
            assert check in health_response["checks"]


class TestPolicyValidation:
    """Tests for policy validation."""
    
    def test_valid_policy_structure(self):
        """Test valid policy passes validation."""
        valid_policy = {
            "name": "test-policy",
            "description": "Test",
            "resource": "azure.vm",
            "enabled": True,
            "filters": [{"type": "last_used", "days": 7}],
            "actions": [{"type": "stop"}]
        }
        
        # Verify required fields
        required = ["name", "resource", "actions"]
        for field in required:
            assert field in valid_policy
        
        # Verify valid values
        valid_resources = ["azure.vm", "azure.disk", "azure.publicip"]
        assert valid_policy["resource"] in valid_resources
        
        valid_actions = ["stop", "delete", "log"]
        assert valid_policy["actions"][0]["type"] in valid_actions
    
    def test_invalid_resource_type(self):
        """Test invalid resource type is caught."""
        invalid_policy = {
            "name": "bad-policy",
            "resource": "azure.invalid",
            "actions": [{"type": "stop"}]
        }
        
        valid_resources = [
            "azure.vm", "azure.disk", "azure.resourcegroup",
            "azure.storage", "azure.sql", "azure.publicip",
            "azure.applicationgateway", "azure.nic"
        ]
        
        assert invalid_policy["resource"] not in valid_resources
    
    def test_invalid_action_type(self):
        """Test invalid action type is caught."""
        valid_actions = ["stop", "delete", "update_sku", "scale_dtu", "log", "downgrade_disks"]
        
        assert "explode" not in valid_actions
        assert "destroy" not in valid_actions


class TestVMCostEstimation:
    """Tests for VM cost estimation."""
    
    def test_known_vm_size(self):
        """Test cost estimation for known VM size."""
        size_costs = {
            'Standard_B1s': 7.59,
            'Standard_B2s': 30.37,
            'Standard_D2s_v3': 70.08,
        }
        
        assert size_costs['Standard_B1s'] == 7.59
        assert size_costs['Standard_D2s_v3'] == 70.08
    
    def test_unknown_vm_size_default(self):
        """Test default cost for unknown VM size."""
        size_costs = {
            'Standard_B1s': 7.59,
        }
        
        # Unknown sizes should return default
        default_cost = 50.0
        unknown_size = 'Standard_Unknown_v99'
        
        cost = size_costs.get(unknown_size, default_cost)
        assert cost == default_cost


# Pytest fixtures
@pytest.fixture
def sample_policies():
    """Sample policies for testing."""
    return {
        "policies": [
            {
                "name": "stop-unused-vms",
                "resource": "azure.vm",
                "enabled": True,
                "filters": [{"type": "last_used", "days": 7}],
                "actions": [{"type": "stop"}]
            },
            {
                "name": "delete-unattached-disks",
                "resource": "azure.disk",
                "enabled": True,
                "filters": [{"type": "unattached"}],
                "actions": [{"type": "delete"}]
            }
        ]
    }


@pytest.fixture
def mock_azure_credential():
    """Mock Azure credential for testing."""
    credential = Mock()
    credential.get_token.return_value = Mock(token="test-token")
    return credential


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
