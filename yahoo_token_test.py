import json
import requests


# ---------------------------------------------------------
# LOAD CREDENTIALS
# ---------------------------------------------------------

with open("yahoo_credentials.json", "r") as file:
    credentials = json.load(file)


client_id = credentials["client_id"]
client_secret = credentials["client_secret"]
refresh_token = credentials["refresh_token"]


# ---------------------------------------------------------
# GET A NEW ACCESS TOKEN
# ---------------------------------------------------------

print()
print("Requesting a fresh Yahoo access token...")
print("=" * 50)

response = requests.post(
    "https://api.login.yahoo.com/oauth2/get_token",
    data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    },
)


print("Token response status:", response.status_code)

token_data = response.json()

if response.status_code != 200:
    print(token_data)
    raise SystemExit


print("Successfully received a new access token.")
print()


# ---------------------------------------------------------
# TEST YAHOO FANTASY API
# ---------------------------------------------------------

access_token = token_data["access_token"]

headers = {
    "Authorization": f"Bearer {access_token}",
}

url = (
    "https://fantasysports.yahooapis.com/"
    "fantasy/v2/users;use_login=1/"
    "?format=json"
)

print("Testing Yahoo Fantasy API...")
print("=" * 50)

api_response = requests.get(
    url,
    headers=headers,
)

print("Fantasy API status:", api_response.status_code)
print()

print(api_response.text[:2000])