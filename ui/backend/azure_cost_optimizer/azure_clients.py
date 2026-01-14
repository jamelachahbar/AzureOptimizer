"""
Azure Client Manager - Centralized Azure SDK client initialization.

This module provides lazy-loaded Azure management clients with connection
validation and caching. Clients are initialized on first use to improve
startup time.

Usage:
    from azure_clients import AzureClientManager
    
    clients = AzureClientManager(subscription_id="xxx")
    compute = clients.compute  # Lazy loaded
    storage = clients.storage  # Lazy loaded
"""

import os
import logging
from functools import cached_property
from typing import Optional

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.subscription import SubscriptionClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.advisor import AdvisorManagementClient

logger = logging.getLogger(__name__)


class AzureClientManager:
    """
    Centralized manager for Azure SDK clients.
    
    Provides lazy-loaded clients that are initialized on first access.
    Supports both DefaultAzureCredential and ClientSecretCredential.
    """
    
    def __init__(
        self,
        subscription_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        credential: Optional[object] = None
    ):
        """
        Initialize the Azure Client Manager.
        
        Args:
            subscription_id: Azure subscription ID. Defaults to AZURE_SUBSCRIPTION_ID env var.
            tenant_id: Azure tenant ID. Defaults to AZURE_TENANT_ID env var.
            credential: Pre-configured credential. If not provided, uses DefaultAzureCredential.
        """
        self._subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID", "").split(",")[0]
        self._tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self._credential = credential
        self._cached_clients = {}
        
        if not self._subscription_id:
            logger.warning("No subscription ID provided. Some clients may not work.")
    
    @property
    def credential(self):
        """Get or create Azure credential."""
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential
    
    @classmethod
    def with_client_secret(cls, tenant_id: str, client_id: str = None, client_secret: str = None, subscription_id: str = None):
        """
        Create a client manager using client secret authentication.
        
        Args:
            tenant_id: Azure tenant ID
            client_id: Azure client ID. Defaults to AZURE_CLIENT_ID env var.
            client_secret: Azure client secret. Defaults to AZURE_CLIENT_SECRET env var.
            subscription_id: Azure subscription ID.
        """
        client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
        
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("tenant_id, client_id, and client_secret are required")
        
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        return cls(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            credential=credential
        )
    
    def _get_cached_client(self, name: str, factory):
        """Get or create a cached client."""
        if name not in self._cached_clients:
            logger.debug(f"Initializing {name} client")
            self._cached_clients[name] = factory()
        return self._cached_clients[name]
    
    @property
    def subscription_id(self) -> str:
        """Get the subscription ID."""
        return self._subscription_id
    
    @subscription_id.setter
    def subscription_id(self, value: str):
        """Set subscription ID and clear cached clients that depend on it."""
        if value != self._subscription_id:
            self._subscription_id = value
            # Clear subscription-dependent clients
            for key in ["resource", "compute", "storage", "network", "sql", "monitor", "advisor"]:
                self._cached_clients.pop(key, None)
    
    @property
    def resource(self) -> ResourceManagementClient:
        """Get Resource Management client."""
        return self._get_cached_client(
            "resource",
            lambda: ResourceManagementClient(self.credential, self._subscription_id)
        )
    
    @property
    def cost_management(self) -> CostManagementClient:
        """Get Cost Management client."""
        return self._get_cached_client(
            "cost_management",
            lambda: CostManagementClient(self.credential)
        )
    
    @property
    def compute(self) -> ComputeManagementClient:
        """Get Compute Management client."""
        return self._get_cached_client(
            "compute",
            lambda: ComputeManagementClient(self.credential, self._subscription_id)
        )
    
    @property
    def storage(self) -> StorageManagementClient:
        """Get Storage Management client."""
        return self._get_cached_client(
            "storage",
            lambda: StorageManagementClient(self.credential, self._subscription_id)
        )
    
    @property
    def network(self) -> NetworkManagementClient:
        """Get Network Management client."""
        return self._get_cached_client(
            "network",
            lambda: NetworkManagementClient(self.credential, self._subscription_id)
        )
    
    @property
    def sql(self) -> SqlManagementClient:
        """Get SQL Management client."""
        return self._get_cached_client(
            "sql",
            lambda: SqlManagementClient(self.credential, self._subscription_id)
        )
    
    @property
    def subscription(self) -> SubscriptionClient:
        """Get Subscription client."""
        return self._get_cached_client(
            "subscription",
            lambda: SubscriptionClient(self.credential)
        )
    
    @property
    def monitor(self) -> MonitorManagementClient:
        """Get Monitor Management client."""
        return self._get_cached_client(
            "monitor",
            lambda: MonitorManagementClient(self.credential, self._subscription_id)
        )
    
    @property
    def advisor(self) -> AdvisorManagementClient:
        """Get Advisor Management client."""
        return self._get_cached_client(
            "advisor",
            lambda: AdvisorManagementClient(self.credential, self._subscription_id)
        )
    
    def validate_connection(self) -> dict:
        """
        Validate Azure connectivity and credentials.
        
        Returns:
            dict with validation results for each check
        """
        results = {
            "credential": {"status": "unknown", "message": ""},
            "subscription": {"status": "unknown", "message": ""}
        }
        
        # Check credential
        try:
            self.credential.get_token("https://management.azure.com/.default")
            results["credential"] = {"status": "healthy", "message": "Credentials valid"}
        except Exception as e:
            results["credential"] = {"status": "unhealthy", "message": str(e)}
        
        # Check subscription access
        try:
            sub = self.subscription.subscriptions.get(self._subscription_id)
            results["subscription"] = {
                "status": "healthy",
                "message": f"Access to subscription: {sub.display_name}"
            }
        except Exception as e:
            results["subscription"] = {"status": "unhealthy", "message": str(e)}
        
        return results
    
    def clear_cache(self):
        """Clear all cached clients."""
        self._cached_clients.clear()
        logger.debug("Cleared all cached Azure clients")


# Convenience function to create a default client manager
def get_azure_clients(subscription_id: str = None) -> AzureClientManager:
    """
    Get an Azure Client Manager instance.
    
    Args:
        subscription_id: Optional subscription ID. Uses env var if not provided.
    
    Returns:
        AzureClientManager instance
    """
    return AzureClientManager(subscription_id=subscription_id)


# For backwards compatibility - global default clients
_default_manager: Optional[AzureClientManager] = None


def get_default_manager() -> AzureClientManager:
    """Get or create the default Azure Client Manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = AzureClientManager()
    return _default_manager
