import uuid
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import threading
import logging
import time
import yaml
import os
import json
from azure_cost_optimizer.optimizer import main as optimizer_main
import matplotlib
# Note: openai is now handled internally by foundry_agent.py
from azure.mgmt.advisor import AdvisorManagementClient
from azure.identity import DefaultAzureCredential
from storage_utils import ensure_container_and_files_exist, container_client
from azure.mgmt.advisor import AdvisorManagementClient
from dotenv import load_dotenv
from cache_manager import cache_manager, CacheNamespaces, CacheTTL
from pagination import paginate, PaginationParams
from llm_tools import AVAILABLE_FUNCTIONS, execute_function, categorize_recommendation
from foundry_agent import generate_advice_with_agent, is_agent_available
import os

load_dotenv()  # Load .env file
subscription_ids = os.getenv('AZURE_SUBSCRIPTION_ID').split(',')  # This will allow for multiple IDs

# Set up the credentials
credential = DefaultAzureCredential()

# import pyodbc # Import the pyodbc module for SQL Server connectivity

# from agents.azure_tools import get_cost_data, get_cost_recommendations, llm_generate_advice
# Ensure the container and files exist at startup
ensure_container_and_files_exist()

# Note: Azure OpenAI is now handled by foundry_agent.py using the new SDK
# The old openai.api_type/api_key/api_base pattern is deprecated in openai>=1.0.0

matplotlib.use('Agg')  # Use a non-interactive backend



app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# ===== REQUEST LOGGING MIDDLEWARE =====
@app.before_request
def before_request_logging():
    """Log incoming request and attach timing/request ID."""
    import uuid
    request.start_time = time.time()
    request.request_id = str(uuid.uuid4())[:8]  # Short request ID for tracing


@app.after_request
def after_request_logging(response):
    """Log request completion with timing information."""
    if hasattr(request, 'start_time'):
        duration_ms = (time.time() - request.start_time) * 1000
        request_id = getattr(request, 'request_id', 'unknown')
        
        # Only log API routes
        if request.path.startswith('/api/'):
            log_level = logging.INFO if response.status_code < 400 else logging.WARNING
            logger.log(
                log_level,
                f"[{request_id}] {request.method} {request.path} - {response.status_code} ({duration_ms:.2f}ms)"
            )
        
        # Add request ID to response headers for client-side tracing
        response.headers['X-Request-ID'] = request_id
    
    return response


# ================================================================================
# OpenAPI / Swagger Documentation Endpoints
# ================================================================================

@app.route('/api/openapi.json')
def openapi_spec():
    """
    Serve OpenAPI specification.
    Returns the OpenAPI 3.0.3 specification for this API.
    """
    try:
        spec_path = os.path.join(app.static_folder, 'openapi.json')
        if os.path.exists(spec_path):
            with open(spec_path, 'r') as f:
                spec = json.load(f)
            return jsonify(spec)
        else:
            return jsonify({
                'error': 'OpenAPI specification not found',
                'path': spec_path
            }), 404
    except Exception as e:
        logger.error(f"Error serving OpenAPI spec: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/docs')
def swagger_ui():
    """
    Serve Swagger UI for interactive API documentation.
    Uses Swagger UI from CDN for minimal dependencies.
    """
    swagger_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Azure Cost Optimizer API - Documentation</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css">
        <style>
            body { margin: 0; padding: 0; }
            .swagger-ui .topbar { display: none; }
            .swagger-ui .info .title { color: #0078d4; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: "/api/openapi.json",
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return swagger_html, 200, {'Content-Type': 'text/html'}


# ================================================================================
# Cache Management Endpoints
# ================================================================================

@app.route('/api/cache/stats')
def cache_stats():
    """
    Get cache statistics.
    Returns hit/miss counts, hit rate, and current cache size.
    """
    return jsonify({
        'status': 'success',
        'cache': cache_manager.stats
    })


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """
    Clear the cache.
    Optionally specify a namespace to clear only specific entries.
    
    Query params:
        namespace: Optional namespace prefix to clear (e.g., 'policies', 'cost_data')
    """
    namespace = request.args.get('namespace')
    count = cache_manager.clear(namespace)
    
    return jsonify({
        'status': 'success',
        'message': f'Cleared {count} cache entries' + (f' in namespace: {namespace}' if namespace else ''),
        'cleared_count': count
    })


@app.route('/api/cache/cleanup', methods=['POST'])
def cleanup_cache():
    """
    Remove expired entries from the cache.
    This is useful for manual cleanup without clearing valid entries.
    """
    count = cache_manager.cleanup_expired()
    
    return jsonify({
        'status': 'success',
        'message': f'Removed {count} expired entries',
        'removed_count': count
    })


summary_metrics_data = []
execution_data_data = []
impacted_resources_data = []
optimizer_status = "Idle"
anomalies_data = []
trend_data = []
log_messages = []
stop_event = threading.Event()

POLICIES_FILE = os.path.join('policies', 'policies.yaml')
def validate_policy(policy):
    required_keys = ['name', 'description', 'resource', 'actions']
    missing_keys = [key for key in required_keys if key not in policy]
    if missing_keys:
        logger.warning(f"Policy {policy.get('name', 'Unnamed')} is missing keys: {missing_keys}")
        return False
    return True
def load_policies():
    """Load and validate policies from the YAML file."""
    try:
        if os.path.exists(POLICIES_FILE):
            with open(POLICIES_FILE, 'r') as file:
                policies = yaml.safe_load(file) or {'policies': []}
                for policy in policies.get('policies', []):
                    if 'enabled' not in policy:
                        policy['enabled'] = True
                    if not validate_policy(policy):
                        logger.warning(f"Invalid policy found: {policy}")
                return policies
        else:
            logger.error(f"Policies file not found at {POLICIES_FILE}")
            return {'policies': []}
    except Exception as e:
        logger.exception(f"Failed to load policies: {e}")
        return {'policies': []}
def save_policies(policies):
    """Save policies to the YAML file and upload to Azure Blob Storage."""
    try:
        # Save to local file
        with open(POLICIES_FILE, 'w') as file:
            yaml.safe_dump(policies, file, sort_keys=False)
        logger.info(f"Policies saved locally to {POLICIES_FILE}")

        # Upload the file to Azure Blob Storage
        blob_name = os.path.basename(POLICIES_FILE)  # Use only the file name, not the full path
        blob_client = container_client.get_blob_client(blob_name)
        with open(POLICIES_FILE, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
        logger.info(f"Policies uploaded to Azure Blob Storage: {blob_name}")
    except Exception as e:
        logger.error(f"Error saving or uploading policies: {e}")
        raise



def stream_logs():
    global log_messages
    while True:
        if log_messages:
            message = log_messages.pop(0)
            yield f'data: {message}\n\n'
        time.sleep(1)

class SSELogHandler(logging.Handler):
    def emit(self, record):
        global log_messages
        log_messages.append(self.format(record))

sse_handler = SSELogHandler()
sse_handler.setFormatter(formatter)
logger.addHandler(sse_handler)

@app.route('/api/log-stream')
def log_stream():
    return Response(stream_logs(), content_type='text/event-stream')


@app.route('/api/run', methods=['POST'])
def run_optimizer():
    global optimizer_status
    mode = request.json.get('mode')
    tenant_id = request.json.get('tenantId')
    all_subscriptions = request.json.get('all_subscriptions', False)

    if not tenant_id:
        return jsonify({'error': 'Tenant ID is required'}), 400

    stop_event.clear()  # Reset the stop event

    def run_optimizer_in_thread():
        global summary_metrics_data, execution_data_data, impacted_resources_data, anomalies_data, trend_data, optimizer_status
        optimizer_status = "Running"
        try:
            # Pass the tenantId to optimizer_main
            result = optimizer_main(mode=mode, all_subscriptions=all_subscriptions, tenant_id=tenant_id, stop_event=stop_event)
            if result is None:
                raise ValueError("optimizer_main returned None")
            summary_metrics_data = result['summary_reports']
            execution_data_data = result['status_log']
            impacted_resources_data = result['impacted_resources']
            trend_data = result['trend_data']
            anomalies_data = result['anomalies']
            optimizer_status = "Completed"
        except Exception as e:
            optimizer_status = f"Error: {str(e)}"
            logger.error(f"Optimizer error: {e}")

    thread = threading.Thread(target=run_optimizer_in_thread)
    thread.start()

    return jsonify({'status': 'Optimizer started'}), 200

@app.route('/api/stop', methods=['POST'])
def stop_optimizer():
    global optimizer_status
    stop_event.set()
    optimizer_status = "Stopped"
    return jsonify({'status': 'Optimizer stopping'}), 200

@app.route('/api/status', methods=['GET'])
def get_status():
    global optimizer_status
    logger.info(f"Current optimizer status: {optimizer_status}")
    return jsonify({'status': optimizer_status}), 200


@app.route('/health', methods=['GET'])
def health_probe():
    """Simple health probe endpoint for Container App liveness/readiness checks."""
    return jsonify({'status': 'ok'}), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify API and dependencies are operational.
    Returns 200 if healthy, 503 if any dependency is unhealthy.
    """
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }
    
    is_healthy = True
    
    # Check 1: Azure Credentials (non-blocking - degraded mode is acceptable)
    try:
        # Test credential by getting token
        credential.get_token("https://management.azure.com/.default")
        health_status["checks"]["azure_credentials"] = {
            "status": "healthy",
            "message": "Azure credentials valid"
        }
    except Exception as e:
        # Don't fail health check for credential issues - app can still serve some endpoints
        # This prevents container restart loops during credential propagation delays
        health_status["checks"]["azure_credentials"] = {
            "status": "degraded",
            "message": f"Azure credential not ready: {str(e)}"
        }
        logger.warning(f"Health check: Azure credentials not ready - {str(e)}")

    # Check 2: Blob Storage (non-blocking - storage is optional for basic functionality)
    try:
        # Test blob storage connectivity
        if container_client:
            container_client.get_container_properties()
            health_status["checks"]["blob_storage"] = {
                "status": "healthy",
                "message": "Blob storage accessible"
            }
        else:
            health_status["checks"]["blob_storage"] = {
                "status": "degraded",
                "message": "Blob storage client not initialized - some features unavailable"
            }
    except Exception as e:
        # Don't fail health check for storage issues
        health_status["checks"]["blob_storage"] = {
            "status": "degraded",
            "message": f"Blob storage error: {str(e)}"
        }
        logger.warning(f"Health check: Blob storage not accessible - {str(e)}")
    
    # Check 3: Policies file
    try:
        if os.path.exists(POLICIES_FILE):
            policies = load_policies()
            policy_count = len(policies.get('policies', []))
            health_status["checks"]["policies"] = {
                "status": "healthy",
                "message": f"Policies loaded: {policy_count} policies found"
            }
        else:
            health_status["checks"]["policies"] = {
                "status": "warning",
                "message": "Policies file not found"
            }
    except Exception as e:
        health_status["checks"]["policies"] = {
            "status": "unhealthy",
            "message": f"Policies error: {str(e)}"
        }
    
    # Check 4: Environment variables
    required_vars = ["AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if not missing_vars:
        health_status["checks"]["environment"] = {
            "status": "healthy",
            "message": "All required environment variables set"
        }
    else:
        is_healthy = False
        health_status["checks"]["environment"] = {
            "status": "unhealthy",
            "message": f"Missing environment variables: {', '.join(missing_vars)}"
        }
    
    # Set overall status
    if not is_healthy:
        health_status["status"] = "unhealthy"
        return jsonify(health_status), 503
    
    return jsonify(health_status), 200


@app.route('/api/summary-metrics', methods=['GET'])
def get_summary_metrics():
    try:
        return jsonify(summary_metrics_data), 200
    except Exception as e:
        logger.error(f"Error fetching summary metrics: {e}")
        return jsonify({'error': 'Error fetching summary metrics'}), 500

@app.route('/api/execution-data', methods=['GET'])
def get_execution_data():
    global execution_data_data
    try:
        logger.info("Returning Execution Data")
        
        # If in-memory data is empty, try loading from file
        data = execution_data_data
        if not data:
            execution_data_file = os.path.join(os.path.dirname(__file__), 'execution_data.json')
            if os.path.exists(execution_data_file):
                try:
                    with open(execution_data_file, 'r') as f:
                        data = json.load(f)
                    logger.info(f"Loaded {len(data)} records from execution_data.json")
                except Exception as e:
                    logger.warning(f"Failed to load execution_data.json: {e}")
                    data = []
        
        # Support optional pagination via query params
        if 'page' in request.args or 'per_page' in request.args:
            return jsonify(paginate(data, request, sort_key='Resource')), 200
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error fetching execution data: {e}")
        return jsonify({'error': 'Error fetching execution data'}), 500

@app.route('/api/impacted-resources', methods=['GET'])
def get_impacted_resources():
    global impacted_resources_data
    try:
        logger.info("Returning Impacted Resources Data")
        
        # If in-memory data is empty, try loading from file
        resources = impacted_resources_data
        if not resources:
            impacted_resources_file = os.path.join(os.path.dirname(__file__), 'impacted_resources.json')
            if os.path.exists(impacted_resources_file):
                try:
                    with open(impacted_resources_file, 'r') as f:
                        resources = json.load(f)
                    logger.info(f"Loaded {len(resources)} resources from impacted_resources.json")
                except Exception as e:
                    logger.warning(f"Failed to load impacted_resources.json: {e}")
                    resources = []
        
        # Support optional pagination via query params
        if 'page' in request.args or 'per_page' in request.args:
            return jsonify(paginate(resources, request, sort_key='Resource')), 200
        return jsonify(resources), 200
    except Exception as e:
        logger.error(f"Error fetching impacted resources: {e}")
        return jsonify({'error': 'Error fetching impacted resources'}), 500

@app.route('/api/trend-data', methods=['GET'])
def get_trend_data():
    try:
        return jsonify(trend_data), 200
    except Exception as e:
        logger.error(f"Error fetching trend data: {e}")
        return jsonify({'error': 'Error fetching trend data'}), 500

@app.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    try:
        return jsonify(anomalies_data), 200
    except Exception as e:
        logger.error(f"Error fetching anomalies data: {e}")
        return jsonify({'error': 'Error fetching anomalies data'}), 500

@app.route('/api/policies', methods=['GET'])
def get_policies():
    try:
        policies = load_policies()
        return jsonify(policies), 200
    except Exception as e:
        logger.error(f"Error fetching policies: {e}")
        return jsonify({'error': 'Error fetching policies'}), 500

@app.route('/api/policies/<string:policy_name>', methods=['PATCH'])
def update_policy_status(policy_name):
    try:
        # Load existing policies
        policies = load_policies()

        # Find and update the specified policy
        for policy in policies['policies']:
            if policy['name'] == policy_name:
                policy['enabled'] = request.json.get('enabled', policy['enabled'])
                break
        else:
            return jsonify({"error": "Policy not found"}), 404

        # Save updated policies locally and upload to Azure Storage
        save_policies(policies)

        return jsonify({"message": "Policy updated successfully", "policy": policy}), 200
    except Exception as e:
        logger.error(f"Error updating policy: {e}")
        return jsonify({'error': 'Error updating policy'}), 500


@app.route('/api/toggle-policy', methods=['POST'])
def toggle_policy():
    try:
        data = request.json
        policy_name = data['policy_name']
        enabled = data['enabled']
        
        policies = load_policies()
        
        for policy in policies['policies']:
            if policy['name'] == policy_name:
                policy['enabled'] = enabled
                break
        
        save_policies(policies)
        
        return jsonify({"message": "Policy updated"}), 200
    except Exception as e:
        logger.error(f"Error toggling policy: {e}")
        return jsonify({'error': 'Error toggling policy'}), 500



@app.route('/api/initialize', methods=['POST'])
def initialize_storage():
    """Initialize storage by ensuring the container and files exist."""
    try:
        ensure_container_and_files_exist()
        return jsonify({"message": "Storage initialized successfully"}), 200
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return jsonify({"error": "Failed to initialize storage"}), 500


### API Endpoint for Cost Savings Estimation ###
@app.route('/api/estimate-savings', methods=['GET'])
def estimate_savings():
    """
    Estimate potential cost savings based on identified waste resources.
    
    Uses the impacted_resources_data that has already been populated by the optimizer,
    or falls back to execution_data.json if impacted_resources is empty.
    """
    global impacted_resources_data
    
    subscription_id = request.args.get('subscription_id')
    
    try:
        # Use impacted_resources_data if available, otherwise load from execution_data.json
        resources = impacted_resources_data
        
        if not resources:
            # Try loading from impacted_resources.json as fallback (has full data including Cost, ResourceId, etc.)
            impacted_resources_file = os.path.join(os.path.dirname(__file__), 'impacted_resources.json')
            if os.path.exists(impacted_resources_file):
                try:
                    with open(impacted_resources_file, 'r') as f:
                        resources = json.load(f)
                    logger.info(f"Loaded {len(resources)} resources from impacted_resources.json")
                except Exception as e:
                    logger.warning(f"Failed to load impacted_resources.json: {e}")
                    resources = []
        
        # Filter by subscription if provided
        if subscription_id and subscription_id != 'All Subscriptions':
            resources = [r for r in resources if r.get('SubscriptionId') == subscription_id]
        
        # Group resources by policy
        policy_groups = {}
        for resource in resources:
            policy_name = resource.get('Policy', 'Unknown')
            if policy_name not in policy_groups:
                policy_groups[policy_name] = []
            policy_groups[policy_name].append(resource)
        
        savings_estimate = {
            "subscription_id": subscription_id or "All Subscriptions",
            "estimated_monthly_savings": 0.0,
            "currency": "USD",
            "breakdown": [],
            "resources_analyzed": len(resources),
            "resources_impacted": len(resources)
        }
        
        # Calculate savings for each policy group
        for policy_name, policy_resources in policy_groups.items():
            # Get resource type from the first resource, or infer from policy name
            first_resource = policy_resources[0] if policy_resources else {}
            resource_type = first_resource.get('ResourceType', _infer_resource_type(policy_name))
            
            policy_estimate = {
                "policy_name": policy_name,
                "resource_type": resource_type,
                "matching_resources": len(policy_resources),
                "estimated_savings": 0.0,
                "resources": []
            }
            
            for resource in policy_resources:
                resource_name = resource.get('Resource', 'Unknown')
                resource_id = resource.get('ResourceId', '')
                actions = resource.get('Actions', resource.get('Action', ''))
                actual_cost = resource.get('Cost', 0) or 0  # Actual cost from Azure Cost Management
                resource_type_single = resource.get('ResourceType', '')
                
                # Use actual cost from Azure Cost Management if available, otherwise estimate
                # NICs, Resource Groups don't have direct costs in Azure
                has_actual_cost = actual_cost > 0
                if has_actual_cost:
                    estimated_monthly = float(actual_cost)
                    is_estimate = False
                else:
                    estimated_monthly = _estimate_resource_savings(resource_name, actions, policy_name, actual_cost)
                    is_estimate = True
                
                policy_estimate["estimated_savings"] += estimated_monthly
                policy_estimate["resources"].append({
                    "name": resource_name,
                    "resource_id": resource_id,
                    "resource_group": _extract_resource_group(resource_id) if resource_id else 'Unknown',
                    "resource_type": resource_type_single,
                    "action": actions,
                    "status": resource.get('Status', 'Identified'),
                    "subscription_id": resource.get('SubscriptionId', 'Unknown'),
                    "estimated_monthly_cost": round(estimated_monthly, 2),
                    "actual_cost": round(actual_cost, 2),
                    "is_estimate": is_estimate
                })
            
            if policy_estimate["matching_resources"] > 0:
                savings_estimate["breakdown"].append(policy_estimate)
                savings_estimate["estimated_monthly_savings"] += policy_estimate["estimated_savings"]
        
        # Round to 2 decimal places
        savings_estimate["estimated_monthly_savings"] = round(savings_estimate["estimated_monthly_savings"], 2)
        
        return jsonify(savings_estimate), 200
        
    except Exception as e:
        logger.error(f"Error estimating savings: {e}")
        return jsonify({'error': str(e)}), 500


def _infer_resource_type(policy_name: str) -> str:
    """Infer resource type from policy name."""
    policy_lower = policy_name.lower()
    if 'vm' in policy_lower or 'virtual' in policy_lower:
        return 'azure.vm'
    elif 'disk' in policy_lower:
        return 'azure.disk'
    elif 'nic' in policy_lower or 'network interface' in policy_lower:
        return 'azure.nic'
    elif 'public' in policy_lower and 'ip' in policy_lower:
        return 'azure.publicip'
    elif 'storage' in policy_lower:
        return 'azure.storage'
    elif 'sql' in policy_lower or 'database' in policy_lower:
        return 'azure.sql'
    elif 'gateway' in policy_lower:
        return 'azure.applicationgateway'
    elif 'resource' in policy_lower and 'group' in policy_lower:
        return 'azure.resourcegroup'
    return 'azure.unknown'


def _extract_resource_group(resource_id: str) -> str:
    """Extract resource group from resource ID or name."""
    if '/resourceGroups/' in resource_id:
        parts = resource_id.split('/resourceGroups/')
        if len(parts) > 1:
            return parts[1].split('/')[0]
    return 'Unknown'


def _estimate_resource_savings(resource_name: str, action: str, policy_name: str, cost: float) -> float:
    """
    Estimate monthly savings for a resource based on its type and action.
    
    Uses the cost from the optimizer if available, otherwise estimates based on resource type.
    """
    # If cost was provided by the optimizer, use it
    if cost and cost > 0:
        return float(cost)
    
    policy_lower = policy_name.lower()
    action_lower = action.lower() if action else ''
    
    # Estimate based on resource type inferred from policy
    if 'nic' in policy_lower or 'network interface' in policy_lower:
        # NICs themselves don't have direct cost, but indicate orphaned resources
        # Estimate a small cost for tracking purposes
        return 0.50
    
    elif 'disk' in policy_lower:
        # Unattached disks - estimate based on typical disk sizes
        # Average unattached disk ~128GB at ~$0.05/GB/month = ~$6.40/month
        return 6.40
    
    elif 'public' in policy_lower and 'ip' in policy_lower:
        # Static public IP ~$3.65/month
        return 3.65
    
    elif 'vm' in policy_lower:
        if 'stop' in action_lower:
            # Average VM cost when stopped (no compute, just disk)
            return 50.0
        elif 'delete' in action_lower:
            return 75.0
    
    elif 'storage' in policy_lower:
        if 'downgrade' in action_lower or 'sku' in action_lower:
            # Downgrading storage SKU - estimate 30% savings
            return 15.0
        return 10.0
    
    elif 'sql' in policy_lower or 'database' in policy_lower:
        # SQL database scaling savings
        return 50.0
    
    elif 'gateway' in policy_lower:
        # Application Gateway - can be expensive
        return 100.0
    
    elif 'resource' in policy_lower and 'group' in policy_lower:
        # Resource group cleanup - aggregate of contained resources
        return 25.0
    
    # Default estimate for unknown resources
    return 5.0


credential = DefaultAzureCredential()


### API Endpoint for Policy Validation ###
@app.route('/api/policies/validate', methods=['POST'])
def validate_policy_endpoint():
    """
    Validate a policy without saving it.
    
    Accepts a policy JSON and validates it against the schema,
    checking for valid resource types, filter types, and action types.
    """
    import json
    import jsonschema
    
    try:
        policy = request.json
        
        if not policy:
            return jsonify({
                "valid": False,
                "errors": [{"field": "body", "message": "No policy data provided"}]
            }), 400
        
        errors = []
        
        # Check required fields
        required_fields = ['name', 'resource', 'actions']
        for field in required_fields:
            if field not in policy:
                errors.append({
                    "field": field,
                    "message": f"Missing required field: {field}"
                })
        
        if errors:
            return jsonify({
                "valid": False,
                "errors": errors
            }), 400
        
        # Validate resource type
        valid_resources = [
            "azure.vm", "azure.disk", "azure.resourcegroup", 
            "azure.storage", "azure.sql", "azure.publicip", 
            "azure.applicationgateway", "azure.nic"
        ]
        if policy.get('resource') not in valid_resources:
            errors.append({
                "field": "resource",
                "message": f"Invalid resource type: {policy.get('resource')}. Valid types: {', '.join(valid_resources)}"
            })
        
        # Validate action types
        valid_actions = ["stop", "delete", "update_sku", "scale_dtu", "log", "downgrade_disks"]
        for i, action in enumerate(policy.get('actions', [])):
            if action.get('type') not in valid_actions:
                errors.append({
                    "field": f"actions[{i}].type",
                    "message": f"Invalid action type: {action.get('type')}. Valid types: {', '.join(valid_actions)}"
                })
        
        # Validate filter types
        valid_filters = ["last_used", "unattached", "tag", "sku", "stopped"]
        for i, filter_item in enumerate(policy.get('filters', [])):
            if filter_item.get('type') not in valid_filters:
                errors.append({
                    "field": f"filters[{i}].type",
                    "message": f"Invalid filter type: {filter_item.get('type')}. Valid types: {', '.join(valid_filters)}"
                })
            
            # Validate filter-specific requirements
            filter_type = filter_item.get('type')
            if filter_type == 'last_used':
                if 'days' not in filter_item:
                    errors.append({
                        "field": f"filters[{i}].days",
                        "message": "last_used filter requires 'days' field"
                    })
            elif filter_type == 'tag':
                if 'key' not in filter_item:
                    errors.append({
                        "field": f"filters[{i}].key",
                        "message": "tag filter requires 'key' field"
                    })
            elif filter_type == 'sku':
                if 'values' not in filter_item or not isinstance(filter_item.get('values'), list):
                    errors.append({
                        "field": f"filters[{i}].values",
                        "message": "sku filter requires 'values' field (array of SKU names)"
                    })
        
        # Validate action-specific requirements
        for i, action in enumerate(policy.get('actions', [])):
            action_type = action.get('type')
            if action_type == 'update_sku':
                if 'sku' not in action:
                    errors.append({
                        "field": f"actions[{i}].sku",
                        "message": "update_sku action requires 'sku' field (target SKU name)"
                    })
            elif action_type == 'scale_dtu':
                if 'tiers' not in action or not isinstance(action.get('tiers'), list):
                    errors.append({
                        "field": f"actions[{i}].tiers",
                        "message": "scale_dtu action requires 'tiers' field (array of tier configurations)"
                    })
        
        # Validate against JSON schema if available
        schema_file = os.path.join('src', 'schema.json')
        if os.path.exists(schema_file):
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                
                # Wrap policy in policies array for schema validation
                policy_wrapper = {"policies": [policy]}
                jsonschema.validate(instance=policy_wrapper, schema=schema)
            except jsonschema.ValidationError as e:
                errors.append({
                    "field": e.path[-1] if e.path else "unknown",
                    "message": e.message
                })
        
        if errors:
            return jsonify({
                "valid": False,
                "errors": errors
            }), 400
        
        return jsonify({
            "valid": True,
            "message": "Policy is valid",
            "policy_name": policy.get('name'),
            "resource_type": policy.get('resource'),
            "filter_count": len(policy.get('filters', [])),
            "action_count": len(policy.get('actions', []))
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating policy: {e}")
        return jsonify({
            "valid": False,
            "errors": [{"field": "unknown", "message": str(e)}]
        }), 500


### API Endpoints for Policy Editor ###
@app.route('/api/policies/policyeditor/<policy_name>', methods=['POST'])
def add_policy(policy_name):
    try:
        new_policy = request.json  # Expect the full policy structure from the frontend
        policies = load_policies()

        # Ensure the policy name in the URL matches the name in the policy data
        if policy_name != new_policy.get('name'):
            return jsonify({'error': 'Policy name in URL does not match policy data.'}), 400

        # Check for existing policy with the same name
        if any(policy['name'] == policy_name for policy in policies['policies']):
            return jsonify({'error': 'Policy with this name already exists.'}), 400

        policies['policies'].append(new_policy)
        save_policies(policies)  # Save locally and upload to Azure Storage

        return jsonify({"message": "Policy added successfully"}), 200
    except Exception as e:
        logger.error(f"Error adding policy: {e}")
        return jsonify({'error': 'Error adding policy'}), 500

@app.route('/api/policies/policyeditor/<policy_name>', methods=['PUT'])
def update_policy(policy_name):
    try:
        updated_policy = request.json  # The updated policy data sent from the frontend
        policies = load_policies()  # Load existing policies from the YAML file

        # Search for the policy by name
        for i, policy in enumerate(policies['policies']):
            if policy['name'] == policy_name:
                # Update the policy with the new data
                policies['policies'][i] = updated_policy
                save_policies(policies)  # Save the updated policies back to the YAML file
                return jsonify({"message": "Policy updated successfully"}), 200

        return jsonify({'error': 'Policy not found.'}), 404
    except Exception as e:
        logger.error(f"Error updating policy: {e}")
        return jsonify({'error': 'Error updating policy'}), 500

@app.route('/api/policies/policyeditor/<policy_name>', methods=['DELETE'])
def delete_policy(policy_name):
    try:
        policies = load_policies()

        # Find and remove the policy by name
        policy_to_delete = next((policy for policy in policies['policies'] if policy['name'] == policy_name), None)

        if not policy_to_delete:
            return jsonify({'error': 'Policy not found.'}), 404

        policies['policies'].remove(policy_to_delete)
        save_policies(policies)

        return jsonify({"message": "Policy deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting policy: {e}")
        return jsonify({'error': 'Error deleting policy'}), 500



### API Endpoint to fetch Subscription IDs from Azure ###
from azure.mgmt.resource import SubscriptionClient

@app.route('/api/get-subscriptions', methods=['POST'])
def get_user_subscriptions():
    """Fetch subscriptions for the authenticated user's tenant."""
    try:
        data = request.get_json()
        tenant_id = data.get('tenantId')

        if not tenant_id:
            return jsonify({'error': 'Tenant ID is required'}), 400

        # Initialize SubscriptionClient with credentials scoped to the tenantId
        credential = DefaultAzureCredential()
        subscription_client = SubscriptionClient(credential)

        # Fetch subscriptions for the tenant
        subscriptions = subscription_client.subscriptions.list()

        # Filter subscriptions tied to the tenantId
        subscription_list = [
            {"id": sub.subscription_id, "name": sub.display_name}
            for sub in subscriptions
        ]

        return jsonify(subscription_list), 200
    except Exception as e:
        logger.error(f"Error fetching subscriptions: {e}")
        return jsonify({'error': 'Failed to fetch subscriptions. Please check Azure credentials.'}), 500



### Work In Progress - Azure API and SQL DB Integration for Recommendations and Advice Generation ###

### Function to get recommendations from Azure API ###

from azure.identity import ClientSecretCredential, ManagedIdentityCredential

def get_credentials(tenant_id):
    """Return credentials for the given tenant ID.
    Uses ClientSecretCredential if AZURE_CLIENT_SECRET is set,
    otherwise falls back to ManagedIdentityCredential for Azure deployments.
    """
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    
    if client_id and client_secret:
        return ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    elif client_id:
        # Use Managed Identity with the specified client ID
        logger.info(f"Using Managed Identity with client_id: {client_id}")
        return ManagedIdentityCredential(client_id=client_id)
    else:
        # Fall back to DefaultAzureCredential
        logger.info("Using DefaultAzureCredential")
        return DefaultAzureCredential()

def get_cost_recommendations(tenant_id, subscription_ids):
    """Fetch cost recommendations from Azure Advisor."""
    all_cost_recommendations = {}

    # Create credentials for the specified tenant
    try:
        credential = get_credentials(tenant_id)
    except Exception as e:
        logger.error(f"Failed to get credentials for tenant {tenant_id}: {e}")
        return {}

    for subscription_id in subscription_ids:
        try:
            client = AdvisorManagementClient(credential, subscription_id)
            recommendations = client.recommendations.list()

            # Process each recommendation and always add a UUID, regardless of existing IDs
            cost_recommendations = [
                {
                    **rec.as_dict(),
                    'uuid': str(uuid.uuid4()),  # Always generate a new UUID
                    'RecommendationId': rec.id if rec.id else None,  # Keep original RecommendationId if present
                    'source': 'Azure API',
                    'subscription_id': subscription_id,  # Include the subscription_id
                    'impact': rec.impact if rec.impact else 'Unknown',  # Normalize impact
                    'resource_id': rec.resource_metadata.resource_id if hasattr(rec, 'resource_metadata') and hasattr(rec.resource_metadata, 'resource_id') else 'N/A'
                }
                for rec in recommendations if rec.category == 'Cost'
            ]

            all_cost_recommendations[subscription_id] = cost_recommendations
        except Exception as e:
            logger.error(f"Error fetching cost recommendations for subscription {subscription_id}: {e}")
            all_cost_recommendations[subscription_id] = []

    return all_cost_recommendations



### Function to get recommendations from SQL database ###

# def get_sql_recommendations():
#     conn_str = (
#         "DRIVER={ODBC Driver 18 for SQL Server};"
#         "SERVER=aoejml-sql.database.windows.net,1433;"
#         "DATABASE=azureoptimization;"
#         "UID=azureadmin@aoejml-sql;"
#         "PWD=Achahbar2019;"
#         "Encrypt=yes;"
#         "TrustServerCertificate=no;"
#         "Connection Timeout=30;"
#     )

#     query = """
#     SELECT RecommendationId, Category, Impact, 
#            RecommendationDescription, RecommendationAction, 
#            InstanceName, SubscriptionGuid, AdditionalInfo, 
#            TenantGuid, FitScore, GeneratedDate
#     FROM dbo.Recommendations
#     WHERE Category = 'Cost';
#     """

#     try:
#         conn = pyodbc.connect(conn_str)
#         cursor = conn.cursor()
#         cursor.execute(query)

#         recommendations = []
#         for row in cursor.fetchall():
#             # Always generate a UUID, even if other IDs are present
#             rec_uuid = str(uuid.uuid4())  
#             recommendations.append({
#                 'uuid': rec_uuid,
#                 'RecommendationId': row.RecommendationId if row.RecommendationId else rec_uuid,
#                 'category': row.Category,
#                 'impact': row.Impact if row.Impact else 'Unknown',  # Normalize impact
#                 'short_description': {
#                     'problem': row.RecommendationDescription if row.RecommendationDescription else 'No problem description available'
#                 },
#                 'action': row.RecommendationAction if row.RecommendationAction else 'No action available',
#                 'Instance': row.InstanceName,
#                 'subscription_id': row.SubscriptionGuid or rec_uuid,
#                 'source': 'SQL DB',
#                 'additional_info': row.AdditionalInfo,
#                 'tenant_id': row.TenantGuid,
#                 'fit_score': row.FitScore,
#                 'generated_date': row.GeneratedDate,
#                 'resource_id': 'N/A'  # Include this in the response, even if not provided by SQL

#             })
#         conn.close()
#         return recommendations

#     except Exception as e:
#         logger.error(f"Error fetching recommendations from SQL: {e}")
#         return []


### API Endpoint to Query Recommendations from Log Analytics ###
from log_analytics import get_log_analytics_data
from datetime import timedelta
from uuid import uuid4

# Ensure the correct mapping of fields for Log Analytics
@app.route('/api/log-analytics-data', methods=['POST'])
def fetch_log_analytics_data():
    # Use 'DEFAULT' if no client_id_key is passed in the request body
    client_id_key = request.json.get('client_id_key', 'DEFAULT')

    # Get the timespan from the request, or default to 30 days
    days = request.json.get('days', 30)
    timespan = timedelta(days=days)

    # Define the KQL query for Log Analytics data
    query = """
    AzureOptimizationRecommendationsV1_CL
    | where TimeGenerated >= ago(30d) and Category == "Cost"
    | extend additionalInfo = parse_json(AdditionalInfo_s)
    | project 
        problem = RecommendationDescription_s,  // Keep original name for recommendation
        impact = Impact_s,  // Keep original name for impact
        solution = RecommendationAction_s,  // Keep original name for solution
        TimeGenerated,  // Keep original name for generated date
        SubscriptionGuid_g,  // Keep original name for subscription ID
        savingsAmount = additionalInfo.savingsAmount,  // Include savingsAmount as is
        InstanceName_g,  // Include instance name
        FitScore_d,  // Fit score (if needed)
        resource_id = InstanceId_s
    | order by TimeGenerated desc
    """
    
    # Call the function with the dynamic client_id_key and timespan
    data = get_log_analytics_data(query=query, client_id_key='OTHER', timespan=timespan)

    return jsonify(data), 200


### LLM Advice Generation ###
MAX_TOKENS = 5000  # Maximum tokens for OpenAI API
def generate_advice_with_llm(recommendations):
    advice_list = []

    # Few-shot examples to guide the LLM output format
    few_shot_examples = """
    Example 1:
    To address the recommendation: **utilizing App Service Reserved Instances** for cost optimization effectively, consider implementing the following actionable steps:

    1. **Purchase App Service Reserved Instance**: Acquire 1 Azure App Service Premium v3 Plan (Linux P1 v3) for a term of 3 years in the South Central US region. This purchase will enable you to save approximately $910 annually, translating to a significant reduction in your ongoing costs.

    2. **Evaluate App Service Usage**: Review your current and forecasted usage of the App Service to ensure that it aligns with the reserved instance. Analyze the projected workload and confirm that this app service will be consistently utilized to maximize the annual savings of $910.

    3. **Monitor and Adjust Resource Allocation**: After purchasing the reserved instance, utilize Azure’s monitoring tools to track the performance and usage of the app service. This will help validate ongoing alignment with your operational needs and allow adjustments in future resource planning.

    **Conclusion**: Given the potential to save $910 annually and the high impact of this recommendation, it is advisable to take action by purchasing the App Service reserved instance. This decision aligns with your cost optimization goals in Azure and helps to ensure that resources are both effectively utilized and financially optimized.
    Example 2:
    **Recommendation: Reducing Costs with SQL DB Instance Rightsizing**
    
    The recommendation regarding oversized SQL Database instances can be addressed with the following steps:
    
    1. **Analyze SQL Database Utilization**: Review your current SQL database instance sizes and compare them against the actual workload usage metrics. If databases are oversized, there is an opportunity to downsize to a smaller instance tier.
    
    2. **Scale Down SQL DB**: For underutilized instances, scale down the SQL database to a lower pricing tier to reduce ongoing costs. Ensure that the new instance size meets the performance requirements of your application workloads.
    
    3. **Monitor Performance**: After downsizing, continuously monitor the performance of the SQL databases to ensure the new instance size meets workload demands.
    
    **Conclusion**: By rightsizing SQL Database instances and aligning them with actual usage, you can achieve significant cost savings while maintaining performance. 
    **Link**: [Azure SQL Database Pricing](https://azure.microsoft.com/en-us/pricing/details/sql-database/)
    **Link**: [Azure SQL Database Sizing and Performance Guidelines](https://docs.microsoft.com/en-us/azure/azure-sql/database/service-tier-hyperscale)
    
    Example 3:
    **Recommendation: Optimizing Costs with Reserved Instances**

    To optimize costs effectively using Reserved Instances in Azure, consider the following actions:
    

    1. **Analyze Usage Patterns**: Evaluate your historical usage patterns to identify stable workloads that can benefit from Reserved Instances. Focus on services with consistent demand to maximize savings.

    2. **Purchase Reserved Instances**: Once identified, purchase Reserved Instances for the appropriate services and regions. Leverage the Azure Hybrid Benefit for additional savings on Windows VMs.

    3. **Monitor and Adjust**: Regularly monitor your usage and adjust Reserved Instances as needed to align with changing workload requirements. Optimize your reservations to avoid underutilization.

    **Conclusion**: By strategically leveraging Reserved Instances based on usage patterns and monitoring your reservations, you can achieve significant cost savings in Azure.
    **Link**: [Azure Reserved VM Instances](https://azure.microsoft.com/en-us/pricing/reserved-vm-instances/)
    **Link**: [Azure Reserved Instances Documentation](https://docs.microsoft.com/en-us/azure/cost-management-billing/reserved-vm-instances)
    
    Example 4:

    **Recommendation: Optimizing Costs for Orphaned Public IP:**

    1. **Audit Public IP Allocations**: Confirm the orphaned status of the public IP (appgw-pip) by reviewing its association with resources. Assess if it was meant for a service that is still under development or needs, which can justify keeping it.

    2. **Delete Orphaned Public IP**: If you confirm that the public IP is indeed orphaned and lacks any associated resource utility, delete it to eliminate the ongoing costs. This will help reduce unnecessary expenses.

    3. **Change Configuration to Dynamic Allocation (if needed)**: If you require a public IP for future use, consider changing its allocation method to dynamic instead of static. This ensures you avoid incurring costs when the IP isn’t in active use.

    **Conclusion**: Deleting the orphaned public IP (appgw-pip) will result in immediate cost savings since it currently incurs no costs but is a potential liability for future charges if left unutilized. If there's potential to need it in the future, consider using dynamic allocation to minimize expenses.    
   
    Example 5:

    To effectively address the recommendation regarding **unattached disks** and optimize costs, consider implementing the following actionable steps:

    1. **Audit Unattached Disks**: Review all unattached disks within the specified subscription (e9b4640d-1f1f-45fe-a543-c0ea45ac34c1) to confirm which disks are indeed unnecessary. Cross-reference these disks with active VMs to validate they are not tied to any future deployments.

    2. **Delete Unused Disks**: For the disks confirmed to have no ownership and no future use, proceed with deletion. This will immediately cease any unnecessary costs associated with these unattached disks.

    3. **Evaluate Downgrade Options**: For disks that may be needed for future use but are currently unattached, assess the feasibility of downgrading these disks to a Standard SKU. This will reduce ongoing costs while still keeping the disks available for potential future use.

    **Conclusion**: Given the medium impact of this recommendation and the modest savings of approximately $0.04 per hour, it is advisable to take action to optimize costs by auditing, deleting unnecessary disks, and considering downgrades where appropriate. While the immediate savings might be low, it supports overall cost management principles and reduces clutter in your Azure environment.
    
    Example 6:
    **Recommendation: Optimize Costs with a Compute Savings Plan**
    To address the recommendation regarding purchasing a savings plan for compute, consider the following actionable steps:

    1. **Evaluate Current Compute Usage**: Analyze your current and forecasted compute resource usage to determine the consistency of your workloads. Ensure that the volumes of compute resources used align with the planned commitment over the savings plan's duration of 3 years for significant cost reductions.

    2.   **Purchase Compute Savings Plan**: Acquire a Compute Savings Plan based on your analysis. With an expected annual savings amount of $96 and a monthly commitment of only $8, this plan can substantially lower your costs while allowing the flexibility to utilize compute resources across different services within the specified subscription.

    3.  **Monitor and Adjust Resource Allocation**: After purchasing the savings plan, continuously monitor your compute usage to ensure you're maximizing savings. Assess how the savings plan can align with any shifted workloads and adjust as necessary to optimize usage.

    **Conclusion**: Given the high impact of this recommendation, alongside the considerable savings potential, it is advisable to take action by purchasing a Compute Savings Plan. This decision aligns well with your cost optimization goals in Azure, ensuring efficient utilization of resources while reducing costs.
    
    **Link**: [Buy an Azure savings plan](https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/buy-savings-plan)


    
    
    """

    # Mapping of resource types or recommendation categories to specific prompt instructions
    resource_instruction_map = {
        'disk': "If the recommendation is about unattached disks, your advice must be ONLY about unattached disks (e.g., audit, delete, downgrade, or repurpose disks). Do not mention tagging, cost analysis, or general Azure governance unless it directly applies to unattached disks.",
        'publicip': "If the recommendation is about unattached public IPs, your advice must be ONLY about unattached public IPs (e.g., audit, delete, or repurpose).",
        'nic': "If the recommendation is about unattached network interfaces, your advice must be ONLY about unattached NICs (e.g., audit, delete, or repurpose).",
        'sql': "If the recommendation is about SQL databases, your advice must be ONLY about SQL DBs (e.g., rightsize, scale, monitor, or optimize performance/cost).",
        'applicationgateway': "If the recommendation is about idle Application Gateways, your advice must be ONLY about Application Gateways (e.g., audit, delete, or reconfigure).",
        # Add more resource types and instructions as needed
    }

    for rec in recommendations:
        # Gather all available context fields
        short_description = rec.get('short_description', {})
        problem = short_description.get('problem') or rec.get('problem', 'No problem description available')
        solution = short_description.get('solution') or rec.get('solution', 'No solution available')
        impact = rec.get('impact', 'Unknown')
        subscription_id = rec.get('extended_properties', {}).get('subId', rec.get('subscription_id', 'N/A'))
        instance_name = rec.get('Instance', 'N/A')
        savings_amount = rec.get('savingsAmount', 'N/A')
        annual_savings = rec.get('annualSavingsAmount', 'N/A')
        resource_id = rec.get('resource_id', 'N/A')
        extended_properties = rec.get('extended_properties', {})
        source = rec.get('source', 'Unknown')

        # Try to infer resource type from recommendation fields
        resource_type = (
            rec.get('resource_type') or
            rec.get('resource') or
            (rec.get('short_description', {}).get('problem', '').split()[0].lower() if rec.get('short_description', {}).get('problem') else '')
        )
        resource_type = resource_type.lower() if resource_type else ''

        # Get resource-specific instructions if available
        resource_instructions = resource_instruction_map.get(resource_type, "Your advice must be ONLY about the specific resource/problem below. Do not give generic Azure cost management advice. If you cannot provide specific advice, say so directly.")

        # Build a context-rich, scalable prompt for the LLM
        prompt = f"""
        You are an expert Azure cost optimization consultant. Your task is to provide highly targeted, actionable advice for the following cost recommendation. The field 'Problem' below contains the main topic and scenario for this recommendation. **All advice and actions must be directly and specifically based on the Problem field.**

        {resource_instructions}

        Recommendation Context:
        - Source: {source}
        - PROBLEM (main topic): {problem}
        - Solution: {solution}
        - Impact: {impact}
        - Subscription ID: {subscription_id}
        - Instance Name: {instance_name}
        - Savings Amount: {savings_amount}
        - Annual Savings: {annual_savings}
        - Resource ID: {resource_id}
        - Extended Properties: {extended_properties}

        Instructions:
        1. The Problem field is the main topic. All advice and actions must be directly related to the Problem field and not generic.
        2. Provide a maximum of 3 bullet points for actions, each tailored to the context above.
        3. Conclude with a clear decision (take action or not), based on the specific details.
        4. Provide a working link to the most relevant Microsoft Learn documentation for this recommendation, if possible.
        5. Do not repeat generic advice—be as specific as possible. If you cannot provide specific advice, say so directly.

        {few_shot_examples}
        """

        try:
            # Send prompt to Azure OpenAI (GPT-4)
            response = openai.ChatCompletion.create(
                engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                messages=[
                    {"role": "system", "content": "You are a skilled Azure consultant who knows everything about FinOps and cost optimization."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_TOKENS
            )

            advice_text = response['choices'][0]['message']['content'].strip()
            if not advice_text:
                advice_text = "No advice could be generated."
            advice_list.append(advice_text)

        except openai.OpenAIError as e:
            logger.error(f"OpenAI Error: {e}")
            advice_list.append(f"An error occurred: {str(e)}")

    return advice_list


def generate_advice_with_function_calling(recommendations):
    """
    Generate cost optimization advice using Azure OpenAI with function calling.
    Uses curated, verified Azure documentation links instead of hallucinated URLs.
    """
    advice_list = []
    
    system_prompt = """You are an expert Azure consultant with 10+ years of FinOps experience.
Your role is to analyze Azure cost recommendations and provide actionable advice.

IMPORTANT INSTRUCTIONS:
1. Provide a maximum of 3 bullet points for actions
2. Conclude with a clear decision (take action or not)
3. ALWAYS use the get_azure_documentation or get_cost_optimization_action functions to get verified documentation links
4. NEVER make up or guess documentation URLs - always use the provided functions
5. Focus on cost optimization and immediate actionable steps

When providing links:
- Use get_azure_documentation for learning resources
- Use get_cost_optimization_action for step-by-step action guidance
- Use search_azure_docs only if the specific topic is not available in other functions"""

    for rec in recommendations:
        # Extract recommendation details
        short_description = rec.get('short_description', {})
        problem = short_description.get('problem') or rec.get('problem', 'No problem description available')
        solution = short_description.get('solution') or rec.get('solution', 'No solution available')
        impact = rec.get('impact', 'Unknown')
        source = rec.get('source', 'Unknown')
        subscription_id = rec.get('extended_properties', {}).get('subId', rec.get('subscription_id', 'N/A'))
        extended_props = rec.get('extended_properties', {})
        
        # Determine the category for function calling context
        category = categorize_recommendation(problem, solution)
        
        # Build the user prompt
        user_prompt = f"""Analyze this Azure cost recommendation and provide actionable advice:

**Source:** {source}
**Impact:** {impact}
**Problem:** {problem}
**Solution:** {solution}
**Subscription ID:** {subscription_id}
**Extended Properties:** {json.dumps(extended_props, indent=2) if extended_props else 'N/A'}

Please:
1. Provide 3 actionable bullet points
2. Give a clear decision (take action or not)
3. Use the available functions to get verified documentation links for category: {category}
4. Include at least one relevant Azure documentation link using the functions provided"""

        try:
            # First call with function definitions
            response = openai.ChatCompletion.create(
                engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                functions=AVAILABLE_FUNCTIONS,
                function_call="auto",
                max_tokens=MAX_TOKENS
            )

            response_message = response['choices'][0]['message']
            
            # Check if the model wants to call a function
            if response_message.get('function_call'):
                function_name = response_message['function_call']['name']
                function_args = json.loads(response_message['function_call']['arguments'])
                
                # Execute the function
                function_response = execute_function(function_name, function_args)
                
                # Send the function result back to the model
                second_response = openai.ChatCompletion.create(
                    engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                        response_message,
                        {
                            "role": "function",
                            "name": function_name,
                            "content": function_response
                        }
                    ],
                    functions=AVAILABLE_FUNCTIONS,
                    function_call="auto",
                    max_tokens=MAX_TOKENS
                )
                
                # Check for additional function calls (up to 3 iterations)
                final_message = second_response['choices'][0]['message']
                iterations = 0
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    response_message,
                    {"role": "function", "name": function_name, "content": function_response}
                ]
                
                while final_message.get('function_call') and iterations < 3:
                    func_name = final_message['function_call']['name']
                    func_args = json.loads(final_message['function_call']['arguments'])
                    func_response = execute_function(func_name, func_args)
                    
                    messages.append(final_message)
                    messages.append({"role": "function", "name": func_name, "content": func_response})
                    
                    next_response = openai.ChatCompletion.create(
                        engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                        messages=messages,
                        functions=AVAILABLE_FUNCTIONS,
                        function_call="auto",
                        max_tokens=MAX_TOKENS
                    )
                    final_message = next_response['choices'][0]['message']
                    iterations += 1
                
                advice_text = final_message.get('content', '').strip()
            else:
                # No function call, use the direct response
                advice_text = response_message.get('content', '').strip()
            
            if not advice_text:
                advice_text = "No advice could be generated."
            
            advice_list.append(advice_text)

        except openai.OpenAIError as e:
            logger.error(f"OpenAI Error: {e}")
            advice_list.append(f"An error occurred: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error in function arguments: {e}")
            advice_list.append("An error occurred while processing the recommendation.")
        except Exception as e:
            logger.error(f"Unexpected error in generate_advice_with_function_calling: {e}")
            advice_list.append(f"An error occurred: {str(e)}")

    return advice_list


# azure_subscription_ids = ['e9b4640d-1f1f-45fe-a543-c0ea45ac34c1','34f635ef-9210-4e8f-b9a9-8c3327604b23','b26069e9-79e1-49d1-a47c-877dfdc1fb20','b640da53-da83-438f-8c1d-dbc3de526d65','6d03d786-1501-4575-8d34-643ceca8af07']
# sql_subscription_id = '9d923c47-1aa2-4fc9-856f-16ca53e97b76'


### API Endpoint to Fetch and Review Recommendations ###
@app.route('/api/review-recommendations', methods=['POST'])
def review_recommendations_route():
    try:
        # Extract tenantId and subscriptionIds from the request body
        data = request.get_json()
        tenant_id = data.get('tenantId')
        subscription_ids = data.get('subscriptionIds', [])

        # Log received tenantId for debugging
        logger.info(f"Received tenantId: {tenant_id}")
        # Validate tenantId and subscriptionIds
        if not tenant_id:
            return jsonify({'error': 'Tenant ID is required'}), 400
        if not isinstance(subscription_ids, list):
            return jsonify({'error': 'Subscription IDs must be a list'}), 400
        if not subscription_ids:
            return jsonify({'error': 'A list of Subscription IDs is required'}), 400  # Optional: Allow empty list if necessary

        all_recommendations = []

        # Fetch recommendations from Azure Advisor
        azure_recommendations = []
        for subscription_id in subscription_ids:
            try:
                # Pass tenantId to get_cost_recommendations
                advisor_recommendations = get_cost_recommendations(tenant_id, [subscription_id])
                if isinstance(advisor_recommendations, dict):
                    for recommendations in advisor_recommendations.values():
                        if recommendations:
                            for rec in recommendations:
                                # Ensure subscription_id is included in each recommendation
                                if 'extended_properties' in rec and 'subid' in rec['extended_properties']:
                                    rec['subscription_id'] = rec['extended_properties']['subid']
                                else:
                                    rec['subscription_id'] = subscription_id  # Fallback to subscription_id
                                azure_recommendations.append(rec)
            except Exception as e:
                logger.error(f"Error fetching recommendations for subscription {subscription_id}: {e}")

        # Combine all recommendations
        all_recommendations.extend(azure_recommendations)

        # If no recommendations are found, return empty array (frontend expects an array)
        if not all_recommendations:
            logger.info(f"No recommendations found for tenant {tenant_id} and subscriptions {subscription_ids}")
            return jsonify([]), 200

        # Return the combined recommendations
        return jsonify(all_recommendations), 200

    except Exception as e:
        logger.error(f"Error fetching recommendations: {e}")
        return jsonify({'error': str(e)}), 500



### API Endpoint to Analyze Recommendations ###
@app.route('/api/analyze-recommendations', methods=['POST'])
def analyze_recommendations_route():
    data = request.get_json()
    recommendations = data.get('recommendations', [])
    logger.info(f"Received recommendations: {recommendations}")

    if not recommendations:
        return jsonify({'error': 'No recommendations provided'}), 400

    # Use the new Foundry agent with MCP tools for verified documentation links
    structured_data = []
    for rec in recommendations:
        try:
            # Use the new agent-based approach
            advice = generate_advice_with_agent(rec, use_mcp=True)
            structured_data.append({
                'recommendation': rec,
                'advice': advice
            })
        except Exception as e:
            logger.error(f"Error generating advice: {e}")
            structured_data.append({
                'recommendation': rec,
                'advice': f"Error generating advice: {str(e)}"
            })

    return jsonify(structured_data), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)