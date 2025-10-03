import pandas as pd
from dnacentersdk import DNACenterAPI
import time
import requests

requests.packages.urllib3.disable_warnings()

# Configuration
DNAC_HOST = ''
USERNAME = ''
PASSWORD = ''
EXCEL_FILE = 'removal.xlsx'
HOSTNAME_COLUMN = 'hostname'

def check_task_status(dnac, task_id):
    max_attempts = 30  # 60 seconds total (30 * 2s)
    interval = 2  # Seconds between polls

    for attempt in range(1, max_attempts + 1):
        try:
            task = dnac.task.get_task_by_id(task_id)
            task_response = task.response
            print(f"Task {task_id} (attempt {attempt}/{max_attempts}): {task_response}")

            # Check for error
            if task_response.get('isError', False):
                return False, f"Task failed: {task_response.get('failureReason', 'Unknown error')}"

            # Check for completion
            if task_response.get('endTime') or 'completed' in task_response.get('progress', '').lower():
                return True, "Device deleted successfully"

            time.sleep(interval)
        except Exception as e:
            return False, f"Error checking task status: {e}"
    
    return False, f"Task did not complete in {max_attempts * interval} seconds"

def check_provisioning_status(dnac, device_id):
    try:
        device = dnac.devices.get_device_by_id(id=device_id)
        return device.response.get('managementStatus') in ['MANAGED', 'PROVISIONED'] or bool(device.response.get('siteId'))
    except Exception as e:
        print(f"Error checking provisioning status for device {device_id}: {e}")
        return False

def delete_devices_from_dnac():
    # Initialize DNAC API
    try:
        dnac = DNACenterAPI(base_url=DNAC_HOST, username=USERNAME, password=PASSWORD, version='2.3.7.9', verify=False)
    except Exception as e:
        print(f"Error connecting to DNAC: {e}")
        return
    
    # Read hostnames from Excel
    try:
        df = pd.read_excel(EXCEL_FILE)
        hostnames = df[HOSTNAME_COLUMN].dropna().tolist()
        print(f"Loaded {len(hostnames)} hostnames from Excel: {hostnames}")
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return
    
    for hostname in hostnames:
        try:
            # Get device by hostname
            devices = dnac.devices.get_device_list(hostname=hostname)
            if not devices or not devices.response:
                print(f"Device '{hostname}' not found in DNAC.")
                continue
            
            device = devices.response[0]
            device_id = device.id
            print(f"Found device '{hostname}' with ID: {device_id}")
            
            # Check provisioning status
            if check_provisioning_status(dnac, device_id):
                print(f"Warning: Device '{hostname}' is provisioned. Attempting to unprovision first.")
                try:
                    dnac.devices.unprovision_devices(deviceIds=[device_id])
                    print(f"Unprovisioning initiated for '{hostname}'. Waiting 10s for stability.")
                    time.sleep(10)  # Wait for unprovisioning to stabilize
                except Exception as e:
                    print(f"Failed to unprovision '{hostname}': {e}. Skipping deletion.")
                    continue
            
            # Delete the device
            result = dnac.devices.delete_device_by_id(id=device_id, clean_config=True)
            print(f"Deletion initiated for '{hostname}'. Task ID: {result.response.taskId}")
            
            # Check task status
            success, message = check_task_status(dnac, result.response.taskId)
            print(f"Deletion status for '{hostname}': {message}")
            
            # Verify deletion
            devices = dnac.devices.get_device_list(hostname=hostname)
            if not devices.response:
                print(f"Verified: Device '{hostname}' no longer exists in DNAC.")
            else:
                print(f"Warning: Device '{hostname}' still exists in DNAC.")
            
            time.sleep(5)
        except Exception as e:
            print(f"Error processing device '{hostname}': {e}")

if __name__ == "__main__":
    delete_devices_from_dnac()
