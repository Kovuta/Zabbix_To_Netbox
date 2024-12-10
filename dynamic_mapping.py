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
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()["results"]
    for item in data:
        if not item.get(key_field) or not item.get(value_field):
            print(f"Skipping invalid item: {item}")
            continue
        mapping[item[key_field]] = item[value_field]

    
    mapping = {item[key_field]: item[value_field] for item in data}
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