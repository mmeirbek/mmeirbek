import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USERNAME = "mmeirbek"

API_URL = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

TOKEN = os.environ["GITHUB_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ─────────────────────────────────────────────
# GitHub API
# ─────────────────────────────────────────────

def api_get(url):
    request = urllib.request.Request(
        url,
        headers=HEADERS,
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def graphql(query):
    payload = json.dumps({
        "query": query
    }).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            **HEADERS,
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())

    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]


# ─────────────────────────────────────────────
# User information
# ─────────────────────────────────────────────

def get_user():
    return api_get(
        f"{API_URL}/users/{USERNAME}"
    )


def get_repositories():
    repositories = []
    page = 1

    while True:
        data = api_get(
            f"{API_URL}/users/{USERNAME}/repos"
            f"?per_page=100"
            f"&page={page}"
            f"&type=owner"
        )

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repositories


# ─────────────────────────────────────────────
# Contributions
# ─────────────────────────────────────────────

def get_contributions():
    query = f"""
    query {{
        user(login: "{USERNAME}") {{
            contributionsCollection {{
                contributionCalendar {{
                    totalContributions

                    weeks {{
                        contributionDays {{
                            date
                            contributionCount
                        }}
                    }}
                }}
            }}
        }}
    }}
    """

    data = graphql(query)

    calendar = (
        data["user"]
        ["contributionsCollection"]
        ["contributionCalendar"]
    )

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"],
            })

    return (
        calendar["totalContributions"],
        days,
    )


# ─────────────────────────────────────────────
# Contribution streak
# ─────────────────────────────────────────────

def calculate_streak(days):
    counts = {
        day["date"]: day["count"]
        for day in days
    }

    today = datetime.now(
        timezone.utc
    ).date()

    current = today

    # If there was no contribution today,
    # start checking from yesterday.
    if counts.get(
        current.isoformat(),
        0
    ) == 0:
        current -= timedelta(days=1)

    streak = 0

    while counts.get(
        current.isoformat(),
        0
    ) > 0:

        streak += 1
        current -= timedelta(days=1)

    return streak


# ─────────────────────────────────────────────
# SVG helpers
# ─────────────────────────────────────────────

def escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ─────────────────────────────────────────────
# Generate compact SVG
# ─────────────────────────────────────────────

def generate_svg(
    total_contributions,
    stars,
    repositories,
    followers,
    streak,
    days,
):

    WIDTH = 760
    HEIGHT = 175

    # Last 30 days
    recent_days = days[-30:]

    max_activity = max(
        [day["count"] for day in recent_days]
        or [1]
    )

    # Activity bars
    bars = []

    bar_width = 13
    gap = 8

    start_x = 455
    baseline_y = 143
    max_height = 38

    for index, day in enumerate(recent_days):

        count = day["count"]

        if max_activity > 0:
            height = int(
                (count / max_activity)
                * max_height
            )
        else:
            height = 0

        # Minimum visual height for active days
        if count > 0:
            height = max(
                height,
                5
            )

        x = (
            start_x
            + index * (bar_width + gap)
        )

        y = baseline_y - height

        opacity = (
            0.18
            if count == 0
            else 0.35
            + (
                0.65
                * count
                / max_activity
            )
        )

        bars.append(
            f"""
            <rect
                x="{x}"
                y="{y}"
                width="{bar_width}"
                height="{max(height, 2)}"
                rx="4"
                fill="#58A6FF"
                opacity="{opacity:.2f}"
            />
            """
        )

    activity_bars = "".join(bars)

    # ─────────────────────────────────────────
    # SVG
    # ─────────────────────────────────────────

    svg = f"""<svg
    width="{WIDTH}"
    height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
>

<style>

    .background {{
        fill: #0D1117;
    }}

    .border {{
        fill: none;
        stroke: #30363D;
        stroke-width: 1;
    }}

    .label {{
        fill: #8B949E;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.7px;
    }}

    .value {{
        fill: #F0F6FC;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

        font-size: 18px;
        font-weight: 700;
    }}

    .small {{
        fill: #8B949E;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

        font-size: 11px;
    }}

    .streak {{
        fill: #F0883E;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

        font-size: 12px;
        font-weight: 600;
    }}

</style>


<!-- Background -->

<rect
    x="0.5"
    y="0.5"
    width="{WIDTH - 1}"
    height="{HEIGHT - 1}"
    rx="14"
    class="background"
/>

<rect
    x="0.5"
    y="0.5"
    width="{WIDTH - 1}"
    height="{HEIGHT - 1}"
    rx="14"
    class="border"
/>


<!-- Header -->

<text
    x="24"
    y="27"
    class="label"
>
    📊 GITHUB STATS
</text>


<!-- Stats -->

<text
    x="24"
    y="52"
    class="value"
>
    {escape(total_contributions)}
</text>

<text
    x="24"
    y="69"
    class="label"
>
    CONTRIBUTIONS
</text>


<text
    x="160"
    y="52"
    class="value"
>
    {escape(stars)}
</text>

<text
    x="160"
    y="69"
    class="label"
>
    ⭐ STARS
</text>


<text
    x="285"
    y="52"
    class="value"
>
    {escape(repositories)}
</text>

<text
    x="285"
    y="69"
    class="label"
>
    📦 REPOSITORIES
</text>


<text
    x="405"
    y="52"
    class="value"
>
    {escape(followers)}
</text>

<text
    x="405"
    y="69"
    class="label"
>
    👥 FOLLOWERS
</text>


<!-- Divider -->

<line
    x1="24"
    y1="82"
    x2="736"
    y2="82"
    stroke="#21262D"
/>


<!-- Streak -->

<text
    x="24"
    y="106"
    class="streak"
>
    🔥 {escape(streak)} day streak
</text>


<!-- Activity label -->

<text
    x="455"
    y="106"
    class="label"
>
    📈 ACTIVITY
</text>


<!-- Activity -->

{activity_bars}


<!-- Activity baseline -->

<line
    x1="455"
    y1="144"
    x2="736"
    y2="144"
    stroke="#30363D"
/>


<!-- Footer -->

<text
    x="24"
    y="143"
    class="small"
>
    github.com/{escape(USERNAME)}
</text>


</svg>
"""

    return svg


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():

    print(
        f"Fetching GitHub data for @{USERNAME}..."
    )

    user = get_user()

    repositories = get_repositories()

    total_contributions, days = (
        get_contributions()
    )

    # Total stars across owned repositories
    stars = sum(
        repo["stargazers_count"]
        for repo in repositories
    )

    repository_count = len(
        repositories
    )

    followers = user["followers"]

    streak = calculate_streak(
        days
    )

    svg = generate_svg(
        total_contributions=
            total_contributions,

        stars=stars,

        repositories=
            repository_count,

        followers=
            followers,

        streak=streak,

        days=days,
    )

    output = Path(
        "assets/github-stats.svg"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        svg,
        encoding="utf-8"
    )

    print(
        "✓ GitHub stats generated."
    )

    print(
        f"  Contributions: {total_contributions}"
    )

    print(
        f"  Stars:         {stars}"
    )

    print(
        f"  Repositories:  {repository_count}"
    )

    print(
        f"  Followers:     {followers}"
    )

    print(
        f"  Streak:        {streak} days"
    )

    print(
        f"✓ Saved to {output}"
    )


if __name__ == "__main__":
    main()
