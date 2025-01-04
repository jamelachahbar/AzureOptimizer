import uuid
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import threading
import logging
import time
import yaml
import os
from azure_cost_optimizer.optimizer import main as optimizer_main
import matplotlib
import openai
from azure.mgmt.advisor import AdvisorManagementClient
from azure.identity import DefaultAzureCredential
from storage_utils import ensure_container_and_files_exist  # Import the storage utility module
from azure.identity import DefaultAzureCredential
from azure.mgmt.advisor import AdvisorManagementClient
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file
subscription_ids = os.getenv('AZURE_SUBSCRIPTION_ID').split(',')  # This will allow for multiple IDs

# Set up the credentials
credential = DefaultAzureCredential()

# import pyodbc # Import the pyodbc module for SQL Server connectivity

# from agents.azure_tools import get_cost_data, get_cost_recommendations, llm_generate_advice
# Ensure the container and files exist at startup
ensure_container_and_files_exist()
# Configure OpenAI GPT-4 API (or Azure OpenAI) using your API keys and endpoint
openai.api_key = os.getenv("OPENAI_API_KEY")
# Configure OpenAI GPT-4 API (or Azure OpenAI) using your API keys and endpoint
matplotlib.use('Agg')  # Use a non-interactive backend



app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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
    """Save policies to the YAML file."""
    with open(POLICIES_FILE, 'w') as file:
        yaml.safe_dump(policies, file, sort_keys=False)
    logger.info(f"Policies saved to {POLICIES_FILE}")

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
    all_subscriptions = request.json.get('all_subscriptions', False)
    stop_event.clear()  # Reset the stop event

    def run_optimizer_in_thread():
        global summary_metrics_data, execution_data_data, impacted_resources_data, anomalies_data, trend_data, optimizer_status
        optimizer_status = "Running"
        try:
            result = optimizer_main(mode=mode, all_subscriptions=all_subscriptions, stop_event=stop_event)
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
    return jsonify({'status': optimizer_status}), 200

@app.route('/api/summary-metrics', methods=['GET'])
def get_summary_metrics():
    try:
        return jsonify(summary_metrics_data), 200
    except Exception as e:
        logger.error(f"Error fetching summary metrics: {e}")
        return jsonify({'error': 'Error fetching summary metrics'}), 500

@app.route('/api/execution-data', methods=['GET'])
def get_execution_data():
    try:
        logger.info("Returning Execution Data")
        return jsonify(execution_data_data), 200
    except Exception as e:
        logger.error(f"Error fetching execution data: {e}")
        return jsonify({'error': 'Error fetching execution data'}), 500

@app.route('/api/impacted-resources', methods=['GET'])
def get_impacted_resources():
    try:
        logger.info("Returning Impacted Resources Data")
        return jsonify(impacted_resources_data), 200
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
    policies = load_policies()
    for policy in policies['policies']:
        if policy['name'] == policy_name:
            policy['enabled'] = request.json.get('enabled', policy['enabled'])
            save_policies(policies)
            return jsonify({"message": "Policy updated", "policy": policy})
    return jsonify({"error": "Policy not found"}), 404

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
        save_policies(policies)

        return jsonify({"message": "Policy added successfully"}), 200
    except Exception as e:
        logger.error(f"Error adding policy: {e}")
        return jsonify({'error': 'Error adding policy'}), 500

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

credential = DefaultAzureCredential()

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



### Work In Progress - Azure API and SQL DB Integration for Recommendations and Advice Generation ###

### Function to get recommendations from Azure API ###

def get_cost_recommendations(subscription_ids):
    all_cost_recommendations = {}

    for subscription_id in subscription_ids:
        try:
            client = AdvisorManagementClient(credential, subscription_id)
            recommendations = client.recommendations.list()

            # Process each recommendation and always add a UUID, regardless of existing IDs
            cost_recommendations = [
                {
                    **rec.as_dict(),
                    'uuid': str(uuid.uuid4()),  # Always generate a new UUID, independent of existing IDs
                    'RecommendationId': rec.id if rec.id else None,  # Keep original RecommendationId if present
                    'source': 'Azure API',
                    'subscription_id': subscription_id,  # Use the subscription_id
                    'impact': rec.impact if rec.impact else 'Unknown',  # Normalize impact
                    'resource_id': 'N/A'  # Include this in the response, even if not provided by SQL
                }
                for rec in recommendations if rec.category == 'Cost'
            ]
            
            all_cost_recommendations[subscription_id] = cost_recommendations
        except Exception as e:
            logger.error(f"Error fetching cost recommendations for subscription {subscription_id}: {str(e)}")
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
    
    Example 3:
    **Recommendation: Optimizing Costs with Reserved Instances**

    To optimize costs effectively using Reserved Instances in Azure, consider the following actions:
    

    1. **Analyze Usage Patterns**: Evaluate your historical usage patterns to identify stable workloads that can benefit from Reserved Instances. Focus on services with consistent demand to maximize savings.

    2. **Purchase Reserved Instances**: Once identified, purchase Reserved Instances for the appropriate services and regions. Leverage the Azure Hybrid Benefit for additional savings on Windows VMs.

    3. **Monitor and Adjust**: Regularly monitor your usage and adjust Reserved Instances as needed to align with changing workload requirements. Optimize your reservations to avoid underutilization.

    **Conclusion**: By strategically leveraging Reserved Instances based on usage patterns and monitoring your reservations, you can achieve significant cost savings in Azure.

    **Recommendation: Optimizing Costs for Orphaned Public IP:**

    1. **Audit Public IP Allocations**: Confirm the orphaned status of the public IP (appgw-pip) by reviewing its association with resources. Assess if it was meant for a service that is still under development or needs, which can justify keeping it.

    2. **Delete Orphaned Public IP**: If you confirm that the public IP is indeed orphaned and lacks any associated resource utility, delete it to eliminate the ongoing costs. This will help reduce unnecessary expenses.

    3. **Change Configuration to Dynamic Allocation (if needed)**: If you require a public IP for future use, consider changing its allocation method to dynamic instead of static. This ensures you avoid incurring costs when the IP isn’t in active use.

    **Conclusion**: Deleting the orphaned public IP (appgw-pip) will result in immediate cost savings since it currently incurs no costs but is a potential liability for future charges if left unutilized. If there's potential to need it in the future, consider using dynamic allocation to minimize expenses.    
   
    Example 4:

    To effectively address the recommendation regarding **unattached disks** and optimize costs, consider implementing the following actionable steps:

    1. **Audit Unattached Disks**: Review all unattached disks within the specified subscription (e9b4640d-1f1f-45fe-a543-c0ea45ac34c1) to confirm which disks are indeed unnecessary. Cross-reference these disks with active VMs to validate they are not tied to any future deployments.

    2. **Delete Unused Disks**: For the disks confirmed to have no ownership and no future use, proceed with deletion. This will immediately cease any unnecessary costs associated with these unattached disks.

    3. **Evaluate Downgrade Options**: For disks that may be needed for future use but are currently unattached, assess the feasibility of downgrading these disks to a Standard SKU. This will reduce ongoing costs while still keeping the disks available for potential future use.

    **Conclusion**: Given the medium impact of this recommendation and the modest savings of approximately $0.04 per hour, it is advisable to take action to optimize costs by auditing, deleting unnecessary disks, and considering downgrades where appropriate. While the immediate savings might be low, it supports overall cost management principles and reduces clutter in your Azure environment.
    """

    for rec in recommendations:
        # Handling SQL DB Recommendations
        # if rec.get('source') == 'SQL DB':
        #     problem = rec.get('short_description', {}).get('problem', 'No description available')
        #     solution = rec.get('action', 'No action available')
        #     impact = rec.get('impact', 'Unknown')
        #     subscription_id = rec.get('subscription_id', 'N/A')
        #     instance_name = rec.get('Instance', 'N/A')

        #     # Create prompt for SQL DB recommendations
        #     prompt = f"""
        #     As my Expert assistant with over 10 years of Azure consultant experience, you are here to help me make the best decision related to Cost Recommendations, I want you to analyze the following recommendation from SQL DB and provide specific, actionable advice on how to address it, making use of the extended properties as well to prioritize actions. In the end, give me your decision. Focus on cost optimization only and provide a maximum of 3 bulletpoints for action and conclude with a clear decision to take action or not.
        #     {few_shot_examples}
        #     Now, here is the recommendation:

        #     - Instance: {instance_name}
        #     - Problem: {problem}
        #     - Solution: {solution}
        #     - Impact: {impact}
        #     - Subscription ID: {subscription_id}
        #     - Instance Name: {instance_name}
        #     - Additional Info: {rec.get('additional_info', 'N/A')}

        #     Provide a maximum of 3 bullet points for actions to optimize costs + Conclude with a decision based on the information provided.
        #     """
        
        # Handling Azure API Recommendations
        if rec.get('source') == 'Azure API':
            problem = rec.get('short_description', {}).get('problem', 'No description available')
            solution = rec.get('short_description', {}).get('solution', 'No solution available')
            impact = rec.get('impact', 'Unknown')
            subscription_id = rec.get('extended_properties', {}).get('subId', rec.get('subscription_id', 'N/A'))

            # Create prompt for Azure API recommendations
            prompt = f"""
            As my Expert assistant with over 10 years of Azure consultant experience, you are here to help me make the best decision related to Cost Recommendations, I want you to analyze the following recommendation from SQL DB and provide specific, actionable advice on how to address it, making use of the extended properties as well to prioritize actions. In the end, give me your decision. Focus on cost optimization only and provide a maximum of 3 bulletpoints for action and conclude with a clear decision to take action or not.
            {few_shot_examples}
            Now, here is the recommendation:

            - Problem: {problem}
            - Solution: {solution}
            - Impact: {impact}
            - Subscription ID: {subscription_id}
            - Extended Properties: {rec.get('extended_properties', 'N/A')}

            Provide a maximum of 3 bullet points for actions to optimize costs and conclude with a decision based on the information provided with the extended properties.
            """
        
        # Handling Log Analytics Recommendations
        elif rec.get('source') == 'Log Analytics':
            problem = rec.get('problem', 'No problem description available')
            solution = rec.get('solution', 'No solution available')
            impact = rec.get('impact', 'Unknown')
            subscription_id = rec.get('subscription_id', 'N/A')
            instance_name = rec.get('Instance', 'N/A')
            savings_amount = rec.get('savingsAmount', 'N/A')
            annual_savings = rec.get('annualSavingsAmount', 'N/A')
            resource_id = rec.get('resource_id', 'N/A')

            # Create prompt for Log Analytics recommendations
            prompt = f"""
            {few_shot_examples}
            As my Expert assistant with over 10 years of Azure consultant experience, you are here to help me make the best decision related to Cost Recommendations, I want you to analyze the following recommendation from SQL DB and provide specific, actionable advice on how to address it, making use of the extended properties as well to prioritize actions. In the end, give me your decision. Focus on cost optimization only and provide a maximum of 3 bulletpoints for action and conclude with a clear decision to take action or not.
            Now, here is the recommendation:
            - Instance: {instance_name}
            - Problem: {problem}
            - Solution: {solution}
            - Impact: {impact}
            - Subscription ID: {subscription_id}
            - Savings Amount: {savings_amount}
            - Annual Savings: {annual_savings}
            - Resource ID: {resource_id}

            Provide a maximum of 3 bullet points for actions to optimize costs and conclude with a decision based on the information provided.
            """

        # Fallback for any other unknown sources (if any are added later)
        else:
            prompt = f"Unknown source recommendation. Please analyze manually."

        try:
            # Send prompt to OpenAI (GPT-4)
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
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



### API Endpoint to Fetch and Review Recommendations ###
@app.route('/api/review-recommendations', methods=['GET'])
def review_recommendations_route():
    try:
        azure_subscription_ids = ['e9b4640d-1f1f-45fe-a543-c0ea45ac34c1','34f635ef-9210-4e8f-b9a9-8c3327604b23','b26069e9-79e1-49d1-a47c-877dfdc1fb20','b640da53-da83-438f-8c1d-dbc3de526d65','6d03d786-1501-4575-8d34-643ceca8af07']
        # sql_subscription_id = '9d923c47-1aa2-4fc9-856f-16ca53e97b76'
        
        all_recommendations = []

        # Fetch recommendations from Azure Advisor
        azure_recommendations = []
        for subscription_id in azure_subscription_ids:
            try:
                advisor_recommendations = get_cost_recommendations([subscription_id])
                if isinstance(advisor_recommendations, dict):
                    for recommendations in advisor_recommendations.values():
                        if recommendations:
                            for rec in recommendations:
                                # Ensure subscription_id is included in each recommendation
                                if 'extended_properties' in rec and 'subid' in rec['extended_properties']:
                                    rec['subscription_id'] = rec['extended_properties']['subid']
                                else:
                                    rec['subscription_id'] = subscription_id  # Fallback to subscription_id if not found in extended properties
                                azure_recommendations.append(rec)
            except Exception as e:
                logger.error(f"Error fetching Azure Advisor recommendations for subscription {subscription_id}: {e}")
        
        # Fetch recommendations from SQL database
        # sql_recommendations = []
        # try:
        #     sql_recommendations = get_sql_recommendations()
        #     if not sql_recommendations:
        #         logger.warning(f"No recommendations found for SQL subscription: {sql_subscription_id}")
        #     else:
        #         # Ensure each SQL recommendation has the subscription_id set correctly
        #         for rec in sql_recommendations:
        #             if 'subscription_id' not in rec:
        #                 rec['subscription_id'] = sql_subscription_id
        # except Exception as e:
        #     logger.error(f"Error fetching SQL recommendations: {e}")
    
        # Fetch recommendations from Log Analytics
        log_analytics_recommendations = []
        try:
            # Example: Set a default client_id_key and timespan (30 days) for the Log Analytics query
            client_id_key = 'OTHER'  # This can be dynamic or static based on your needs
            timespan = timedelta(days=30)  # Fetch data for the last 30 days

            log_analytics_query = """
            AzureOptimizationRecommendationsV1_CL
            | where TimeGenerated >= ago(30d) and Category == "Cost"
            | extend additionalInfo = parse_json(AdditionalInfo_s)
            | project 
                problem = RecommendationDescription_s,  // Keep original name for recommendation
                impact = Impact_s , 
                solution = RecommendationAction_s,  // Keep original name for solution
                TimeGenerated,  // Keep original name for generated date
                SubscriptionGuid_g,  // Keep original name for subscription ID
                savingsAmount = additionalInfo.savingsAmount,  // Include savingsAmount as 
                annualSavingsAmount = additionalInfo.annualSavingsAmount,  // Include annualSavingsAmount as well
                InstanceName_g,  // Include instance name
                FitScore_d,
                resource_id = InstanceId_s
            | order by TimeGenerated desc
            """
            # Now pass the correct arguments: query, client_id_key, and timespan
            log_analytics_recommendations = get_log_analytics_data(query=log_analytics_query, client_id_key=client_id_key, timespan=timespan)
            # Add UUID and source to each recommendation
            for rec in log_analytics_recommendations:
                rec['uuid'] = str(uuid4())
                rec['source'] = 'Log Analytics'
                rec['subscription_id'] = rec.get('SubscriptionGuid_g', 'N/A')
                rec['impact'] = rec.get('impact', 'Unknown')
                rec['resource_id'] = rec.get('resource_id', 'N/A')  # Ensure resource_id is included

                # Normalize the structure to match other recommendations
                rec['additional_info'] = rec.get('savingsAmount', 'N/A')
                rec['Instance'] = rec.get('InstanceName_g', 'N/A')
                rec['problem'] = rec.get('problem', 'No problem description available')
                rec['solution'] = rec.get('solution', 'No solution description available')
                rec['fit_score'] = rec.get('FitScore_d', 'N/A')
                rec['annual_savings'] = rec.get('annualSavingsAmount', 'N/A')
            if not log_analytics_recommendations:
                logger.warning("No recommendations found from Log Analytics.")
        except Exception as e:
            logger.error(f"Error fetching Log Analytics recommendations: {e}")

        # Combine recommendations from all sources
        all_recommendations.extend(azure_recommendations)
        # all_recommendations.extend(sql_recommendations)
        all_recommendations.extend(log_analytics_recommendations)

        if not all_recommendations:
            logger.warning("No recommendations found from any source.")
            return jsonify({"message": "No recommendations available"}), 200

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

    advice = generate_advice_with_llm(recommendations)

    structured_data = []
    for rec, adv in zip(recommendations, advice):
        structured_data.append({
            'recommendation': rec,
            'advice': adv
        })

    return jsonify(structured_data), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)