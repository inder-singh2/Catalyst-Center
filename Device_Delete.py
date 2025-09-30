import pandas as pd
from dnacentersdk import DNACenterAPI
import time
import requests

requests.packages.urllib3.disable_warnings()

# Configuration - Update these with your DNAC details
DNAC_HOST = ''  # Replace with your DNAC URL
USERNAME = ''  # DNAC username
PASSWORD = ''  # DNAC password
EXCEL_FILE = 'File.xlsx'  # Path to your Excel file
HOSTNAME_COLUMN = 'hostname'

def check_task_status(dnac, task_id):
    max_attempts = 10
    for _ in range(max_attempts):
        try:
            task = dnac.task.get_task_by_id(task_id)
            if task.response.isError:
                return False, task.response.failureReason or "Unknown error"
            if task.response.progress == "Completed":
                return True, "Device deleted successfully"
            time.sleep(2)  # Wait before retrying
        except Exception as e:
            return False, f"Error checking task status: {e}"
    return False, "Task did not complete in time"

def delete_devices_from_dnac():
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
            # Get device list filtered by hostname (exact match)
            devices = dnac.devices.get_device_list(hostname=hostname)
            
            if not devices or not devices.response:
                print(f"Device '{hostname}' not found in DNAC.")
                continue
            
            # Assuming hostname is unique; take the first match
            device = devices.response[0]
            device_id = device.id
            print(f"Found device '{hostname}' with ID: {device_id}")
            
            # Delete the device using correct parameter 'id'
            result = dnac.devices.delete_device_by_id(id=device_id)
            print(f"Deletion initiated for '{hostname}'. Task ID: {result.response.taskId}")
            
            # Check task status
            success, message = check_task_status(dnac, result.response.taskId)
            print(f"Deletion status for '{hostname}': {message}")
            
            # Brief pause to avoid rate limiting
            time.sleep(5)
            
        except Exception as e:
            print(f"Error processing device '{hostname}': {e}")

if __name__ == "__main__":
    delete_devices_from_dnac()
