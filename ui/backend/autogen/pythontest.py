from azure.monitor.query import LogsQueryClient
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta
import pytz
import logging
from typing import List, Dict

# Replace with your workspace GUID
workspace_id = "608cd3e5-cf6b-4fa0-ac79-b5db5136c18f"  # This should be the Workspace GUID, not the full ARM path

def query_resource_logs(workspace_id: str, query: str, days: int = 1) -> List[Dict]:
    """
    Queries Azure Monitor logs for the Log Analytics Workspace.

    Args:
        workspace_id (str): The Log Analytics Workspace GUID.
        query (str): The KQL query to run on the log data.
        days (int): The number of days to query logs for.

    Returns:
        List[Dict]: The logs data as a list of dictionaries.
    """
    print(f"Querying logs for workspace: {workspace_id} for the last {days} day(s)")
    
    credential = DefaultAzureCredential()
    logs_client = LogsQueryClient(credential)

    # Calculate start and end time for the query
    utc = pytz.UTC
    end_time = utc.localize(datetime.utcnow())  # Explicitly add UTC timezone
    start_time = end_time - timedelta(days=days)

    print(f"Start time: {start_time}, End time: {end_time}")

    # Initialize an empty list to store the log data
    log_data = []

    try:
        # Query Azure Monitor Logs using the workspace GUID and provided query
        print("Running query in workspace...")
        response = logs_client.query_workspace(
            workspace_id=workspace_id,  # Use the Workspace GUID, not the full ARM path
            query=query,
            timespan=(start_time, end_time)  # Using the start and end time as a tuple
        )

        print("Query executed. Processing the response...")

        # Debugging: Print the structure of the response
        print(f"Response: {response}")
        for table in response.tables:
            print(f"Table: {table}")
            print(f"Columns: {table.columns}")  # Check column names
            print(f"Rows: {table.rows}")        # Check the rows content

            if table.rows:
                print(f"Table found with {len(table.rows)} rows.")
                for row in table.rows:
                    # Process the row data
                    log_data.append({col.name: val for col, val in zip(table.columns, row)})

        if log_data:
            print("Log data found and processed.")
        else:
            print("No logs found in the query.")

        return log_data

    except Exception as e:
        logging.error(f"Error querying logs for workspace {workspace_id}: {e}")
        return []

# Example usage of the function with a dynamic query
# kql_query = """
# AzureDiagnostics
# | where TimeGenerated > ago(1d)
# | limit 10
# """

# The LLM agent can generate or modify this query dynamically
logs = query_resource_logs(workspace_id, query=kql_query, days=1)

if logs:
    print("Logs retrieved:")
    for log in logs:
        print(log)
else:
    print("No logs retrieved or an error occurred.")
