import logging
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.sql.models import DatabaseUpdate
from azure.mgmt.sql.models import Sku
from azure.mgmt.sql.models import Database  # Import the Database class

# Authentication
credential = DefaultAzureCredential()
subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')

# Client
sql_client = SqlManagementClient(credential, subscription_id)

def simple_scale_sql_database(sql_client, database, new_dtu, dry_run=True):
    """Simple function to scale a SQL database DTU without any conditions."""
    try:
        # Fetch the current SKU
        current_sku = database.sku

        logging.info(f"Database: {database.name}, Current DTU: {current_sku.capacity}")
        print(f"Database: {database.name}, Current DTU: {current_sku.capacity}")

        if new_dtu == current_sku.capacity:
            logging.info("Current DTU is already optimal.")
            return 'No Change', 'Current DTU is already optimal.'

        resource_group_name = database.id.split('/')[4]
        server_name = database.id.split('/')[8]
        database_name = database.name
        logging.info(f"Scaling SQL database {database.name} to {new_dtu} DTU.")

        # Update the SKU with the new DTU
        new_sku = Sku(name=current_sku.name, tier=current_sku.tier, capacity=new_dtu)

        update_parameters = Database(
            # Add the location property
            location=database.location,
            sku=new_sku,
            min_capacity=new_dtu
        )
        logging.info(f"Update parameters: {update_parameters}")

        if dry_run:
            logging.info("This is a dry run. No changes will be made.")
            return 'Dry Run', f'Would scale DTU to {new_dtu}.'
        else:
            # Apply the update
            sql_client.databases.begin_create_or_update(resource_group_name, server_name, database_name, update_parameters)
            return 'Success', f'Scaled DTU to {new_dtu}.'

    except Exception as e:
        logging.error(f"Error scaling SQL database {database.name}: {str(e)}")
        return 'Error', str(e)

def list_and_scale_databases(sql_client, new_dtu, dry_run=True):
    """List all SQL databases and attempt to scale them."""
    try:
        servers = sql_client.servers.list()
        for server in servers:
            resource_group_name = server.id.split('/')[4]
            server_name = server.name
            databases = sql_client.databases.list_by_server(resource_group_name, server_name)
            for database in databases:
                status, message = simple_scale_sql_database(sql_client, database, new_dtu, dry_run)
                logging.info(f"Scale status for {database.name}: {status} - {message}")
                print(f"Scale status for {database.name}: {status} - {message}")
    except Exception as e:
        logging.error(f"Failed to list and scale SQL databases: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    new_dtu = '10'  # Specify the DTU you want to scale to, changed for testing
    dry_run = False  # Change to False to apply changes
    list_and_scale_databases(sql_client, new_dtu, dry_run)
