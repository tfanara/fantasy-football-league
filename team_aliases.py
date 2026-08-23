TEAM_ALIASES = {
    # Same franchise, renamed after 2018
    "PickUpYourBratsMalle": "ThreatLevelMidnight",

    # Same franchise, renamed after 2023
    "You Better Park It": "Buttermilk Puuump",
}


def canonical_team(name):
    """
    Convert a historical team name to the franchise's
    current/final canonical name.
    """
    if name is None:
        return None

    name = str(name).strip()

    return TEAM_ALIASES.get(name, name)
