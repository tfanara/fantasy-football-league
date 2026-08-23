from yahoofantasy import Context


# ---------------------------------------------------------
# CREATE AUTHENTICATED YAHOO CONTEXT
# ---------------------------------------------------------

ctx = Context()


print()
print("Yahoo Fantasy Context created!")
print()


# ---------------------------------------------------------
# TEST 2025 NFL
# ---------------------------------------------------------

print("Testing 2025 NFL...")
print("=" * 50)

try:
    leagues = ctx.get_leagues("nfl", 2025)

    print()
    print(f"Found {len(leagues)} league(s):")
    print()

    for league in leagues:
        print(
            f"{league.id} | "
            f"{league.name} | "
            f"{league.league_type}"
        )

except Exception as e:
    print()
    print("ERROR:")
    print(e)