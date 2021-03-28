# bot.py
import os
import json
import asyncio
import logging
from urllib.parse import urlparse

import discord

from quart import Quart, request
from dotenv import load_dotenv
from blizzardapi import BlizzardApi

logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filemode="w",
)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")

BLIZZARD_CLIENT = os.getenv("BLIZZARD_CLIENT")
BLIZZARD_SECRET = os.getenv("BLIZZARD_SECRET")

app = Quart(__name__)

client = discord.Client()
blizzard_client = BlizzardApi(BLIZZARD_CLIENT, BLIZZARD_SECRET)


async def get_wow_character_image_from_url(url):
    """Returns the avartar image of the given wow character url.

    url - https://worldofwarcraft.com/en-us/character/us/malganis/astrocamp
    """
    parsed_armory_url = urlparse(url)
    path_parts = parsed_armory_url.path.strip("/").rsplit("/")

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


async def embed_application_response(data):

    embed = discord.Embed(
        title=data["name"], url=data["armory"], description=data["server"]
    )

    thumbnail_url = await get_wow_character_image_from_url(url=data["armory"])
    embed.set_thumbnail(url=thumbnail_url)

    embed.add_field(name="Class", value=data["class"], inline=True)
    embed.add_field(name="Spec", value=data["spec"], inline=True)
    embed.add_field(name="Covenant", value=data["covenant"], inline=True)

    embed.add_field(name="Logs", value=data["logs"], inline=False)

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
        logging.info(f"New channel created: {channel}")
    else:
        logging.warning(f"Channel already exists: {channel}")

    return channel


def authenticate_request(payload):
    return payload["key"] == os.getenv("TOKEN")


@app.before_serving
async def before_serving():
    loop = asyncio.get_event_loop()
    await client.login(TOKEN)
    loop.create_task(client.connect())
    logging.info("SlurpBot is online.")


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
    logging.info("/submit_application post received.")
    payload = await request.get_json()

    # validate token
    if authenticate_request(payload) == False:
        logging.warning(f"Invalid key: {payload['key']}")
        return "Bad Request", 400

    guild = discord.utils.get(client.guilds, name=GUILD)
    applicant_category = discord.utils.get(
        (await guild.fetch_channels()), name="Applicants"
    )
    channel_name = payload["name"].lower()
    channel = await create_applicant_channel(guild=guild, channel_name=channel_name)

    # embed important character details
    await channel.send(embed=await embed_application_response(data=payload))

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