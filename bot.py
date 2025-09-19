import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import re

# set up bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_course_info(code):
    subject = ''.join([c for c in code if not c.isdigit()]).lower()

    # map of subject → slug (for URL)
    slug_map = {
        "coop": "co-op",
        "co-op": "co-op",
        "math": "math",
        "cis": "cis",
        "biol": "biol",
        "chem": "chem",
        "econ": "econ",
        "psyc": "psyc",
        "stat": "stat",
        "geog": "geog",
        "frhd": "frhd",
        "oac": "oac",
        # might not need slugmap at all
    }

    subject_slug = slug_map.get(subject, subject)

    url = f"https://calendar.uoguelph.ca/undergraduate-calendar/course-descriptions/{subject_slug}/"
    print("[debug] url ->", url)

    res = requests.get(url)
    if res.status_code != 200:
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    code_fmt = code.upper().replace(" ", "")
    if "*" not in code_fmt:
        # find first digit, insert * before it
        for i, ch in enumerate(code_fmt):
            if ch.isdigit():
                code_fmt = code_fmt[:i] + "*" + code_fmt[i:]
                break

    print("[debug] searching for id ->", code_fmt)

    blocks = soup.find_all("div", class_="courseblock")
    print(f"[debug] found {len(blocks)} course blocks on page")

    for b in blocks:
        code_tag = b.find("span", class_="text detail-code margin--small text--semibold text--big")
        title_tag = b.find("span", class_="text detail-title margin--small text--semibold text--big")
        hours_tag = b.find("span", class_="text detail-hours_html margin--small text--semibold text--big")
        offered_tag = b.find("span", class_="text detail-typically_offered margin--small text--semibold text--big")
        desc_tag = b.find("div", class_="courseblockextra noindent")

        if not code_tag or not title_tag:
            continue

        course_code = code_tag.get_text(strip=True)
        if course_code != code_fmt:
            continue

        course_title = title_tag.get_text(strip=True)
        hours_text = hours_tag.get_text(strip=True) if hours_tag else ""

        # extract lecture/lab breakdown
        lecture_lab = "Not listed"
        if hours_tag:
            parent = hours_tag.find_parent("div", class_="cols noindent")
            if parent:
                lecture_lab = parent.get_text(" ", strip=True)
                lecture_lab = lecture_lab.replace(course_code, "")
                lecture_lab = lecture_lab.replace(course_title, "")
                lecture_lab = lecture_lab.replace(hours_text, "")
                lecture_lab = lecture_lab.replace(offered_tag.get_text(strip=True) if offered_tag else "", "")
                lecture_lab = lecture_lab.strip()

        offered = offered_tag.get_text(strip=True) if offered_tag else "Not listed"
        desc = desc_tag.get_text(strip=True) if desc_tag else "No description found"

        restrictions, prereqs = "None", "None"
        extra_divs = b.find_all("div", class_="noindent")
        for div in extra_divs:
            strong = div.find("strong")
            if strong:
                label = strong.get_text(strip=True).lower()
                text = div.get_text(strip=True)
                if "restriction" in label:
                    restrictions = text.replace("Restrictions:", "").strip()
                elif "prerequisite" in label:
                    prereqs = text.replace("Prerequisite(s):", "").replace("Prerequisites:", "").strip()

        return {
            "title": f"{course_code} {course_title} {hours_text}",
            "desc": desc,
            "offered": offered,
            "restrictions": restrictions,
            "prereqs": prereqs,
            "lecture_lab": lecture_lab if lecture_lab else "Not listed"
        }

    return None

# command
@bot.command()
async def course(ctx, code: str):
    info = get_course_info(code)
    if not info:
        await ctx.send(f"could not find {code.upper()}")
        return

    embed = discord.Embed(
        title=info["title"],
        description=info["desc"],
        color=discord.Color.blue()
    )
    embed.add_field(name="Typically Offered", value=info["offered"], inline=False)
    embed.add_field(name="Lecture/Lab Hours", value=info["lecture_lab"], inline=False)
    embed.add_field(name="Restrictions", value=info["restrictions"], inline=False)
    embed.add_field(name="Prerequisites", value=info["prereqs"], inline=False)

    await ctx.send(embed=embed)

# run bot
import os
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
