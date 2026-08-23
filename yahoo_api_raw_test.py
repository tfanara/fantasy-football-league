import pickle
import requests
from pathlib import Path


# --------------------------------------------------
# Load Yahoo credentials
# --------------------------------------------------

credentials_file = Path(".yahoofantasy")

with open(credentials_file, "rb") as f:
    data = pickle.load(f)

auth = data["auth"]

access_token = auth["access_token"]


# --------------------------------------------------
# Test Yahoo Fantasy API
# --------------------------------------------------

url = "https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
}

print()
print("Testing Yahoo Fantasy API...")
print("=" * 50)

response = requests.get(url, headers=headers)

print("HTTP status:", response.status_code)
print()

if response.ok:
    print("SUCCESS!")
    print(response.text[:2000])
else:
    print("ERROR:")
    print(response.text)
