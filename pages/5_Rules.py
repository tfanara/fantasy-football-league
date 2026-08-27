import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="League Rules | Malle's League",
    page_icon="📜",
    layout="wide",
)


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1400px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }

        .rules-hero {
            padding: 1.6rem 1.8rem;
            border-radius: 18px;
            background: linear-gradient(
                135deg,
                rgba(30, 41, 59, 0.98),
                rgba(15, 23, 42, 0.98)
            );
            color: white;
            margin-bottom: 1.4rem;
        }

        .rules-hero h1 {
            margin: 0;
            font-size: 2.25rem;
            font-weight: 800;
        }

        .rules-hero p {
            margin: .45rem 0 0 0;
            color: #cbd5e1;
            font-size: 1rem;
        }

        .rule-card {
            padding: 1rem 1.1rem;
            border-radius: 14px;
            background: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.18);
            margin-bottom: .8rem;
        }

        .rule-card strong {
            font-size: 1.02rem;
        }

        .small-note {
            color: #64748b;
            font-size: .9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="rules-hero">
        <h1>📜 League Constitution</h1>
        <p>
            The official rules governing Malle Is The Worst Commissioner.
            Where Yahoo settings are specifically referenced, Yahoo controls.
            Where league-specific rules apply, this page controls.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# QUICK FACTS
# ============================================================

st.header("🏈 League Basics")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Founded", "2017")
c2.metric("Teams", "12")
c3.metric("Annual Dues", "$100")
c4.metric("Prize Pool", "$1,200")
c5.metric("Current Season", "2026")

st.markdown(
    """
**League Name:** Malle Is The Worst Commissioner

**League Type:** 12-team fantasy football league

Managers are responsible for knowing the rules on this page and the applicable
Yahoo league settings. "I didn't know" remains a weak legal defense.
"""
)


# ============================================================
# DUES + PAYOUTS
# ============================================================

st.divider()

st.header("💰 League Dues & Payouts")

st.markdown(
    """
Each franchise owes **$100 per season**.

With 12 teams, the total annual prize pool is:

## **$1,200**
"""
)

p1, p2, p3 = st.columns(3)

with p1:
    st.metric(
        "🥇 1st Place",
        "$720",
    )
    st.caption("60% of the total prize pool")

with p2:
    st.metric(
        "🥈 2nd Place",
        "$360",
    )
    st.caption("30% of the total prize pool")

with p3:
    st.metric(
        "🥉 3rd Place",
        "$120",
    )
    st.caption("10% of the total prize pool")

st.success(
    "The full $1,200 collected in league dues is paid back out through the "
    "three prizes above."
)


# ============================================================
# ROSTER + LINEUP RESPONSIBILITY
# ============================================================

st.divider()

st.header("🧠 Manager Responsibilities")

with st.expander("Set a legal and competitive lineup", expanded=True):
    st.markdown(
        """
Managers are responsible for setting their own lineups before the applicable
Yahoo game deadlines.

A manager should make a good-faith effort to field a competitive lineup each
week.

Starting a player who is clearly ruled **OUT**, leaving a bye-week player in
the lineup, or otherwise failing to manage the roster is the responsibility
of that manager.

Yahoo's lock times and eligibility rules control once a player's game begins.
"""
    )

with st.expander("Bye weeks and inactive players", expanded=True):
    st.markdown(
        """
Managers are responsible for monitoring bye weeks, injuries, suspensions,
inactive designations, and roster availability.

The NFL schedule is public. The injury report is public. Sympathy is limited.
"""
    )

with st.expander("Tanking / intentionally weakened lineups", expanded=True):
    st.markdown(
        """
Managers may not intentionally manipulate competitive integrity by deliberately
fielding an obviously inferior or incomplete lineup for the purpose of helping
or hurting another franchise.

The commissioner may investigate obvious cases and may correct conduct that
threatens the integrity of standings or playoff qualification.
"""
    )


# ============================================================
# KEEPER RULES
# ============================================================

st.divider()

st.header("🔒 Keeper Rules")

st.info(
    "Keeper value is based on acquisition history and progresses one round "
    "earlier for each keeper season."
)

k1, k2, k3 = st.columns(3)

with k1:
    st.metric(
        "Maximum Keeper Seasons",
        "2",
    )
    st.caption(
        "A player may be kept in two consecutive keeper seasons."
    )

with k2:
    st.metric(
        "Undrafted FA / Waiver Cost",
        "Round 10",
    )
    st.caption(
        "An undrafted waiver/free-agent acquisition begins at Round 10."
    )

with k3:
    st.metric(
        "Annual Cost Increase",
        "1 Round Earlier",
    )
    st.caption(
        "Keeper cost advances one round each season the player is kept."
    )


st.subheader("Keeper Eligibility")

st.markdown(
    """
A player is eligible to be kept only if the franchise **still holds that player
on its roster at the end of the prior season**.

A player who is no longer on the franchise's roster at season end cannot be
claimed as that franchise's keeper the following year.
"""
)


st.subheader("Drafted Player Keeper Cost")

st.markdown(
    """
For a drafted player, the keeper cost moves **one round earlier** each keeper
season.

Example:

- Player is drafted in **Round 10**
- First keeper season: **Round 9**
- Second / final keeper season: **Round 8**
- Following season: player must return to the draft pool
"""
)


st.subheader("Waiver / Free-Agent Keeper Cost")

st.markdown(
    """
An **undrafted** player acquired through waivers or free agency begins with a
**Round 10 keeper value** for the following season.

That value then progresses normally:

- First keeper season: **Round 10**
- Second / final keeper season: **Round 9**
- Following season: player returns to the draft pool
"""
)


st.subheader("Drop and Re-Acquisition Rule")

st.markdown(
    """
If a player is **dropped** and later acquired through waivers or free agency,
the player's keeper value **resets to Round 10 for the following season**.

The reacquiring franchise must still hold the player at the end of the season
for the player to remain keeper-eligible.
"""
)


st.subheader("Keeper Tenure")

st.markdown(
    """
Keeper status is tracked as:

- **🟢 1st-Year Keeper** — the player's first season being kept
- **🟡 2nd-Year Keeper — Final Year** — the player's second and final keeper season
- **🔴 Keeper Limit Exception** — a historical case where a player was kept beyond
  the normal two-season limit

After two keeper seasons, the player must return to the draft pool.
"""
)


st.subheader("Worked Keeper Examples")

e1, e2 = st.columns(2)

with e1:
    st.markdown(
        """
### Example A — Drafted Player

**2025**  
Player drafted in **Round 10**

**2026**  
1st-Year Keeper  
Cost: **Round 9**

**2027**  
2nd-Year Keeper — Final Year  
Cost: **Round 8**

**2028**  
Player returns to the draft pool
"""
    )

with e2:
    st.markdown(
        """
### Example B — Undrafted Waiver Pickup

**2025**  
Player was undrafted and acquired on waivers

**2026**  
1st-Year Keeper  
Cost: **Round 10**

**2027**  
2nd-Year Keeper — Final Year  
Cost: **Round 9**

**2028**  
Player returns to the draft pool
"""
    )


st.caption(
    "Historical keeper records may contain documented round or tenure "
    "exceptions. Those exceptions do not replace the standard rules above."
)


# ============================================================
# DRAFT
# ============================================================

st.divider()

st.header("🎯 Draft")

st.markdown(
    """
The official draft order and draft settings are determined according to the
league's established process and the published Draft page.

Keeper selections consume the applicable keeper round for that franchise.

Yahoo's draft room controls timing, roster eligibility, and the actual draft
execution once the draft begins.
"""
)

st.warning(
    "If a keeper, draft-order, or draft-room issue is discovered before the "
    "draft starts, it should be raised immediately. Waiting until after the "
    "player is selected significantly weakens your case."
)


# ============================================================
# WAIVERS + FREE AGENCY
# ============================================================

st.divider()

st.header("📡 Waivers & Free Agency")

st.markdown(
    """
Waivers and free agency operate according to the league's current Yahoo settings.

Managers are responsible for submitting waiver claims and monitoring available
players.

Yahoo controls waiver processing order, eligibility, claim timing, and roster
locks unless the commissioner is correcting a verified platform error.
"""
)

st.caption(
    "Keeper-specific waiver/free-agent treatment is governed by the Keeper Rules "
    "section above."
)


# ============================================================
# TRADES
# ============================================================

st.divider()

st.header("🤝 Trades")

st.markdown(
    """
Trades are permitted during the league's designated trading period.

Managers may negotiate freely and are not required to accept a trade simply
because another manager believes the offer is 'fair.'

Trades should be made in good faith and for legitimate fantasy-football reasons.
Collusion, side payments outside normal league activity, or coordinated roster
manipulation are prohibited.
"""
)

st.info(
    "Keeper implications follow the player's actual acquisition/roster history. "
    "A trade does not create an extra keeper season or override the normal "
    "two-season keeper limit."
)


# ============================================================
# PLAYOFFS
# ============================================================

st.divider()

st.header("🏆 Playoffs")

st.markdown(
    """
Playoff qualification, seeding, matchup weeks, and Yahoo tiebreakers are governed
by the official league settings in Yahoo unless the league has explicitly adopted
a separate written rule.

The championship standings determine the league payouts:

- **Champion:** $720
- **Runner-Up:** $360
- **3rd Place:** $120
"""
)

st.caption(
    "Winning regular-season games remains a surprisingly effective way to improve "
    "playoff qualification."
)


# ============================================================
# YAHOO SETTINGS + STAT CORRECTIONS
# ============================================================

st.divider()

st.header("🖥️ Yahoo Settings & Stat Corrections")

st.markdown(
    """
Yahoo is the official scoring platform for the league.

Unless a league-specific rule on this page says otherwise:

- Yahoo scoring settings control fantasy-point calculations
- Yahoo player eligibility controls roster-position eligibility
- Yahoo lock times control lineup changes
- Yahoo stat corrections are accepted when officially applied
- Yahoo waiver processing controls waiver results
"""
)

st.warning(
    "A verified Yahoo display or data error may be reviewed by the commissioner. "
    "A manager simply disliking the outcome is not a platform error."
)


# ============================================================
# COMMISSIONER AUTHORITY
# ============================================================

st.divider()

st.header("👑 Commissioner Authority")

st.markdown(
    """
The commissioner is responsible for:

- Maintaining league settings
- Collecting / coordinating league dues
- Managing the draft and keeper process
- Resolving data or platform issues
- Interpreting ambiguous rules
- Protecting competitive integrity
- Correcting obvious administrative mistakes when appropriate

The commissioner should apply rules consistently and in good faith.
"""
)

st.warning(
    """
Commissioner authority does not automatically make the commissioner correct.

Historical evidence remains admissible.
"""
)


# ============================================================
# DISPUTES
# ============================================================

st.divider()

st.header("⚖️ Dispute Resolution")

st.markdown(
    """
When a rules issue arises:

1. Raise the issue promptly with the commissioner.
2. Identify the relevant written rule or Yahoo setting.
3. Provide screenshots / evidence when the dispute involves Yahoo behavior.
4. The commissioner reviews the facts and makes a ruling.
5. If a rule is genuinely unclear, the league may clarify it for future use.

A ruling should not normally be rewritten after the outcome of a matchup is known
simply because the result became inconvenient.
"""
)

with st.expander("Unofficial league dispute procedure"):
    st.markdown(
        """
1. Bring the issue to the commissioner.  
2. Argue about it in the group chat.  
3. Become increasingly certain everyone else is wrong.  
4. Cite an unrelated incident from four years ago.  
5. Eventually find the Yahoo rule.  
6. Pretend the argument never happened.
"""
    )


# ============================================================
# TRASH TALK
# ============================================================

st.divider()

st.header("🔥 Trash Talk Policy")

st.markdown(
    """
Trash talk is **strongly encouraged**.

Managers may criticize fantasy-football performance, including:

- Draft decisions
- Lineup decisions
- Trades
- Waiver claims
- Keeper choices
- Playoff collapses
- Fantasy-football knowledge
- General managerial competence

Personal attacks that go beyond normal league trash talk are not part of the game.

The objective is to make the league more entertaining, not make everyone hate
each other in real life.
"""
)


# ============================================================
# RULE CHANGES
# ============================================================

st.divider()

st.header("📝 Rule Changes")

st.markdown(
    """
Major league-rule changes should be communicated clearly before they take effect.

Whenever practical, changes affecting keeper value, payouts, roster construction,
scoring, or playoff qualification should be adopted **before the relevant season
or decision point begins** rather than retroactively.
"""
)

st.caption(
    "If this page is updated, the website version should be treated as the current "
    "written rulebook."
)


# ============================================================
# FOOTER / DISCLAIMER
# ============================================================

st.divider()

st.error(
    """
### ⚠️ Final Commissioner Disclaimer

The commissioner reserves the right to interpret these rules where genuinely
necessary.

The league reserves the right to question the commissioner's interpretation.

The commissioner reserves the right to explain why everyone else is wrong.

The league reserves the right to complain about that explanation forever.
"""
)

st.caption(
    "Malle Is The Worst Commissioner • Est. 2017 • League Constitution"
)