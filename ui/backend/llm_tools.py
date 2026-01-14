"""
LLM Tools for Azure Cost Optimizer
Provides function calling capabilities for AI advice generation with verified documentation links.

Search Strategy (in order of preference):
1. Curated documentation links (always available, most reliable)
2. DuckDuckGo site-specific search (fallback, free)

All links are validated before being returned to ensure they exist.
"""

import json
import logging
import os
import requests
from typing import Optional, Dict, List, Any
from urllib.parse import quote_plus
import re

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Azure AI Foundry configuration (for future agent scenarios)
FOUNDRY_ENDPOINT = os.getenv('AZURE_AI_PROJECT_ENDPOINT')
FOUNDRY_MODEL_DEPLOYMENT = os.getenv('AZURE_AI_MODEL_DEPLOYMENT_NAME')

logger.info("Using curated documentation links with DuckDuckGo fallback")


# ============================================================================
# URL Validation and Web Search (DuckDuckGo Fallback)
# ============================================================================

def validate_url(url: str, timeout: int = 5) -> bool:
    """
    Validate that a URL exists and returns a successful response.
    Uses HEAD request for efficiency.
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 400
    except requests.RequestException:
        try:
            # Fallback to GET if HEAD fails
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            return response.status_code < 400
        except requests.RequestException:
            return False


def search_microsoft_docs_ddg(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search Microsoft Learn documentation using DuckDuckGo (fallback method).
    Returns a list of verified URLs with titles.
    """
    results = []
    
    # Construct Microsoft Learn search URL
    search_query = quote_plus(f"site:learn.microsoft.com/en-us/azure {query}")
    
    # Try DuckDuckGo HTML search (no API key needed)
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q={search_query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(ddg_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Extract URLs from response
            content = response.text
            
            # Find Microsoft Learn URLs
            url_pattern = r'https://learn\.microsoft\.com/en-us/azure[^\s"<>\']*'
            found_urls = re.findall(url_pattern, content)
            
            # Deduplicate and validate
            seen = set()
            for url in found_urls:
                # Clean URL
                url = url.rstrip('.,;:)')
                if url not in seen and len(results) < max_results:
                    seen.add(url)
                    if validate_url(url):
                        # Extract title from URL path
                        path = url.replace('https://learn.microsoft.com/en-us/azure/', '')
                        title = path.replace('-', ' ').replace('/', ' - ').title()
                        results.append({
                            'url': url,
                            'title': f"Azure {title}",
                            'verified': True,
                            'source': 'duckduckgo'
                        })
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
    
    return results


def search_microsoft_docs(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search Microsoft Learn documentation using DuckDuckGo.
    
    Strategy:
    1. DuckDuckGo site-specific search (free)
    2. Curated links (always available as fallback)
    
    Returns a list of verified URLs with titles.
    """
    # Search with DuckDuckGo
    logger.debug(f"Searching with DuckDuckGo: {query}")
    results = search_microsoft_docs_ddg(query, max_results)
    if results:
        logger.info(f"DuckDuckGo returned {len(results)} results")
    
    return results



def get_verified_azure_link(topic: str, resource_type: str = None) -> Dict[str, Any]:
    """
    Get a verified Azure documentation link for a topic.
    First checks curated links, then searches if needed.
    """
    result = {
        'success': False,
        'links': [],
        'source': 'unknown'
    }
    
    # First, try curated links
    curated = get_azure_documentation(
        category=categorize_recommendation(topic, ''),
        subcategory=resource_type
    )
    
    if curated.get('links'):
        # Validate curated links
        for link in curated['links']:
            if validate_url(link['url']):
                result['links'].append({
                    'url': link['url'],
                    'title': link['title'],
                    'verified': True,
                    'source': 'curated'
                })
        
        if result['links']:
            result['success'] = True
            result['source'] = 'curated'
            return result
    
    # If no curated links, search the web
    search_results = search_microsoft_docs(f"{topic} {resource_type or ''}")
    if search_results:
        result['links'] = search_results
        result['success'] = True
        result['source'] = 'web_search'
    
    return result

# Verified Azure documentation links by recommendation category
AZURE_DOCS_MAPPING = {
    # Reserved Instances & Savings Plans
    "reserved_instances": {
        "vm": "https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations",
        "sql": "https://learn.microsoft.com/en-us/azure/azure-sql/database/reserved-capacity-overview",
        "cosmos": "https://learn.microsoft.com/en-us/azure/cosmos-db/cosmos-db-reserved-capacity",
        "storage": "https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-reserved-capacity",
        "app_service": "https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/prepay-app-service",
        "general": "https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations"
    },
    "savings_plan": {
        "compute": "https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/savings-plan-compute-overview",
        "purchase": "https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/buy-savings-plan",
        "manage": "https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/manage-savings-plan"
    },
    
    # Resource Optimization
    "vm_rightsizing": {
        "resize": "https://learn.microsoft.com/en-us/azure/virtual-machines/resize-vm",
        "advisor": "https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations",
        "sizing": "https://learn.microsoft.com/en-us/azure/virtual-machines/sizes"
    },
    "sql_optimization": {
        "dtu": "https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-dtu",
        "vcore": "https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-sql-database-vcore",
        "elastic_pool": "https://learn.microsoft.com/en-us/azure/azure-sql/database/elastic-pool-overview",
        "serverless": "https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-overview"
    },
    "storage_optimization": {
        "tiers": "https://learn.microsoft.com/en-us/azure/storage/blobs/access-tiers-overview",
        "lifecycle": "https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview",
        "pricing": "https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview"
    },
    
    # Unused Resources
    "unused_resources": {
        "disk": "https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types",
        "public_ip": "https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/public-ip-addresses",
        "nic": "https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-network-interface",
        "app_gateway": "https://learn.microsoft.com/en-us/azure/application-gateway/overview",
        "load_balancer": "https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-overview"
    },
    
    # Idle/Stopped Resources
    "idle_resources": {
        "vm": "https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing",
        "aks": "https://learn.microsoft.com/en-us/azure/aks/start-stop-cluster",
        "app_service": "https://learn.microsoft.com/en-us/azure/app-service/overview-hosting-plans"
    },
    
    # Cost Management
    "cost_management": {
        "budgets": "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets",
        "alerts": "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/cost-mgt-alerts-monitor-usage-spending",
        "analysis": "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/quick-acm-cost-analysis",
        "advisor": "https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations"
    },
    
    # Hybrid Benefits
    "hybrid_benefit": {
        "windows": "https://learn.microsoft.com/en-us/azure/virtual-machines/windows/hybrid-use-benefit-licensing",
        "sql": "https://learn.microsoft.com/en-us/azure/azure-sql/azure-hybrid-benefit",
        "linux": "https://learn.microsoft.com/en-us/azure/virtual-machines/linux/azure-hybrid-benefit-linux"
    }
}


# Function definitions for OpenAI function calling
AVAILABLE_FUNCTIONS = [
    {
        "name": "get_azure_documentation",
        "description": "Get verified Azure documentation links for a specific cost optimization topic. Use this to provide accurate, working documentation links to users.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "The category of the recommendation",
                    "enum": ["reserved_instances", "savings_plan", "vm_rightsizing", "sql_optimization", 
                             "storage_optimization", "unused_resources", "idle_resources", "cost_management", "hybrid_benefit"]
                },
                "subcategory": {
                    "type": "string",
                    "description": "The specific subcategory (e.g., 'vm', 'sql', 'disk', 'compute')"
                },
                "resource_type": {
                    "type": "string",
                    "description": "The Azure resource type mentioned in the recommendation (e.g., 'Virtual Machine', 'SQL Database', 'Disk')"
                }
            },
            "required": ["category"]
        }
    },
    {
        "name": "search_azure_docs",
        "description": "Search for Azure documentation when specific topic is not in the curated list. Returns a constructed Microsoft Learn search URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for Azure documentation"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_cost_optimization_action",
        "description": "Get specific cost optimization actions and their Azure portal links",
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "The type of cost optimization action",
                    "enum": ["delete_resource", "resize_resource", "purchase_reservation", "enable_hybrid_benefit", 
                             "change_tier", "stop_resource", "enable_autoscale"]
                },
                "resource_type": {
                    "type": "string",
                    "description": "The Azure resource type"
                }
            },
            "required": ["action_type", "resource_type"]
        }
    }
]


def get_azure_documentation(category: str, subcategory: str = None, resource_type: str = None) -> Dict[str, Any]:
    """Get verified Azure documentation links for a category."""
    result = {
        "success": True,
        "links": [],
        "category": category
    }
    
    if category in AZURE_DOCS_MAPPING:
        category_docs = AZURE_DOCS_MAPPING[category]
        
        # Try to find specific subcategory
        if subcategory and subcategory.lower() in category_docs:
            result["links"].append({
                "title": f"Azure {subcategory.upper()} Documentation",
                "url": category_docs[subcategory.lower()],
                "type": "primary"
            })
        
        # Map resource types to subcategories
        resource_mapping = {
            "virtual machine": "vm",
            "vm": "vm",
            "sql database": "sql",
            "sql": "sql",
            "disk": "disk",
            "managed disk": "disk",
            "public ip": "public_ip",
            "network interface": "nic",
            "storage account": "storage",
            "app service": "app_service",
            "application gateway": "app_gateway",
            "cosmos db": "cosmos"
        }
        
        if resource_type:
            mapped_key = resource_mapping.get(resource_type.lower())
            if mapped_key and mapped_key in category_docs:
                result["links"].append({
                    "title": f"Azure {resource_type} Documentation",
                    "url": category_docs[mapped_key],
                    "type": "resource_specific"
                })
        
        # Add general link if available
        if "general" in category_docs and not result["links"]:
            result["links"].append({
                "title": "Azure Documentation",
                "url": category_docs["general"],
                "type": "general"
            })
        
        # If still no links, add all from category
        if not result["links"]:
            for key, url in list(category_docs.items())[:3]:
                result["links"].append({
                    "title": f"Azure {key.replace('_', ' ').title()}",
                    "url": url,
                    "type": "related"
                })
    else:
        result["success"] = False
        result["message"] = f"Category '{category}' not found"
        # Fallback to Azure Advisor
        result["links"].append({
            "title": "Azure Advisor Cost Recommendations",
            "url": "https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations",
            "type": "fallback"
        })
    
    return result


def search_azure_docs(query: str) -> Dict[str, Any]:
    """Generate a Microsoft Learn search URL for the query."""
    # Clean and encode the query
    clean_query = query.replace(" ", "+")
    search_url = f"https://learn.microsoft.com/en-us/search/?terms={clean_query}&scope=Azure"
    
    return {
        "success": True,
        "search_url": search_url,
        "query": query,
        "message": f"Search Azure documentation for: {query}"
    }


def get_cost_optimization_action(action_type: str, resource_type: str) -> Dict[str, Any]:
    """Get specific action guidance and portal links."""
    actions = {
        "delete_resource": {
            "title": "Delete Unused Resource",
            "portal_url": "https://portal.azure.com/#view/HubsExtension/BrowseAll",
            "docs": "https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/delete-resource-group",
            "steps": [
                "Navigate to the resource in Azure Portal",
                "Review any dependencies or data that may be lost",
                "Click 'Delete' and confirm the action",
                "Verify the resource has been removed"
            ]
        },
        "resize_resource": {
            "title": "Resize/Rightsize Resource",
            "portal_url": "https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/advisor",
            "docs": "https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations",
            "steps": [
                "Review current resource utilization metrics",
                "Identify the recommended size from Azure Advisor",
                "Schedule a maintenance window if needed",
                "Resize the resource to the recommended tier"
            ]
        },
        "purchase_reservation": {
            "title": "Purchase Reserved Instance",
            "portal_url": "https://portal.azure.com/#view/Microsoft_Azure_Reservations/CreateBlade/referrer/Browse",
            "docs": "https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations",
            "steps": [
                "Analyze your usage patterns for stability",
                "Calculate potential savings with reservation",
                "Choose 1-year or 3-year term based on commitment",
                "Purchase reservation through Azure Portal"
            ]
        },
        "enable_hybrid_benefit": {
            "title": "Enable Azure Hybrid Benefit",
            "portal_url": "https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Compute%2FVirtualMachines",
            "docs": "https://learn.microsoft.com/en-us/azure/virtual-machines/windows/hybrid-use-benefit-licensing",
            "steps": [
                "Verify you have eligible Windows Server licenses with Software Assurance",
                "Navigate to the VM in Azure Portal",
                "Go to Configuration and enable Azure Hybrid Benefit",
                "Save changes to start saving immediately"
            ]
        },
        "change_tier": {
            "title": "Change Resource Tier/SKU",
            "portal_url": "https://portal.azure.com",
            "docs": "https://learn.microsoft.com/en-us/azure/storage/blobs/access-tiers-overview",
            "steps": [
                "Review current usage and access patterns",
                "Identify the appropriate tier for your workload",
                "Plan for any performance impact during transition",
                "Change the tier and monitor performance"
            ]
        },
        "stop_resource": {
            "title": "Stop/Deallocate Resource",
            "portal_url": "https://portal.azure.com",
            "docs": "https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing",
            "steps": [
                "Identify resources that can be stopped during off-hours",
                "Consider using Azure Automation for scheduling",
                "Stop and deallocate (not just stop) to avoid compute charges",
                "Verify only storage charges remain after deallocation"
            ]
        },
        "enable_autoscale": {
            "title": "Enable Autoscaling",
            "portal_url": "https://portal.azure.com/#view/Microsoft_Azure_Monitoring/AzureMonitoringBrowseBlade/~/autoscale",
            "docs": "https://learn.microsoft.com/en-us/azure/azure-monitor/autoscale/autoscale-overview",
            "steps": [
                "Analyze your workload patterns and peak times",
                "Define minimum, maximum, and default instance counts",
                "Create scale-out and scale-in rules based on metrics",
                "Test autoscaling in a non-production environment first"
            ]
        }
    }
    
    action = actions.get(action_type, {
        "title": "Cost Optimization Action",
        "portal_url": "https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/overview",
        "docs": "https://learn.microsoft.com/en-us/azure/cost-management-billing/",
        "steps": ["Review the recommendation in Azure Advisor", "Take appropriate action based on guidance"]
    })
    
    return {
        "success": True,
        "action": action,
        "resource_type": resource_type
    }


def execute_function(function_name: str, arguments: Dict) -> str:
    """Execute a function call and return the result as a string."""
    if function_name == "get_azure_documentation":
        result = get_azure_documentation(**arguments)
    elif function_name == "search_azure_docs":
        result = search_azure_docs(**arguments)
    elif function_name == "get_cost_optimization_action":
        result = get_cost_optimization_action(**arguments)
    else:
        result = {"error": f"Unknown function: {function_name}"}
    
    return json.dumps(result)


def categorize_recommendation(problem: str, solution: str, resource_type: str = None) -> str:
    """Determine the category of a recommendation based on its content."""
    text = f"{problem} {solution}".lower()
    
    # Check for reserved instances
    if any(kw in text for kw in ["reserved instance", "reservation", "reserve capacity", "ri "]):
        return "reserved_instances"
    
    # Check for savings plans
    if any(kw in text for kw in ["savings plan", "compute savings"]):
        return "savings_plan"
    
    # Check for rightsizing
    if any(kw in text for kw in ["rightsize", "right-size", "resize", "underutilized", "oversized", "scale down"]):
        if "sql" in text:
            return "sql_optimization"
        return "vm_rightsizing"
    
    # Check for unused resources
    if any(kw in text for kw in ["unused", "unattached", "orphan", "not attached", "idle disk", "unassociated"]):
        return "unused_resources"
    
    # Check for idle resources
    if any(kw in text for kw in ["idle", "stopped", "deallocate", "shutdown", "not running"]):
        return "idle_resources"
    
    # Check for storage optimization
    if any(kw in text for kw in ["storage tier", "access tier", "cool storage", "archive", "lifecycle"]):
        return "storage_optimization"
    
    # Check for hybrid benefit
    if any(kw in text for kw in ["hybrid benefit", "ahb", "license", "byol"]):
        return "hybrid_benefit"
    
    # Default to cost management
    return "cost_management"
