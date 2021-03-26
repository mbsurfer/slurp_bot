# bot.py
import os
import json
import asyncio
from urllib.parse import urlparse

import discord

from quart import Quart, request
from dotenv import load_dotenv
from blizzardapi import BlizzardApi

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")

BLIZZARD_CLIENT = os.getenv("BLIZZARD_CLIENT")
BLIZZARD_SECRET = os.getenv("BLIZZARD_SECRET")


app = Quart(__name__)

client = discord.Client()
blizzard_client = BlizzardApi(BLIZZARD_CLIENT, BLIZZARD_SECRET)


def get_wow_character_image_from_url(url):
    """Returns the avartar image of the given wow character url.

    url - https://worldofwarcraft.com/en-us/character/us/malganis/astrocamp
    """
    parsed_armory_url = urlparse(url)
    print(f"parsed_armory_url: {parsed_armory_url}")
    path_parts = parsed_armory_url.path.strip("/").rsplit("/")
    print(f"path_parts: {path_parts}")

    locale, obj, region, realm_slug, character_name = path_parts

    resource = blizzard_client.wow.profile.get_character_media_summary(
        region=region,
        locale=locale,
        realm_slug=realm_slug,
        character_name=character_name,
    )
    return resource["assets"][0]["value"]


def format_application_repsonse(title, descrption):
    return f"**__{title}__**\n{descrption}"


def embed_application_response(data):

    embed = discord.Embed(
        title=data["name"], url=data["armory"], description=data["server"]
    )

    thumbnail_url = get_wow_character_image_from_url(url=data["armory"])
    embed.set_thumbnail(url=thumbnail_url)

    embed.add_field(name="Class", value=data["class"], inline=True)
    embed.add_field(name="Spec", value=data["spec"], inline=True)
    embed.add_field(name="Covenant", value=data["covenant"], inline=True)

    return embed


async def create_applicant_channel(guild, channel_name):
    """Returns a new channel for the applicant."""
    # check if applicant channel already exists
    channel = discord.utils.get((await guild.fetch_channels()), name=channel_name)
    if channel is None:
        # Create a new text channel
        channel = await guild.create_text_channel(
            channel_name, category=applicant_category
        )
        print(f"New channel created: {channel}")
    else:
        print(f"Channel already exists: {channel}")

    return channel


def authenticate_request(payload):
    return payload["key"] == os.getenv("TOKEN")


@app.before_serving
async def before_serving():
    loop = asyncio.get_event_loop()
    await client.login(TOKEN)
    loop.create_task(client.connect())


@app.route("/submit_application", methods=["POST"])
async def submit_application():
    """Webhook for posting application responses to discord

    JSON payload:
    name -- the character name
    server
    class
    spec
    covenant
    armory -- the link to wow armory ie. https://worldofwarcraft.com/en-us/character/us/{server}/{name}
    questions -- an array or questions and answers [{"q": "", "a": ""}, ...]
    """
    print("submit_application post received")
    payload = await request.get_json()

    # validate token
    if authenticate_request(payload) == False:
        print(f"Invalid key: {payload['key']}")
        return "Bad Request", 400

    print("connecting to discord")
    guild = discord.utils.get(client.guilds, name=GUILD)
    applicant_category = discord.utils.get(
        (await guild.fetch_channels()), name="Applicants"
    )
    channel_name = payload["name"].lower()
    channel = await create_applicant_channel(guild=guild, channel_name=channel_name)

    # embed important character details
    await channel.send(embed=embed_application_response(data=payload))

    # loop through the questions array
    for question_and_answer in payload["questions"]:
        await channel.send(
            content=format_application_repsonse(
                title=question_and_answer["q"],
                descrption=question_and_answer["a"],
            )
        )

    return "OK", 200


app.run()