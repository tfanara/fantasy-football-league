from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

print()
print("Testing yahoo_fantasy_api...")
print("=" * 50)

# Load Yahoo OAuth credentials
sc = OAuth2(None, None, from_file="OAuth.json")

print("OAuth loaded successfully.")

# Connect to Yahoo NFL
gm = yfa.Game(sc, "nfl")

print("Yahoo NFL Game object created.")

# Get leagues for the authenticated user
league_ids = gm.league_ids()

print()
print("Your NFL leagues:")
print("=" * 50)

for league in league_ids:
    print(league)

