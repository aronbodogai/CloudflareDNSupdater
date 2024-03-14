import requests
import json
import logging
import re


# Set your authentication details
auth_email = ""                         # The email used to login 'https://dash.cloudflare.com'
auth_method = ""                        # Set to "global" for Global API Key or "token" for Scoped API Token
auth_key = ""                           # add 'Bearer ' in front of the key
zone_identifier = ""                    # Can be found in the "Overview" tab of your domain
record_name = ""                        # Which record you want to be synced
ttl = "1"
proxy = False
sitename = ""
slackchannel = ""                       # Slack Channel #example
slackuri = ""
discorduri = ""                         # URI for Discord WebHook "https://discordapp.com/api/webhooks/xxxxx"

# Logging setup
logging.basicConfig(filename='ddns_updater.log', level=logging.INFO)

# Check public IP
ipv4_regex = r'([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\.([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\.([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\.([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])'
try:
    ip = requests.get('https://api.ipify.org').text.strip()
except requests.RequestException:
    ip = requests.get('https://ipv4.icanhazip.com').text.strip()

# Check IP format
if not re.match(ipv4_regex, ip):
    logging.error("DDNS Updater: Failed to find a valid IP.")
    exit(2)

# Set auth header
if auth_method == "global":
    auth_header = "X-Auth-Key"
else:
    auth_header = "Authorization"

# Get existing IP
headers = {
    'X-Auth-Email': auth_email,
    auth_header: auth_key,
    'Content-Type': 'application/json'
}
params = {
    'type': 'A',
    'name': record_name
}
response = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_identifier}/dns_records", headers=headers, params=params)

record = response.json()
# Check if the domain has an A record
if "result" not in record or len(record["result"]) == 0:
    logging.error(f"DDNS Updater: Record does not exist, perhaps create one first? ({ip} for {record_name})")
    exit(1)


old_ip = record["result"][0]["content"]

# Compare IPs
if ip == old_ip:
    logging.info(f"DDNS Updater: IP ({ip}) for {record_name} has not changed.")
    exit(0)

record_identifier = record["result"][0]["id"]

# Update IP@Cloudflare
data = {
    'type': 'A',
    'name': record_name,
    'content': ip,
    'ttl': ttl,
    'proxied': proxy
}
response = requests.patch(f"https://api.cloudflare.com/client/v4/zones/{zone_identifier}/dns_records/{record_identifier}", headers=headers, json=data)
update = response.json()
# Report status
if update["success"]:
    logging.info(f"DDNS Updater: {ip} {record_name} DDNS updated.")
    message = f"{sitename} Updated: {record_name}'s new IP Address is {ip}"
else:
    logging.error(f"DDNS Updater: {ip} {record_name} DDNS failed for {record_identifier} ({ip}). DUMPING RESULTS:\n{update}")
    message = f"{sitename} DDNS Update Failed: {record_name}: {record_identifier} ({ip})."

if slackuri:
    slack_data = {
        "channel": slackchannel,
        "text": message
    }
    requests.post(slackuri, json=slack_data)

if discorduri:
    discord_data = {
        "content": message
    }
    requests.post(discorduri, json=discord_data)
