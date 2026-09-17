from yahoofantasy import Context

ctx = Context()

print()
print("Yahoo Fantasy Context created!")
print()

print("Testing 2026 NFL...")
print("=" * 50)

try:
    leagues = ctx.get_leagues("nfl", 2026)

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
    print(type(e).__name__)
    print(e)