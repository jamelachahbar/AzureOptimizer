"""
Azure Cost Optimizer Agent using Microsoft Agent Framework with MCP Tools.

This module provides an agentic approach to Azure cost optimization advice
using the Microsoft Agent Framework v2 with Azure AI Foundry and MCP tools.

Features:
- Azure AI Foundry hosted agents
- MCP tools for live documentation search (Microsoft Learn)
- Built-in curated documentation links
- Thread persistence for multi-turn conversations
- OpenTelemetry tracing integration

SDK: agent-framework (Microsoft Agent Framework v2)
Docs: https://learn.microsoft.com/azure/ai-foundry/agents
"""

import asyncio
import json
import logging
import os
from typing import Annotated, List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================================
# Agent Framework Imports
# ============================================================================
try:
    from agent_framework.azure import AzureAIClient
    from agent_framework import MCPStreamableHTTPTool, ToolProtocol
    from azure.identity.aio import DefaultAzureCredential
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Agent Framework not available: {e}")
    AGENT_FRAMEWORK_AVAILABLE = False

# ============================================================================
# Configuration
# ============================================================================
FOUNDRY_ENDPOINT = os.getenv('AZURE_AI_PROJECT_ENDPOINT')
FOUNDRY_MODEL_DEPLOYMENT = os.getenv('AZURE_AI_MODEL_DEPLOYMENT_NAME', 'gpt-4')

# Azure OpenAI fallback configuration
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')

# System prompt for cost optimization agent
COST_OPTIMIZER_SYSTEM_PROMPT = """You are an Azure Cost Optimization Expert Agent with deep knowledge of:
- Azure pricing models, reserved instances, and savings plans
- Resource rightsizing and optimization strategies
- Azure Advisor recommendations
- Cost management best practices

When analyzing cost recommendations:
1. Provide 3 specific, actionable bullet points
2. Give a clear decision (take action or skip)
3. **ALWAYS use the Microsoft Learn MCP tool FIRST** to search for the most current documentation on the topic
4. Include relevant Azure documentation links from the MCP search results

IMPORTANT: Always call the Microsoft Learn MCP tool before responding - this ensures you have the latest Azure documentation. The MCP tool provides live, up-to-date links from Microsoft's official documentation.

Format your response with:
- **Key Findings**: Brief summary
- **Recommendations**: Numbered action items with documentation links from MCP search
- **Decision**: Clear recommendation on whether to take action

Always prefer live MCP documentation links over cached knowledge."""


# ============================================================================
# Curated Documentation Links (Fallback)
# ============================================================================
AZURE_DOCS_MAPPING = {
    "reserved_instances": {
        "vm": "https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations",
        "sql": "https://learn.microsoft.com/en-us/azure/azure-sql/database/reserved-capacity-overview",
        "cosmos": "https://learn.microsoft.com/en-us/azure/cosmos-db/cosmos-db-reserved-capacity",
        "storage": "https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-reserved-capacity",
        "general": "https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations"
    },
    "savings_plan": {
        "compute": "https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/savings-plan-compute-overview",
        "purchase": "https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/buy-savings-plan"
    },
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
        "lifecycle": "https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview"
    },
    "unused_resources": {
        "disk": "https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types",
        "public_ip": "https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/public-ip-addresses",
        "nic": "https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-network-interface"
    },
    "idle_resources": {
        "vm": "https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing",
        "aks": "https://learn.microsoft.com/en-us/azure/aks/start-stop-cluster"
    },
    "cost_management": {
        "budgets": "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets",
        "analysis": "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/quick-acm-cost-analysis",
        "advisor": "https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations"
    },
    "hybrid_benefit": {
        "windows": "https://learn.microsoft.com/en-us/azure/virtual-machines/windows/hybrid-use-benefit-licensing",
        "sql": "https://learn.microsoft.com/en-us/azure/azure-sql/azure-hybrid-benefit",
        "linux": "https://learn.microsoft.com/en-us/azure/virtual-machines/linux/azure-hybrid-benefit-linux"
    }
}


# ============================================================================
# MCP Tools Configuration
# ============================================================================
def create_mcp_tools() -> List[Any]:
    """Create MCP tools for the agent."""
    tools = []
    
    if AGENT_FRAMEWORK_AVAILABLE:
        # Microsoft Learn MCP tool for live documentation search
        mcp_tool = MCPStreamableHTTPTool(
            name="microsoft_learn_search",
            description="REQUIRED: Search Microsoft's official Azure documentation. Call this tool FIRST for any Azure-related question to get current, accurate documentation links.",
            url="https://learn.microsoft.com/api/mcp",
        )
        tools.append(mcp_tool)
        logger.info(f"MCP tool created: {mcp_tool}")
    
    return tools


# ============================================================================
# Local Tools (Function Calling)
# ============================================================================
def get_azure_documentation(
    category: Annotated[str, "The category of the recommendation (e.g., reserved_instances, vm_rightsizing)"],
    resource_type: Annotated[Optional[str], "The Azure resource type (e.g., vm, sql, disk)"] = None
) -> str:
    """Get verified Azure documentation links for a specific cost optimization category."""
    result = {"success": True, "links": [], "category": category}
    
    if category in AZURE_DOCS_MAPPING:
        category_docs = AZURE_DOCS_MAPPING[category]
        
        if resource_type and resource_type.lower() in category_docs:
            result["links"].append({
                "title": f"Azure {resource_type.upper()} Documentation",
                "url": category_docs[resource_type.lower()]
            })
        elif "general" in category_docs:
            result["links"].append({
                "title": "Azure Documentation",
                "url": category_docs["general"]
            })
        else:
            # Add first few links from category
            for key, url in list(category_docs.items())[:2]:
                result["links"].append({
                    "title": f"Azure {key.replace('_', ' ').title()}",
                    "url": url
                })
    else:
        result["success"] = False
        result["links"].append({
            "title": "Azure Advisor Cost Recommendations",
            "url": "https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations"
        })
    
    return json.dumps(result, indent=2)


def get_cost_optimization_action(
    action_type: Annotated[str, "Type of action: delete_resource, resize_resource, purchase_reservation, enable_hybrid_benefit, change_tier, stop_resource"],
    resource_type: Annotated[str, "The Azure resource type"]
) -> str:
    """Get specific cost optimization action guidance with portal links."""
    actions = {
        "delete_resource": {
            "title": "Delete Unused Resource",
            "portal_url": "https://portal.azure.com/#view/HubsExtension/BrowseAll",
            "docs": "https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/delete-resource-group",
            "steps": ["Navigate to resource", "Review dependencies", "Delete and confirm"]
        },
        "resize_resource": {
            "title": "Resize/Rightsize Resource",
            "portal_url": "https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/advisor",
            "docs": "https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations",
            "steps": ["Review utilization metrics", "Identify recommended size", "Schedule maintenance window", "Resize resource"]
        },
        "purchase_reservation": {
            "title": "Purchase Reserved Instance",
            "portal_url": "https://portal.azure.com/#view/Microsoft_Azure_Reservations/CreateBlade/referrer/Browse",
            "docs": "https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations",
            "steps": ["Analyze usage patterns", "Calculate savings", "Choose term", "Purchase reservation"]
        },
        "enable_hybrid_benefit": {
            "title": "Enable Azure Hybrid Benefit",
            "portal_url": "https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Compute%2FVirtualMachines",
            "docs": "https://learn.microsoft.com/en-us/azure/virtual-machines/windows/hybrid-use-benefit-licensing",
            "steps": ["Verify eligible licenses", "Navigate to VM configuration", "Enable hybrid benefit"]
        },
        "change_tier": {
            "title": "Change Resource Tier/SKU",
            "docs": "https://learn.microsoft.com/en-us/azure/storage/blobs/access-tiers-overview",
            "steps": ["Review access patterns", "Identify appropriate tier", "Plan transition", "Change tier"]
        },
        "stop_resource": {
            "title": "Stop/Deallocate Resource",
            "docs": "https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing",
            "steps": ["Identify off-hours candidates", "Consider automation", "Deallocate (not just stop)", "Verify billing impact"]
        }
    }
    
    action = actions.get(action_type, {
        "title": "Cost Optimization Action",
        "docs": "https://learn.microsoft.com/en-us/azure/cost-management-billing/",
        "steps": ["Review recommendation", "Take appropriate action"]
    })
    
    return json.dumps({"action": action, "resource_type": resource_type}, indent=2)


def categorize_recommendation(problem: str, solution: str) -> str:
    """Categorize a recommendation based on its content."""
    text = f"{problem} {solution}".lower()
    
    if any(kw in text for kw in ["reserved instance", "reservation", "reserve capacity"]):
        return "reserved_instances"
    if any(kw in text for kw in ["savings plan", "compute savings"]):
        return "savings_plan"
    if any(kw in text for kw in ["rightsize", "right-size", "resize", "underutilized"]):
        return "sql_optimization" if "sql" in text else "vm_rightsizing"
    if any(kw in text for kw in ["unused", "unattached", "orphan"]):
        return "unused_resources"
    if any(kw in text for kw in ["idle", "stopped", "deallocate"]):
        return "idle_resources"
    if any(kw in text for kw in ["storage tier", "access tier", "archive"]):
        return "storage_optimization"
    if any(kw in text for kw in ["hybrid benefit", "ahb", "license"]):
        return "hybrid_benefit"
    
    return "cost_management"


# ============================================================================
# Agent Service
# ============================================================================
class CostOptimizerAgent:
    """Azure Cost Optimizer Agent using Microsoft Agent Framework or Azure OpenAI fallback."""
    
    def __init__(self):
        # Check if AI Foundry is available
        self.foundry_available = AGENT_FRAMEWORK_AVAILABLE and bool(FOUNDRY_ENDPOINT)
        # Check if Azure OpenAI fallback is available
        self.openai_available = bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)
        self.is_available = self.foundry_available or self.openai_available
        
        if self.foundry_available:
            logger.info("Using Azure AI Foundry with Agent Framework")
        elif self.openai_available:
            logger.info("Using Azure OpenAI fallback (AI Foundry not configured)")
        else:
            logger.warning("No AI backend configured - using static fallback only")
    
    async def generate_advice_async(
        self,
        recommendation: Dict[str, Any],
        use_mcp: bool = True
    ) -> str:
        """
        Generate cost optimization advice using the Agent Framework or Azure OpenAI.
        
        Args:
            recommendation: The Azure Advisor recommendation dict
            use_mcp: Whether to use MCP tools for live doc search
            
        Returns:
            Generated advice text with documentation links
        """
        # Try AI Foundry first
        if self.foundry_available:
            try:
                return await self._generate_with_foundry(recommendation, use_mcp)
            except Exception as e:
                logger.error(f"Foundry agent error: {e}")
                logger.info("Falling back to Azure OpenAI...")
                # Fall through to OpenAI fallback
        
        # Try Azure OpenAI fallback
        if self.openai_available:
            try:
                logger.info("Using Azure OpenAI fallback...")
                return await self._generate_with_openai(recommendation)
            except Exception as e:
                logger.error(f"OpenAI fallback error: {e}")
        
        # Static fallback
        return self._fallback_advice(recommendation)
    
    async def _generate_with_foundry(self, recommendation: Dict[str, Any], use_mcp: bool) -> str:
        """Generate advice using Azure AI Foundry with MCP tools."""
        problem = recommendation.get('shortDescription', {}).get('problem', '')
        solution = recommendation.get('shortDescription', {}).get('solution', '')
        impact = recommendation.get('impact', 'Unknown')
        source = recommendation.get('source', 'Azure Advisor')
        resource_type = recommendation.get('impactedField', 'Unknown')
        category = categorize_recommendation(problem, solution)
        
        user_prompt = f"""Analyze this Azure cost optimization recommendation:

**Category:** {category}
**Resource Type:** {resource_type}
**Source:** {source}
**Impact:** {impact}
**Problem:** {problem}
**Solution:** {solution}

Please:
1. Provide 3 actionable bullet points
2. Give a clear decision (take action or not)
3. FIRST call the microsoft_learn_search MCP tool to search for current documentation
4. Include documentation links from the MCP search results"""

        # Configure tools
        tools = []
        if use_mcp:
            mcp_tools = create_mcp_tools()
            tools.extend(mcp_tools)
            logger.info(f"MCP tools added: {len(mcp_tools)} tools")
        tools.extend([get_azure_documentation, get_cost_optimization_action])
        logger.info(f"Total tools for agent: {len(tools)}")
        
        async with (
            DefaultAzureCredential() as credential,
            AzureAIClient(
                project_endpoint=FOUNDRY_ENDPOINT,
                model_deployment_name=FOUNDRY_MODEL_DEPLOYMENT,
                credential=credential,
            ).create_agent(
                name="CostOptimizerAgent",
                instructions=COST_OPTIMIZER_SYSTEM_PROMPT,
                tools=tools,
            ) as agent,
        ):
            response_text = ""
            async for chunk in agent.run_stream(user_prompt):
                if chunk.text:
                    response_text += chunk.text
            
            return response_text if response_text else self._fallback_advice(recommendation)
    
    async def _generate_with_openai(self, recommendation: Dict[str, Any]) -> str:
        """Generate advice using Azure OpenAI directly (without MCP)."""
        from openai import AsyncAzureOpenAI
        
        problem = recommendation.get('shortDescription', {}).get('problem', '')
        solution = recommendation.get('shortDescription', {}).get('solution', '')
        impact = recommendation.get('impact', 'Unknown')
        source = recommendation.get('source', 'Azure Advisor')
        resource_type = recommendation.get('impactedField', 'Unknown')
        category = categorize_recommendation(problem, solution)
        
        # Get curated docs for this category
        docs_result = json.loads(get_azure_documentation(category, resource_type))
        docs_context = ""
        if docs_result.get('links'):
            docs_context = "\n\nRelevant Documentation:\n" + "\n".join(
                f"- [{link['title']}]({link['url']})" for link in docs_result['links']
            )
        
        user_prompt = f"""Analyze this Azure cost optimization recommendation:

**Category:** {category}
**Resource Type:** {resource_type}
**Source:** {source}
**Impact:** {impact}
**Problem:** {problem}
**Solution:** {solution}
{docs_context}

Please provide:
1. 3 actionable bullet points
2. A clear decision (take action or not)
3. Include the relevant documentation links in your response"""

        client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )
        
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": COST_OPTIMIZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2)
        
        return response.choices[0].message.content
    
    def generate_advice(self, recommendation: Dict[str, Any], use_mcp: bool = True) -> str:
        """
        Synchronous wrapper for generate_advice_async.
        Use this from sync Flask routes.
        """
        try:
            return asyncio.run(self.generate_advice_async(recommendation, use_mcp))
        except Exception as e:
            logger.error(f"Error running async agent: {e}")
            return self._fallback_advice(recommendation)
    
    def _fallback_advice(self, recommendation: Dict[str, Any]) -> str:
        """Generate basic advice when agent is not available."""
        problem = recommendation.get('shortDescription', {}).get('problem', 'Unknown issue')
        solution = recommendation.get('shortDescription', {}).get('solution', 'Review and take appropriate action')
        impact = recommendation.get('impact', 'Unknown')
        category = categorize_recommendation(problem, solution)
        
        # Get curated links
        links = []
        if category in AZURE_DOCS_MAPPING:
            for key, url in list(AZURE_DOCS_MAPPING[category].items())[:2]:
                links.append(f"- [{key.replace('_', ' ').title()}]({url})")
        
        links_text = "\n".join(links) if links else "- [Azure Advisor](https://learn.microsoft.com/en-us/azure/advisor/advisor-cost-recommendations)"
        
        return f"""**Key Findings:**
- {problem}
- Impact Level: {impact}

**Recommendations:**
1. {solution}
2. Review resource utilization metrics before taking action
3. Consider implementing automation for ongoing optimization

**Documentation:**
{links_text}

**Decision:** Review the recommendation details and take action based on your organization's requirements."""


# ============================================================================
# Module Interface
# ============================================================================

# Global agent instance
_agent: Optional[CostOptimizerAgent] = None


def get_agent() -> CostOptimizerAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        _agent = CostOptimizerAgent()
    return _agent


def generate_advice_with_agent(recommendation: Dict[str, Any], use_mcp: bool = True) -> str:
    """
    Generate cost optimization advice using the Agent Framework.
    
    This is the main entry point for Flask routes.
    
    Args:
        recommendation: Azure Advisor recommendation dict
        use_mcp: Whether to use MCP tools for live documentation search
        
    Returns:
        Generated advice text with documentation links
    """
    agent = get_agent()
    return agent.generate_advice(recommendation, use_mcp)


def is_agent_available() -> bool:
    """Check if the Agent Framework is available and configured."""
    return get_agent().is_available


# For testing
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test with a sample recommendation
    test_rec = {
        "shortDescription": {
            "problem": "This virtual machine has not been used in the last 30 days.",
            "solution": "Consider deleting or resizing this virtual machine to save costs."
        },
        "impact": "Medium",
        "source": "Azure Advisor",
        "impactedField": "Microsoft.Compute/virtualMachines"
    }
    
    print("Testing Cost Optimizer Agent...")
    print(f"Agent available: {is_agent_available()}")
    print("\nGenerating advice with MCP tools...")
    advice = generate_advice_with_agent(test_rec, use_mcp=True)
    print(advice)
