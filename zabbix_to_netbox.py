import requests
import json
import re
from dotenv import load_dotenv
import os
import subprocess
import sys

# Run dynamic mapper!
subprocess.run([sys.executable, "dynamic_mapping.py"], check=True) # sys.executable is for fixing python path issues
with open("mappings.json", "r") as f:
    mappings = json.load(f)
    
device_type_mapping = mappings.get("device_type_mapping", {})
site_mapping = mappings.get("site_mapping", {})
tenant_mapping = mappings.get("tenant_mapping", {})

# Load environment
load_dotenv("zab_net_tokens.env")

net_URL = os.getenv("NETBOX_URL")
net_TOKEN = os.getenv("NETBOX_TOKEN")

zabbix_URL = os.getenv("ZABBIX_URL")
zabbix_TOKEN = os.getenv("ZABBIX_TOKEN")


def create_device(device):
    device_type_id = device_type_mapping.get(device["model"])
    site_id = site_mapping.get(device["site"])
    tenant_id = tenant_mapping.get(device["tenant"])
    
    if not device_type_id:
        print(f"Device type not found for model: {device['model']}")
        return
    if not site_id:
        print(f"Site not found: {device['site']}")
        return
    if not tenant_id:
        print(f"Customer not found: {device['tenant']}")
        return
        
    payload = {
            "name": device["name"],
            "device_type": device_type_id,
            "tenant": tenant_id,
            "site": site_id,
            "primary_ip4": device["ip"]
        }
    
    response = requests.post(f"{net_URL}dcim/devices/", headers=headers, json=payload)
    if response.status_code == 201:
        print(f"Successfully Added: {device['name']} ({device['ip']})")
    elif response.status_code == 400:
        print(f"Already exists or error: {device['name']} ({device['ip']})")
        print(f"Error Reason: {response.text}")
    else:
        print(f"Failed to add {device['name']} - {response.status_code}: {response.text}")
        
        
    return payload


def get_zabbix_hosts():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {zabbix_TOKEN}"
    }
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": "extend",
            "selectInterfaces": ["ip"]
        },
        "id": 1
    }
    
    response = requests.post(zabbix_URL, json=payload, headers=headers, verify=False)

    if response.status_code == 200:
        try:
            hosts = response.json().get("result", [])
            parsed_hosts = []
            for host in hosts:
                if "interfaces" in host and len(host["interfaces"]) > 0:
                    ip = host["interfaces"][0].get("ip")
                    if ip:
                        parsed_hosts.append({"name": host["host"], "ip": ip})
            return parsed_hosts
        except Exception as e:
            print(f"Error Parsing Response: {e}")
    else:
        print(f"Error fetching Zabbix hosts: {response.text}")
        return []
        
        
        
def parse_hostname(hostname):
    # Check which hosts are causing issues or invalids
    if not hostname:
        print("Invalid Hostname:", hostname)
        return None
    
    # Is device router or PTP? Skipping others for now
    router_pattern = r"^(?P<customer>.+?) - (?P<site>.+?) - (?P<model>.+?)$"
    ptp_pattern = r"^(?P<customer>.+?) - (?P<link>.+?) - (?P<site>.+?) - (?P<model>.+?)$"
    
    print("Parsing Hostname:", hostname)
     
    # Matching hostname to router
    router_match = re.match(router_pattern, hostname)
    if router_match:
        return {
            "type": "router",
            "customer": router_match.group("customer"),
            "site": router_match.group("site"),
            "model": router_match.group("model")
        }
    
    # Matching hostname to ptp radio
    ptp_match = re.match(ptp_pattern, hostname)
    if ptp_match:
        return {
            "type": "ptp",
            "customer": ptp_match.group("customer"),
            "link": ptp_match.group("link"),
            "site": ptp_match.group("site"),
            "model": ptp_match.group("model")
            }
        
    return {
        "type": "unknown",
        "customer": "unknown",
        "site": "unknown",
        "model": "unknown",
        "original_name": hostname
        }
        
        
def handle_unknown(host):
    print(f"Unknown format for host: {host['name']}")
    return {
        "type": "unknown",
        "customer": "unknown",
        "site": "unknown",
        "model": "unknown",
        "original_name": host["name"],
        "ip": host["ip"]
    }
    

def fill_netbox(devices):
    headers = {
        "Authorization": f"Token {net_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for device in devices:
        if device is None or "name" not in device or "ip" not in device:
            print("Skipping invalid device:", device)
            continue
            
        print(f"Processing device: {device['name']}, IP: {device['ip']}")
        
        parsed = parse_hostname(device["name"])
        if not parsed or parsed["type"] == "unknown":
            print(f"Skipping device due to invalid parsed data: {device['name']}")
            continue # We are skipping outliers ( can add manually )
        
        print(f"Processing parsed device: {parsed}")
            
        create_device(parsed)


def main():
    print ("Fetching data from Z7...")
    zabbix_hosts = get_zabbix_hosts()
    if zabbix_hosts:
        parsed_hosts = []
        for host in zabbix_hosts:
            parsed_data = parse_hostname(host["name"])
            if "name" in host and "ip" in host:
                print("Adding host:", host)
                parsed_hosts.append({"name": host["name"], "ip":host["ip"]})
            else:
                print("Skipping host due to missing keys:", host)
            
        print(f"Found {len(parsed_hosts)} hosts. Sending to NetBox...")
        fill_netbox(parsed_hosts)
    else:
        print("No hosts found or an error occurred.")
        
        
    print("Migration Complete.")

if __name__ == "__main__":
    main()