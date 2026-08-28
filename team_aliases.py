TEAM_ALIASES = {

    # ---------------------------------------------------------
    # THREATLEVELMIDNIGHT FRANCHISE
    # ---------------------------------------------------------

    # 2017 historical name
    "PickUpYourBratsMalle": "ThreatLevelMidnight",


    # ---------------------------------------------------------
    # POST MAHOMES FRANCHISE
    # ---------------------------------------------------------

    # 2017 historical name
    "Little Red Fournette": "Post Mahomes",


    # ---------------------------------------------------------
    # JOE MANTEGNA FRANCHISE
    # ---------------------------------------------------------

    # 2017 historical name
    "Ur The Best Bellows": "Joe Mantegna",


    # ---------------------------------------------------------
    # BUTTERMILK PUUUMP FRANCHISE
    # ---------------------------------------------------------

    # Historical names
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",

}


def canonical_team(name):
    """
    Convert a historical team name to the franchise's
    current/final canonical name.

    Team names not listed in TEAM_ALIASES remain unchanged.
    This intentionally leaves one-season franchises such as
    Hello Harvard as their own franchise.
    """

    if name is None:
        return None

    name = str(name).strip()

    return TEAM_ALIASES.get(name, name)
