import json
import re
from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="The Commissioner’s Mistake",
    page_icon="📰",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parents[1]
NEWS_DIR = BASE_DIR / "data" / "news"


# ============================================================
# ARTICLE DISCOVERY + LOADING
# ============================================================

def discover_articles():
    """
    Discover generated weekly articles without hard-coding a season or week.
    Expected path:
        data/news/<season>/week_XX_article.json
    """
    articles = []

    if not NEWS_DIR.exists():
        return articles

    for path in NEWS_DIR.glob("*/week_*_article.json"):
        try:
            season = int(path.parent.name)
            match = re.fullmatch(r"week_(\d+)_article\.json", path.name)
            if not match:
                continue
            week = int(match.group(1))
        except (TypeError, ValueError):
            continue

        articles.append(
            {
                "season": season,
                "week": week,
                "path": path,
            }
        )

    return sorted(
        articles,
        key=lambda item: (item["season"], item["week"]),
        reverse=True,
    )


@st.cache_data(show_spinner=False)
def load_article(path_string):
    path = Path(path_string)
    with path.open("r", encoding="utf-8") as handle:
        article = json.load(handle)

    required = {
        "schema_version",
        "season",
        "week",
        "publication_title",
        "issue_headline",
        "issue_deck",
        "lead_story",
        "matchup_recaps",
        "managerial_desk",
        "luck_report",
        "players_of_the_week",
        "record_book",
        "next_week",
        "closing_shot",
    }

    missing = sorted(required - set(article))
    if missing:
        raise ValueError(
            "Article is missing required field(s): "
            + ", ".join(missing)
        )

    return article


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def render_story_body(body):
    """
    Generated article bodies are already validated prose.
    Render as Markdown so normal punctuation/emphasis remains readable.
    """
    text = safe_text(body)
    if text:
        st.markdown(text)


# ============================================================
# NEWSPAPER STYLING
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1380px;
        padding-top: 1.15rem;
        padding-bottom: 4rem;
    }

    .paper-rule {
        border-top: 1px solid rgba(120, 113, 108, .55);
        margin: .55rem 0;
    }

    .paper-rule-heavy {
        border-top: 4px solid currentColor;
        margin: .55rem 0 .35rem 0;
    }

    .paper-rule-double {
        border-top: 1px solid currentColor;
        border-bottom: 3px solid currentColor;
        height: 5px;
        margin: .5rem 0 1.1rem 0;
    }

    .masthead {
        text-align: center;
        padding-top: .25rem;
    }

    .masthead-kicker {
        font-family: Arial, Helvetica, sans-serif;
        text-transform: uppercase;
        letter-spacing: .16em;
        font-size: .72rem;
        font-weight: 700;
        opacity: .72;
        margin-bottom: .25rem;
    }

    .masthead-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(2.6rem, 7vw, 5.8rem);
        line-height: .95;
        font-weight: 900;
        letter-spacing: -.055em;
        margin: 0;
    }

    .masthead-meta {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        font-family: Arial, Helvetica, sans-serif;
        text-transform: uppercase;
        letter-spacing: .08em;
        font-size: .72rem;
        font-weight: 700;
        margin: .45rem 0;
    }

    .front-headline {
        font-family: Georgia, "Times New Roman", serif;
        text-align: center;
        font-size: clamp(2.05rem, 4.4vw, 4rem);
        line-height: .98;
        font-weight: 900;
        letter-spacing: -.035em;
        max-width: 1180px;
        margin: 1.05rem auto .65rem auto;
    }

    .front-deck {
        font-family: Georgia, "Times New Roman", serif;
        text-align: center;
        font-size: clamp(1.05rem, 2vw, 1.38rem);
        line-height: 1.45;
        max-width: 980px;
        margin: 0 auto 1.2rem auto;
        opacity: .82;
    }

    .section-label {
        font-family: Arial, Helvetica, sans-serif;
        text-transform: uppercase;
        letter-spacing: .13em;
        font-size: .74rem;
        font-weight: 800;
        border-top: 4px solid currentColor;
        border-bottom: 1px solid currentColor;
        padding: .42rem 0 .36rem 0;
        margin: 2rem 0 .8rem 0;
    }

    .lead-headline {
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(1.8rem, 3vw, 2.8rem);
        line-height: 1.05;
        font-weight: 900;
        letter-spacing: -.025em;
        margin-bottom: .7rem;
    }

    .lead-story-body div[data-testid="stMarkdownContainer"] p {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.1rem;
        line-height: 1.72;
    }

    .story-headline {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.45rem;
        line-height: 1.08;
        font-weight: 800;
        margin: 0 0 .55rem 0;
    }

    .preview-headline {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.25rem;
        line-height: 1.1;
        font-weight: 800;
        margin: 0 0 .45rem 0;
    }

    .closing-shot {
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(1.35rem, 2.4vw, 2rem);
        font-style: italic;
        line-height: 1.35;
        text-align: center;
        max-width: 1000px;
        margin: 1.1rem auto;
        padding: 1.1rem 1.4rem;
        border-top: 1px solid currentColor;
        border-bottom: 4px solid currentColor;
    }

    .issue-note {
        font-family: Arial, Helvetica, sans-serif;
        text-align: center;
        font-size: .75rem;
        text-transform: uppercase;
        letter-spacing: .08em;
        opacity: .65;
        margin-top: 1.3rem;
    }

    div[data-testid="stMarkdownContainer"] p {
        line-height: 1.62;
    }

    /* ========================================================
       RESPONSIVE / MOBILE NEWSPAPER LAYOUT
       Desktop keeps the two-column newspaper treatment. Phones
       collapse every Streamlit column pair into a single reading
       column and scale the typography to the viewport.
       ======================================================== */
    @media (max-width: 768px) {
        .block-container {
            max-width: 100%;
            padding-top: .55rem;
            padding-left: .8rem;
            padding-right: .8rem;
            padding-bottom: 2.5rem;
        }

        /* Stack matchup, department, and preview st.columns. */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0 !important;
        }

        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 0 !important;
        }

        .masthead {
            padding-top: 0;
        }

        .masthead-kicker {
            font-size: .62rem;
            letter-spacing: .12em;
        }

        .masthead-title {
            font-size: clamp(2.55rem, 13vw, 4.35rem);
            line-height: .88;
            letter-spacing: -.055em;
            padding: 0 .1rem;
        }

        .masthead-meta {
            display: grid;
            grid-template-columns: 1fr;
            gap: .18rem;
            text-align: center;
            font-size: .63rem;
            line-height: 1.35;
            margin: .5rem 0;
        }

        .paper-rule-double {
            margin-bottom: .75rem;
        }

        .front-headline {
            font-size: clamp(2rem, 10vw, 3rem);
            line-height: .98;
            letter-spacing: -.025em;
            margin: .85rem auto .55rem auto;
            overflow-wrap: anywhere;
        }

        .front-deck {
            font-size: 1rem;
            line-height: 1.45;
            margin-bottom: .85rem;
            padding: 0 .15rem;
        }

        .section-label {
            font-size: .68rem;
            letter-spacing: .1em;
            margin: 1.35rem 0 .7rem 0;
            padding: .36rem 0 .3rem 0;
        }

        .lead-headline {
            font-size: 1.8rem;
            line-height: 1.03;
            margin-bottom: .55rem;
        }

        .lead-story-body div[data-testid="stMarkdownContainer"] p {
            font-size: 1.06rem;
            line-height: 1.62;
        }

        .story-headline,
        .preview-headline {
            font-size: 1.38rem;
            line-height: 1.08;
            margin-top: .15rem;
            margin-bottom: .35rem;
            overflow-wrap: anywhere;
        }

        div[data-testid="stMarkdownContainer"] p {
            font-size: 1rem;
            line-height: 1.58;
            overflow-wrap: anywhere;
        }

        /* Give each formerly-columnized story a clear mobile divider. */
        div[data-testid="stColumn"] + div[data-testid="stColumn"] {
            border-top: 1px solid rgba(120, 113, 108, .55);
            padding-top: .8rem;
            margin-top: .55rem;
        }

        .closing-shot {
            font-size: 1.32rem;
            line-height: 1.32;
            margin: .8rem auto;
            padding: .9rem .45rem;
        }

        .issue-note {
            font-size: .62rem;
            line-height: 1.5;
            letter-spacing: .065em;
            margin-top: 1rem;
        }
    }

    @media (max-width: 480px) {
        .block-container {
            padding-left: .65rem;
            padding-right: .65rem;
        }

        .masthead-title {
            font-size: clamp(2.35rem, 14vw, 3.55rem);
        }

        .front-headline {
            font-size: clamp(1.85rem, 10.5vw, 2.55rem);
        }

        .front-deck {
            font-size: .96rem;
        }

        .lead-headline {
            font-size: 1.65rem;
        }

        .lead-story-body div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] p {
            font-size: .98rem;
        }

        .story-headline,
        .preview-headline {
            font-size: 1.28rem;
        }

        .closing-shot {
            font-size: 1.2rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ARCHIVE SELECTION
# ============================================================

articles = discover_articles()

if not articles:
    st.title("📰 The Commissioner’s Mistake")
    st.info(
        "No generated weekly issues are available yet. "
        "Generate an article in data/news/<season>/ and it will "
        "appear here automatically."
    )
    st.stop()

available_seasons = sorted(
    {item["season"] for item in articles},
    reverse=True,
)

latest = articles[0]

with st.sidebar:
    st.header("🗞️ Newspaper Archive")

    default_season_index = available_seasons.index(latest["season"])
    selected_season = st.selectbox(
        "Season",
        available_seasons,
        index=default_season_index,
        key="newspaper_season",
    )

    season_articles = [
        item for item in articles
        if item["season"] == selected_season
    ]
    available_weeks = sorted(
        {item["week"] for item in season_articles},
        reverse=True,
    )

    selected_week = st.selectbox(
        "Issue",
        available_weeks,
        format_func=lambda week: f"Week {week}",
        index=0,
        key="newspaper_week",
    )

    st.caption(
        "New issues appear automatically when a validated "
        "`week_XX_article.json` file is added."
    )

selected = next(
    item for item in season_articles
    if item["week"] == selected_week
)

try:
    article = load_article(str(selected["path"]))
except Exception as exc:
    st.error(f"Could not load this newspaper issue: {exc}")
    st.stop()


# ============================================================
# FRONT PAGE
# ============================================================

publication_title = safe_text(
    article.get("publication_title")
) or "The Commissioner’s Mistake"

season = int(article.get("season", selected_season))
week = int(article.get("week", selected_week))

st.markdown(
    f"""
    <div class="masthead">
        <div class="masthead-kicker">
            Independent League Journalism Since 2017
        </div>
        <div class="masthead-title">
            {publication_title}
        </div>
    </div>
    <div class="paper-rule-heavy"></div>
    <div class="masthead-meta">
        <span>Malle Is The Worst Commissioner</span>
        <span>Season {season} &nbsp;•&nbsp; Week {week}</span>
        <span>Price: One Bad Lineup Decision</span>
    </div>
    <div class="paper-rule-double"></div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="front-headline">{safe_text(article["issue_headline"])}</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="front-deck">{safe_text(article["issue_deck"])}</div>',
    unsafe_allow_html=True,
)


# ============================================================
# LEAD STORY
# ============================================================

lead = article.get("lead_story") or {}

st.markdown(
    '<div class="section-label">Lead Story</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="lead-headline">{safe_text(lead.get("headline"))}</div>',
    unsafe_allow_html=True,
)
lead_body = lead.get("body")
lead_paragraphs = lead_body if isinstance(lead_body, list) else [lead_body]
for paragraph in lead_paragraphs:
    text = safe_text(paragraph)
    if text:
        st.markdown(
            f'<div class="lead-story-body"><p>{text}</p></div>',
            unsafe_allow_html=True,
        )


# ============================================================
# MATCHUP RECAPS
# ============================================================

recaps = article.get("matchup_recaps") or []

st.markdown(
    '<div class="section-label">Around the League — Week Recaps</div>',
    unsafe_allow_html=True,
)

for start in range(0, len(recaps), 2):
    pair = recaps[start:start + 2]
    columns = st.columns(len(pair), gap="large")

    for column, recap in zip(columns, pair):
        with column:
            st.markdown(
                f'<div class="story-headline">'
                f'{safe_text(recap.get("headline"))}'
                f'</div>',
                unsafe_allow_html=True,
            )

            winner = safe_text(recap.get("winner"))
            loser = safe_text(recap.get("loser"))
            if winner and loser:
                st.caption(f"{winner} over {loser}")

            render_story_body(recap.get("body"))

    if start + 2 < len(recaps):
        st.markdown(
            '<div class="paper-rule"></div>',
            unsafe_allow_html=True,
        )


# ============================================================
# DEPARTMENTS
# ============================================================

departments = [
    ("🧠 Managerial Desk", article.get("managerial_desk") or {}),
    ("🍀 Luck Report", article.get("luck_report") or {}),
    ("⭐ Players of the Week", article.get("players_of_the_week") or {}),
    ("📚 Record Book", article.get("record_book") or {}),
]

st.markdown(
    '<div class="section-label">The Departments</div>',
    unsafe_allow_html=True,
)

for start in range(0, len(departments), 2):
    pair = departments[start:start + 2]
    columns = st.columns(len(pair), gap="large")

    for column, (label, section) in zip(columns, pair):
        with column:
            st.caption(label.upper())
            st.markdown(
                f'<div class="story-headline">'
                f'{safe_text(section.get("headline"))}'
                f'</div>',
                unsafe_allow_html=True,
            )
            render_story_body(section.get("body"))

    if start + 2 < len(departments):
        st.markdown(
            '<div class="paper-rule"></div>',
            unsafe_allow_html=True,
        )


# ============================================================
# NEXT WEEK
# ============================================================

next_week = article.get("next_week") or {}
previews = next_week.get("previews") or []

st.markdown(
    '<div class="section-label">On the Docket — Next Week</div>',
    unsafe_allow_html=True,
)

if safe_text(next_week.get("headline")):
    st.markdown(
        f'<div class="lead-headline">'
        f'{safe_text(next_week.get("headline"))}'
        f'</div>',
        unsafe_allow_html=True,
    )

if previews:
    for start in range(0, len(previews), 2):
        pair = previews[start:start + 2]
        columns = st.columns(len(pair), gap="large")

        for column, preview in zip(columns, pair):
            with column:
                st.markdown(
                    f'<div class="preview-headline">'
                    f'{safe_text(preview.get("headline"))}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                team_1 = safe_text(preview.get("team_1"))
                team_2 = safe_text(preview.get("team_2"))
                if team_1 and team_2:
                    st.caption(f"{team_1} vs. {team_2}")

                render_story_body(preview.get("body"))

        if start + 2 < len(previews):
            st.markdown(
                '<div class="paper-rule"></div>',
                unsafe_allow_html=True,
            )
else:
    st.caption("No upcoming matchup previews are available for this issue.")


# ============================================================
# CLOSING SHOT + FOOTER
# ============================================================

closing_shot = safe_text(article.get("closing_shot"))

if closing_shot:
    st.markdown(
        '<div class="section-label">Closing Shot</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="closing-shot">“{closing_shot}”</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    f"""
    <div class="issue-note">
        {publication_title} &nbsp;•&nbsp;
        Season {season}, Week {week} &nbsp;•&nbsp;
        Generated from validated league data
    </div>
    """,
    unsafe_allow_html=True,
)
