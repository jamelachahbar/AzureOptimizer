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
import sys
import pymssql

# from agents.azure_tools import get_cost_data, get_cost_recommendations, llm_generate_advice
# Ensure the container and files exist at startup
ensure_container_and_files_exist()
# Configure OpenAI GPT-4 API (or Azure OpenAI) using your API keys and endpoint
openai.api_key = os.getenv("OPENAI_API_KEY")
# Configure OpenAI GPT-4 API (or Azure OpenAI) using your API keys and endpoint
matplotlib.use('Agg')  # Use a non-interactive backend


import pyodbc # Import the pyodbc module for SQL Server connectivity

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

def load_policies():
    """Load policies from the YAML file."""
    if os.path.exists(POLICIES_FILE):
        with open(POLICIES_FILE, 'r') as file:
            policies = yaml.safe_load(file) or {'policies': []}
            # Ensure all policies have an 'enabled' key
            for policy in policies['policies']:
                if 'enabled' not in policy:
                    policy['enabled'] = True  # Default to enabled
            return policies
    else:
        logger.error(f"Policies file not found at {POLICIES_FILE}")
        return {'policies': []}

def save_policies(policies):
    """Save policies to the YAML file."""
    with open(POLICIES_FILE, 'w') as file:
        yaml.safe_dump(policies, file)
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

from azure.identity import DefaultAzureCredential
from azure.mgmt.advisor import AdvisorManagementClient
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file
subscription_ids = os.getenv('AZURE_SUBSCRIPTION_ID').split(',')  # This will allow for multiple IDs

# Set up the credentials
credential = DefaultAzureCredential()

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

# def get_cost_recommendations(subscription_ids):
#     """
#     Fetch cost recommendations for multiple Azure subscriptions using Azure SDK.
#     This function uses the Azure SDK to fetch cost recommendations from Azure Advisor
#     for the specified list of subscription IDs. It filters the recommendations to only include
#     those in the 'Cost' category.
#     """
#     all_cost_recommendations = {}

#     for subscription_id in subscription_ids:
#         try:
#             client = AdvisorManagementClient(credential, subscription_id)
#             recommendations = client.recommendations.list()
#             cost_recommendations = [rec.as_dict() for rec in recommendations if rec.category == 'Cost']
            
#             # Log the content of the recommendations for debugging
#             logger.info(f"Cost Recommendations for Subscription {subscription_id}: {cost_recommendations}")
            
#             all_cost_recommendations[subscription_id] = cost_recommendations
#         except Exception as e:
#             logger.error(f"Error fetching cost recommendations for subscription {subscription_id}: {str(e)}")
#             all_cost_recommendations[subscription_id] = []

#     return all_cost_recommendations

# def generate_advice_with_llm(recommendations):
#     advice_list = []

#     for rec in recommendations:
#         # Safely access shortDescription, problem, and solution
#         short_description = rec.get('short_description', {})
#         problem = short_description.get('problem', 'No problem description provided.')
#         solution = short_description.get('solution', 'No solution description provided.')

#         # Generate the prompt
#         prompt = f"""
#         As an expert consultant, your task is to analyze the following Azure Advisor recommendation and provide
#         specific, actionable advice on how to address it, making use of the extended properties as well to prioritize actions. In the end, give me your decision. Focus on cost optimization only and provide a maximum of 3 bulletpoints for action and don't make it too long. Here is the recommendation:
        
#         - Category: {rec.get('category', 'Unknown')}
#         - Impact: {rec.get('impact', 'Unknown')}
#         - Problem: {problem}
#         - Solution: {solution}
#         - Extended Properties: {rec.get('extended_properties', 'Unknown')}

#         Please provide detailed advice on how to address this recommendation.
#         """

#         try:
#             logger.info(f"Sending prompt to OpenAI: {prompt}")
#             response = openai.ChatCompletion.create(
#                 model="gpt-4o-mini",
#                 messages=[
#                     {"role": "system", "content": "You are a skilled Azure consultant who knows everything about FinOps and Cost Optimization."},
#                     {"role": "user", "content": prompt}
#                 ]

#             )
#             logger.info(f"Received response from OpenAI: {response}")

#             if not response or not response.choices:
#                 logger.error("No valid response received from OpenAI.")
#                 advice_text = "No advice could be generated."
#             else:
#                 advice_text = response.choices[0].message["content"].strip()

#             if not advice_text:
#                 logger.error("Received empty advice from the AI.")
#                 advice_text = "No advice could be generated."

#             advice_list.append(advice_text)

#         except Exception as e:
#             logger.error(f"Error generating AI advice: {str(e)}")
#             advice_list.append(f"An error occurred: {str(e)}")

#     return advice_list



# @app.route('/api/analyze-recommendations', methods=['POST'])
# def analyze_recommendations_route():
#     data = request.get_json()
#     subscription_id = data.get('subscription_id')
#     impacted_resources = data.get('impacted_resources', [])

#     if not subscription_id:
#         return jsonify({'error': 'Missing subscription ID'}), 400

#     if not impacted_resources:
#         return jsonify({'error': 'Missing impacted resources'}), 400

#     try:
#         # Use the agent to analyze recommendations and impacted resources
#         prompt = f"Analyze cost recommendations and optimization for subscription {subscription_id} with the following impacted resources: {impacted_resources}."
        
#         # Pass the data as a prompt to the agent
#         response = agent.run(prompt)

#         return jsonify({'response': response}), 200
#     except Exception as e:
#         logger.error(f"Error analyzing recommendations: {str(e)}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/analyze-recommendations', methods=['POST'])
# def analyze_recommendations_route():
#     data = request.get_json()
#     subscription_id = data.get('subscription_id')  # Expect a single subscription ID
#     if not subscription_id:
#         return jsonify({'error': 'Missing subscription ID'}), 400

#     try:
#         # Fetch recommendations for the given subscription ID
#         recommendations = get_cost_recommendations([subscription_id])  # Pass as a list with a single ID

#         # Generate advice using the LLM
#         advice = generate_advice_with_llm(recommendations[subscription_id])

#         # Ensure the advice list is the correct length compared to the recommendations
#         if len(advice) != len(recommendations[subscription_id]):
#             logger.error(f"Mismatch between number of recommendations and AI advice for subscription {subscription_id}. Adjusting length...")
#             advice += ["No advice available"] * (len(recommendations[subscription_id]) - len(advice))  # Add placeholders if mismatch

#         # Convert the advice into a structured format for the frontend
#         structured_advice = []
#         for rec, adv in zip(recommendations[subscription_id], advice):  # Assuming the AI advice is split by double newline
#             short_description = rec.get('short_description', {})
#             problem = short_description.get('problem', 'No problem description provided.')
#             solution = short_description.get('solution', 'No solution description provided.')

#             structured_advice.append({
#                 "subscription_id": subscription_id,  # Include the subscription ID for clarity
#                 "category": rec.get("category", "Unknown"),
#                 "impact": rec.get("impact", "Unknown"),
#                 "short_description": {
#                     "problem": problem,
#                     "solution": solution,
#                 },
#                 "extended_properties": rec.get("extended_properties", {}),
#                 "advice": adv  # AI generated advice for this specific recommendation
#             })

#         logger.info(f"Structured Advice Sent to Frontend: {structured_advice}")
#         return jsonify({"advice": structured_advice}), 200
#     except Exception as e:
#         logger.error(f"Error analyzing recommendations: {str(e)}")
#         return jsonify({'error': str(e)}), 500




# Work In Progress
### Function to get recommendations from Azure API ###
def get_cost_recommendations(subscription_ids):
    all_cost_recommendations = {}

    for subscription_id in subscription_ids:
        try:
            client = AdvisorManagementClient(credential, subscription_id)
            recommendations = client.recommendations.list()
            cost_recommendations = [
                {
                    **rec.as_dict(),
                    'source': 'Azure API'  # Add source metadata
                }
                for rec in recommendations if rec.category == 'Cost'
            ]
            all_cost_recommendations[subscription_id] = cost_recommendations
        except Exception as e:
            logger.error(f"Error fetching cost recommendations for subscription {subscription_id}: {str(e)}")
            all_cost_recommendations[subscription_id] = []
    
    return all_cost_recommendations
### Function to get recommendations from SQL database ###
### Function to get recommendations from SQL database ###
def get_sql_recommendations():
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=aoejml-sql.database.windows.net,1433;"
        "DATABASE=azureoptimization;"
        "UID=azureadmin@aoejml-sql;"
        "PWD=Achahbar2019;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    query = """
    SELECT RecommendationId, Category, Impact, 
           RecommendationDescription, RecommendationAction, 
           InstanceName, SubscriptionGuid
    FROM dbo.Recommendations
    WHERE Category = 'Cost';
    """

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(query)

        recommendations = []
        for row in cursor.fetchall():
            recommendations.append({
                'RecommendationId': row.RecommendationId,
                'category': row.Category,  # Mapping SQL 'Category' to 'category'
                'impact': row.Impact if row.Impact else 'Unknown',  # Mapping SQL 'Impact' to 'impact'
                'short_description': {
                    'problem': row.RecommendationDescription if row.RecommendationDescription else 'No problem description available'  # Mapping SQL 'RecommendationDescription' to 'short_description.problem'
                },
                'action': row.RecommendationAction if row.RecommendationAction else 'No action available',  # Custom key for SQL 'RecommendationAction'
                'Instance': row.InstanceName,  # Custom field for instance name
                'subscription_id': row.SubscriptionGuid,  # Mapping SQL 'SubscriptionGuid' to 'subscription_id'
                'source': 'SQL DB'
            })
        conn.close()
        return recommendations

    except Exception as e:
        logger.error(f"Error fetching recommendations from SQL: {e}")
        return []


### LLM Advice Generation ###
MAX_TOKENS = 4000  # Adjust based on the LLM model limits

def generate_advice_with_llm(recommendations):
    advice_list = []

    for rec in recommendations:
        # Truncate problem and solution if needed
        problem = rec.get('Description', 'No description provided.')[:500]
        solution = rec.get('Action', 'No action provided.')[:500]

        # Generate prompt
        prompt = f"""
        As an Azure consultant, analyze the following recommendation and provide actionable steps to optimize costs:

        - Problem: {problem}
        - Solution: {solution}
        - Impact: {rec.get('Impact', 'Unknown')}
        - Source: {rec.get('source', 'Unknown')}

        Provide a maximum of 3 bullet points for actions to optimize costs.
        """

        try:
            # Check token length
            if len(prompt.split()) > MAX_TOKENS:
                raise ValueError("Input exceeds the maximum token length.")

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a skilled Azure consultant who knows everything about FinOps and Cost Optimization."},
                    {"role": "user", "content": prompt}
                ]
            )
            advice_text = response['choices'][0]['message']['content'].strip()

            if not advice_text:
                advice_text = "No advice could be generated."
            advice_list.append(advice_text)

        except openai.OpenAIError as e:
            logger.error(f"Error generating AI advice: {str(e)}")
            advice_list.append(f"An error occurred: {str(e)}")

        except ValueError as ve:
            logger.error(f"Prompt too long: {str(ve)}")
            advice_list.append("Prompt exceeds token limit.")
    
    return advice_list

### API Endpoint to Fetch and Review Recommendations ###
@app.route('/api/review-recommendations', methods=['GET'])
def review_recommendations_route():
    try:
        # Define the valid subscription IDs for both sources
        azure_subscription_ids = ['38c26c07-ccce-4839-b504-cddac8e5b09d', 'c916841c-459e-4bbd-aff7-c235ae45f0dd']  # Azure tenant subscription IDs
        sql_subscription_id = '9d923c47-1aa2-4fc9-856f-16ca53e97b76'  # SQL tenant subscription ID
        
        all_recommendations = []

        # Fetch recommendations from Azure Advisor
        azure_recommendations = []
        for subscription_id in azure_subscription_ids:
            try:
                advisor_recommendations = get_cost_recommendations([subscription_id])
                if isinstance(advisor_recommendations, dict):
                    for recommendations in advisor_recommendations.values():
                        if recommendations:  # Make sure it's not empty
                            azure_recommendations.extend(recommendations)
            except Exception as e:
                logger.error(f"Error fetching Azure Advisor recommendations for subscription {subscription_id}: {e}")
        
        # Fetch recommendations from SQL database
        sql_recommendations = []
        try:
            sql_recommendations = get_sql_recommendations()
            if not sql_recommendations:
                logger.warning(f"No recommendations found for SQL subscription: {sql_subscription_id}")
        except Exception as e:
            logger.error(f"Error fetching SQL recommendations: {e}")

        # Combine recommendations from both sources
        all_recommendations.extend(azure_recommendations)
        all_recommendations.extend(sql_recommendations)

        # Handle empty results from both sources
        if not all_recommendations:
            logger.warning("No recommendations found from either source.")
            return jsonify({"message": "No recommendations available"}), 200

        return jsonify(all_recommendations), 200

    except Exception as e:
        logger.error(f"Error fetching recommendations: {e}")
        return jsonify({'error': str(e)}), 500


### API Endpoint to Analyze Recommendations ###
@app.route('/api/analyze-recommendations', methods=['POST'])
def analyze_recommendations_route():
    data = request.get_json()
    subscription_id = data.get('subscription_id')

    if not subscription_id:
        return jsonify({'error': 'Missing subscription ID'}), 400

    try:
        # Fetch recommendations from both sources
        azure_recommendations = get_cost_recommendations([subscription_id])[subscription_id]
        sql_recommendations = get_sql_recommendations()

        # Merge both recommendation sources
        all_recommendations = azure_recommendations + sql_recommendations

        # Generate advice for all recommendations
        advice = generate_advice_with_llm(all_recommendations)

        # Structured response for frontend
        structured_advice = []
        for rec, adv in zip(all_recommendations, advice):
            structured_advice.append({
                "recommendation": rec,
                "advice": adv
            })

        return jsonify({"advice": structured_advice}), 200

    except Exception as e:
        logger.error(f"Error analyzing recommendations: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)