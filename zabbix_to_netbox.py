import requests
import json
import re

z_URL = "https://172.31.69.12/zabbix/api_jsonrpc.php"
z_token = "22c05403161e726b36da2dfaaeeb3b783758c1a8161aa2ec69150fca39b06327"

net_URL = "http://172.31.69.20:8000/api/"
net_token = "0123456789abcdef0123456789abcdef01234567"

def get_zabbix_hosts():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {z_token}"
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
    
    #payload_json = json.dumps(payload)
    
    response = requests.post(z_URL, json=payload, headers=headers, verify=False)
    
    #print("URL is:", z_URL)
    #print("Payload is (JSON):", payload_json)
    #print("Code:", response.status_code)
    
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
        except exception as e:
            print(f"Error Parsing Response: {e}")
    else:
        print(f"Error fetching Zabbix hosts: {response.text}")
        return []
        
        
        
def parse_hostname(hostname):
    router_pattern = r"^(?P<customer>.+?) - (?P<site>.+?) - (?P<model>.+?)$"
    ptp_pattern = r"^(?P<customer>.+?) - (?P<link>.+?) - (?P<site>.+?) - (?P<model>.+?)$"
    
    router_match = re.match(router_pattern, hostname)
    if router_match:
        return {
            "type": "router",
            "customer": router_match.group("customer"),
            "site": router_match.group("site"),
            "model": router_match.group("model")
        }
        
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
        "Authorization": f"Token {net_token}",
        "Content-Type": "application/json"
    }
    
    for device in devices:
        parsed = parse_hostname(device["name"])
        
        if parsed["type"] == "unknown":
            parsed = handle_unknown(device)
            
        device_data = {
            "name": device["name"],
            "device_role": parsed.get("type", "unknown"),
            "device_type": parsed.get("model", "unknown"),
            "site": parsed.get("site", "unknown"),
            "status": "active"
        }
        
        if parsed["type"] == "ptp":
            device_data["custom_field_link_number"] = parsed.get("link", "unknown")
            
        response = requests.post(f"{net_URL}dcim/devices/", headers=headers, json=device_data)
        
        if response.status_code == 201:
            print(f"Added: {device['name']} ({device['ip']})")
        elif response.status_code == 400:
            print(f"Already exists or error: {device['name']} ({device['ip']})")
            print(f"Error Reason: {response.text}")
        else:
            print(f"Failed to add {device['name']} - {response.status_code}")


def main():
    print ("Fetching data from Z7...")
    zabbix_hosts = get_zabbix_hosts()
    if zabbix_hosts:
        parsed_hosts = []
        for host in zabbix_hosts:
            parsed_data = parse_hostname(host["name"])
            parsed_hosts.append(parsed_data)
            
        print(f"Found {len(parsed_hosts)} hosts. Sending to NetBox...")
        fill_netbox(parsed_hosts)
    else:
        print("No hosts found or an error occurred.")
        

if __name__ == "__main__":
    main()