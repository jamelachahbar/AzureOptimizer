import logging
import time
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.sql.models import Sku, Database
import textwrap
from prettytable import PrettyTable
from termcolor import colored
from datetime import datetime

def wrap_text(text, width=30):
    """Wrap text to a given width."""
    return "\n".join(textwrap.wrap(text, width))

def simple_scale_sql_database(sql_client, database, new_dtu, min_dtu, max_dtu, dry_run=True):
    """Simple function to scale a SQL database DTU without any conditions."""
    try:
        # Fetch the current SKU
        current_sku = database.sku

        logging.info(f"Database: {database.name}, Current DTU: {current_sku.capacity}")
        print(f"Database: {database.name}, Current DTU: {current_sku.capacity}")

        if new_dtu == current_sku.capacity:
            logging.info("Current DTU is already optimal.")
            return 'No Change', 'Current DTU is already optimal.'
        
        # Ensure new DTU is within min and max limits
        if new_dtu < min_dtu:
            new_dtu = min_dtu
        elif new_dtu > max_dtu:
            new_dtu = max_dtu

        resource_group_name = database.id.split('/')[4]
        server_name = database.id.split('/')[8]
        database_name = database.name
        logging.info(f"Scaling SQL database {database.name} to {new_dtu} DTU.")

        # Check if the new DTU is valid for the current tier
        valid_dtus = {
            'Standard': [10, 20, 50, 100, 200, 400, 800, 1200, 1600, 2000, 3000, 4000],
            'Premium': [125, 250, 500, 1000, 1750, 2000, 3000, 4000]
        }
        if new_dtu not in valid_dtus[current_sku.tier]:
            logging.error(f"DTU {new_dtu} is not valid for tier {current_sku.tier}.")
            return 'Error', f'DTU {new_dtu} is not valid for tier {current_sku.tier}.'

        # Update the SKU with the new DTU
        new_sku = Sku(name=current_sku.name, tier=current_sku.tier, capacity=new_dtu)

        update_parameters = Database(
            location=database.location,
            sku=new_sku,
            min_capacity=new_dtu
        )
        logging.info(f"Update parameters: {update_parameters}")

        if dry_run:
            logging.info("This is a dry run. No changes will be made.")
            return 'Dry Run', f'Would scale DTU to {new_dtu}.'
        else:
            sql_client.databases.begin_create_or_update(resource_group_name, server_name, database_name, update_parameters).result()
            # Apply the update but print operation is in progress every 10 seconds
            while True:
                database = sql_client.databases.get(resource_group_name, server_name, database_name)
                if database.sku.capacity == new_dtu:
                    break
                else:
                    logging.info("Operation in progress...")
                    time.sleep(10)
    
            logging.info(f"Database {database.name} scaled to {new_dtu} DTU.")
            return 'Success', f'Scaled DTU to {new_dtu}.'

    except Exception as e:
        logging.error(f"Error scaling SQL database {database.name}: {str(e)}")
        return 'Error', str(e)
    
def scale_databases_based_on_policy(sql_client, policies, dry_run=True):
    """Scale SQL databases based on provided policies."""
    impacted_resources = []
    try:
        for policy in policies:
            if policy['resource'] == 'azure.sql':
                for action in policy['actions']:
                    if action['type'] == 'scale_dtu':
                        tiers = action['tiers']
                        servers = sql_client.servers.list()
                        for server in servers:
                            resource_group_name = server.id.split('/')[4]
                            server_name = server.name
                            databases = sql_client.databases.list_by_server(resource_group_name, server_name)
                            for database in databases:
                                for tier in tiers:
                                    if tier['name'] in database.sku.name:
                                        # Convert off-peak times and current time to datetime objects
                                        off_peak_start = datetime.strptime(tier['off_peak_start'], "%H:%M").time()
                                        off_peak_end = datetime.strptime(tier['off_peak_end'], "%H:%M").time()
                                        current_time = datetime.now().time()

                                        # Check if current time is within off-peak period
                                        if off_peak_start < off_peak_end:
                                            is_off_peak = off_peak_start <= current_time < off_peak_end
                                        else:  # Over midnight
                                            is_off_peak = not (off_peak_end <= current_time < off_peak_start)

                                        # Set new_dtu based on whether it's off-peak
                                        new_dtu = tier['off_peak_dtu'] if is_off_peak else tier['peak_dtu']
                                        min_dtu = tier['min_dtu']
                                        max_dtu = tier['max_dtu']
                                        status, message = simple_scale_sql_database(sql_client, database, new_dtu, min_dtu, max_dtu, dry_run)
                                        # If the dtu would scale, add it to the impacted resources list
                                        if status != 'No Change':
                                            impacted_resources.append({
                                                'policy': 'scale-sql-database-dtu',
                                                'resource': database.name,
                                                'action': f'Scale DTU to {new_dtu}',
                                                'status': status,
                                                'message': message
                                            })

                                        print(f"Scale status for {database.name}: {status} - {message}")
  
        # Print the impacted resources only if impacted
        if impacted_resources == []:
            print(colored("No impacted resources for scale-sql-database-dtu policy.", "green", attrs=["bold"]))
        else:
            changes_table = PrettyTable()
            changes_table.field_names = ["Policy", "Resource", "Actions", "Status", "Message"]
            changes_table.align["Policy"] = "l"
            changes_table.align["Resource"] = "l"
            changes_table.align["Actions"] = "l"
            changes_table.align["Status"] = "l"
            changes_table.align["Message"] = "l"

            for resource in impacted_resources:
                changes_table.add_row([
                    wrap_text(resource['policy']),
                    wrap_text(resource['resource']),
                    wrap_text(resource['action']),
                    wrap_text(resource['status']),
                    wrap_text(resource['message'])
                ])

            print("\n")
            print(colored("Impacted Resources for scale-sql-database-dtu policy :", "cyan", attrs=["bold"]))
            print(colored(changes_table.get_string(), "cyan"))

    except Exception as e:
        logging.error(f"Failed to scale SQL databases based on policy: {e}")

