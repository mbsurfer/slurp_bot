# bot.py
import os
import json
import logging

from logging.config import dictConfig
from urllib.parse import urlparse

import discord
from discord.ext import commands, ipc
from discord.utils import get

from dotenv import load_dotenv
from blizzardapi import BlizzardApi

logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filemode="w",
)
log = logging.getLogger(__name__)

load_dotenv()
IPC_SECRET_KEY = os.getenv("IPC_SECRET_KEY")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD = os.getenv("DISCORD_GUILD")
DISCORD_CATEGORY = os.getenv("DISCORD_CATEGORY")

BLIZZARD_CLIENT = os.getenv("BLIZZARD_CLIENT")
BLIZZARD_SECRET = os.getenv("BLIZZARD_SECRET")


class SlurpBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ipc = ipc.Server(self, secret_key=IPC_SECRET_KEY)

    async def on_ready(self):
        print("SlurpBot is online.")
        self.guild = self.get_guild(int(DISCORD_GUILD))

        # Category where channel will get created
        self.applicant_category = self.get_channel(int(DISCORD_CATEGORY))

    async def on_ipc_ready(self):
        print("Ipc is ready.")

    async def on_ipc_error(self, endpoint, error):
        print(print(endpoint, "raised", error))


slurp_bot = SlurpBot(command_prefix="!")


@slurp_bot.ipc.route()
async def submit_application(data):
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
    payload = data.payload
    guild = slurp_bot.guild

    channel_name = payload["name"].lower()
    channel = await create_applicant_channel(guild=guild, channel_name=channel_name)

    # embed important character details
    await channel.send(embed=await (embed_application_response(data=payload)))

    # loop through the questions array
    for question_and_answer in payload["questions"]:
        await channel.send(
            content=format_application_repsonse(
                title=question_and_answer["q"],
                descrption=question_and_answer["a"],
            )
        )

    return "true"


async def get_wow_character_image_from_url(url):
    """Returns the avartar image of the given wow character url.

    url - https://worldofwarcraft.com/en-us/character/us/malganis/astrocamp
    """
    blizzard_client = BlizzardApi(BLIZZARD_CLIENT, BLIZZARD_SECRET)

    parsed_armory_url = urlparse(url)
    path_parts = parsed_armory_url.path.strip("/").rsplit("/")

    locale, obj, region, realm_slug, character_name = path_parts

    resource = blizzard_client.wow.profile.get_character_media_summary(
        region=region,
        locale=locale,
        realm_slug=realm_slug,
        character_name=character_name.lower(),
    )

    print(resource)

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
    channel = discord.utils.get(await guild.fetch_channels(), name=channel_name)
    if channel is None:
        # Create a new text channel
        channel = await guild.create_text_channel(
            channel_name, category=slurp_bot.applicant_category
        )
        log.info(f"New channel created: {channel}")
    else:
        log.warning(f"Channel already exists: {channel}")

    return channel


if __name__ == "__main__":
    slurp_bot.ipc.start()  # start the IPC Server
    slurp_bot.run(DISCORD_TOKEN)