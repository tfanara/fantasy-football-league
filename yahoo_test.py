import json

from yfpy.query import YahooFantasySportsQuery


# ---------------------------------------------------------
# LOAD PRIVATE CREDENTIALS
# ---------------------------------------------------------

with open("yahoo_credentials.json", "r") as file:
    credentials = json.load(file)


consumer_key = credentials["consumer_key"]
consumer_secret = credentials["consumer_secret"]


# ---------------------------------------------------------
# CONNECT TO YAHOO
# ---------------------------------------------------------

yahoo_query = YahooFantasySportsQuery(
    league_id="",
    game_code="nfl",
    game_id=449,
    yahoo_consumer_key=consumer_key,
    yahoo_consumer_secret=consumer_secret,
)


# ---------------------------------------------------------
# TEST CURRENT USER
# ---------------------------------------------------------

print("\nTesting Yahoo Fantasy API...")
print("--------------------------------")

try:

    user = yahoo_query.get_current_user()

    print("SUCCESS!")
    print(user)

except Exception as e:

    print("Yahoo API request failed:")
    print(e)