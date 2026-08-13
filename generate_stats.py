import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USERNAME = "mmeirbek"

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"

TOKEN = os.environ["GITHUB_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def request(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def graphql(query):
    data = json.dumps({"query": query}).encode()

    req = urllib.request.Request(
        GRAPHQL,
        data=data,
        headers={
            **HEADERS,
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())

    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]


def get_user():
    return request(f"{API}/users/{USERNAME}")


def get_repositories():
    repos = []
    page = 1

    while True:
        data = request(
            f"{API}/users/{USERNAME}/repos"
            f"?per_page=100&page={page}&type=owner"
        )

        if not data:
            break

        repos.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repos


def get_contributions():
    query = """
    query {
      user(login: "mmeirbek") {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    data = graphql(query)

    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"],
            })

    return calendar["totalContributions"], days


def calculate_streak(days):
    counts = {
        day["date"]: day["count"]
        for day in days
    }

    today = datetime.now(timezone.utc).date()

    current = today

    # If today has no contribution, start from yesterday.
    if counts.get(current.isoformat(), 0) == 0:
        current -= timedelta(days=1)

    streak = 0

    while counts.get(current.isoformat(), 0) > 0:
        streak += 1
        current -= timedelta(days=1)

    return streak


def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_stats(user, repos, contributions):
    total_contributions, days = contributions

    stars = sum(repo["stargazers_count"] for repo in repos)
    repositories = len(repos)
    followers = user["followers"]

    svg = f"""<svg width="900" height="230"
xmlns="http://www.w3.org/2000/svg">

<style>
  .bg {{
    fill: #0d1117;
  }}

  .title {{
    fill: #8b949e;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
  }}

  .value {{
    fill: #f0f6fc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 30px;
    font-weight: 700;
  }}

  .card {{
    fill: #161b22;
    stroke: #30363d;
    stroke-width: 1;
  }}
</style>

<rect width="900" height="230" rx="16" class="bg"/>

<rect x="20" y="20" width="410" height="85" rx="12" class="card"/>
<rect x="450" y="20" width="430" height="85" rx="12" class="card"/>

<rect x="20" y="125" width="410" height="85" rx="12" class="card"/>
<rect x="450" y="125" width="430" height="85" rx="12" class="card"/>

<text x="45" y="50" class="title">CONTRIBUTIONS</text>
<text x="45" y="88" class="value">{esc(total_contributions)}</text>

<text x="475" y="50" class="title">⭐ STARS</text>
<text x="475" y="88" class="value">{esc(stars)}</text>

<text x="45" y="155" class="title">📦 REPOSITORIES</text>
<text x="45" y="193" class="value">{esc(repositories)}</text>

<text x="475" y="155" class="title">👥 FOLLOWERS</text>
<text x="475" y="193" class="value">{esc(followers)}</text>

</svg>
"""

    Path("assets/github-stats.svg").write_text(svg, encoding="utf-8")


def write_streak(days):
    streak = calculate_streak(days)

    svg = f"""<svg width="900" height="145"
xmlns="http://www.w3.org/2000/svg">

<style>
  .bg {{
    fill: #0d1117;
  }}

  .title {{
    fill: #8b949e;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
  }}

  .value {{
    fill: #f0f6fc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 32px;
    font-weight: 700;
  }}

  .accent {{
    fill: #f0883e;
  }}
</style>

<rect width="900" height="145" rx="16" class="bg"/>

<text x="35" y="38" class="title">🔥 CONTRIBUTION STREAK</text>

<text x="35" y="88" class="value">
  {esc(streak)} days
</text>

<rect x="35" y="108" width="830" height="3" rx="2" class="accent"/>

</svg>
"""

    Path("assets/streak.svg").write_text(svg, encoding="utf-8")


def write_activity(days):
    # Last 30 days
    recent = days[-30:]

    max_count = max(
        [day["count"] for day in recent] or [1]
    )

    width = 900
    height = 180

    bar_width = 22
    gap = 7

    bars = []

    for i, day in enumerate(recent):
        count = day["count"]

        bar_height = max(
            4,
            int((count / max_count) * 90)
        )

        x = 30 + i * (bar_width + gap)
        y = 125 - bar_height

        opacity = 0.25 + (
            0.75 * (count / max_count)
        ) if count else 0.12

        bars.append(
            f'''
            <rect
              x="{x}"
              y="{y}"
              width="{bar_width}"
              height="{bar_height}"
              rx="5"
              fill="#58a6ff"
              opacity="{opacity:.2f}"
            />
            '''
        )

    svg = f"""<svg width="{width}" height="{height}"
xmlns="http://www.w3.org/2000/svg">

<style>
  .bg {{
    fill: #0d1117;
  }}

  .title {{
    fill: #8b949e;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
  }}
</style>

<rect width="{width}" height="{height}" rx="16" class="bg"/>

<text x="30" y="32" class="title">📈 ACTIVITY · LAST 30 DAYS</text>

{''.join(bars)}

</svg>
"""

    Path("assets/activity.svg").write_text(svg, encoding="utf-8")


def main():
    Path("assets").mkdir(exist_ok=True)

    user = get_user()
    repos = get_repositories()
    contributions = get_contributions()

    write_stats(user, repos, contributions)
    write_streak(contributions[1])
    write_activity(contributions[1])

    print("GitHub stats generated successfully.")


if __name__ == "__main__":
    main()
