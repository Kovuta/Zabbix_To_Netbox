import requests
import json
from dotenv import load_dotenv
import os


# Load keys using environment
load_dotenv("zab_net_tokens.env")

net_url = os.getenv("NETBOX_URL")
net_token = os.getenv("NETBOX_TOKEN")
headers = {"Authorization": f"Token {net_token}"}

def get_mapping(path, key_field, value_field):
    url = f"{net_url}{path}"
    mapping = {}
    
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict):
            results = data.get("results", [])
        elif isinstance(data, list):
            results = data
        else:
            print(f"Unexpected data format: {data}")
            break
        
        if not results:
            print(f"No results found for {path}")
            break
            
        for item in results:
            print(f"Processing item: {item}")
            if not item.get(key_field):
                print(f"Missing key_field '{key_field}' in item: {item}")
                continue
            if not item.get(value_field):
                print(f"Missing value_field '{value_field}' in item: {item}")
                continue
            mapping[item[key_field]] = item[value_field]
        if isinstance(data, dict):
            url = data.get("next") # Some pagination stuff
        else:
            url = none # no pagination

    return mapping

# Calling API to grab proper mappings
mappings = {
    "device_type_mapping": get_mapping("dcim/device-types/", "model", "id"),
    "site_mapping": get_mapping("dcim/sites/", "name", "id"),
    "tenant_mapping": get_mapping("tenancy/tenants/", "name", "id")
}

# Create a json file of the mappings for easy parsing
with open("mappings.json", "w") as f:
    json.dump(mappings, f, indent=4)
print("Mappings have been saved to mappings.json")