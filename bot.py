#!/usr/bin/env python3
import os
import random
import re
import logging
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
MESSAGES_DIR = Path(__file__).parent / "messages"
FALLBACK_VARIANT = "0"
FALLBACK_MESSAGE = "The bot has not functioned as expected, please DM @russiancatmaid"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("welcome_bot")


def _variant_label(path: Path) -> str:
    match = re.search(r"\d+", path.stem)
    return match.group() if match else path.stem


def load_welcome_messages(directory: Path) -> list[tuple[str, str]]:
    files = sorted(directory.glob("*.txt"))
    messages = [(_variant_label(f), f.read_text(encoding="utf-8").strip()) for f in files]
    if not messages:
        logger.warning("No .txt message files found in %s; falling back to variant %s.", directory, FALLBACK_VARIANT)
        messages = [(FALLBACK_VARIANT, FALLBACK_MESSAGE)]
    return messages


WELCOME_MESSAGES = load_welcome_messages(MESSAGES_DIR)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info("Logged in as %s (id: %s)", bot.user, bot.user.id)
    try:
        synced = await bot.tree.sync()
        logger.info("Synced %d application command(s).", len(synced))
    except discord.HTTPException as e:
        logger.exception("Failed to sync application commands: %s", e)


@bot.event
async def on_member_join(member: discord.Member):
    variant, message = random.choice(WELCOME_MESSAGES)
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    try:
        await member.send(message)
        status = f"✅ Sent welcome DM (variant {variant}) to {member.mention} (`{member}`)."
    except discord.Forbidden:
        status = f"⚠️ Could not DM {member.mention} (`{member}`) — they have DMs disabled. (variant {variant})"
    except discord.HTTPException as e:
        status = f"❌ Failed to DM {member.mention} (`{member}`): {e} (variant {variant})"

    if log_channel:
        await log_channel.send(status)
    else:
        logger.warning("LOG_CHANNEL_ID not set/found; skipping channel log. Status: %s", status)


@bot.tree.command(name="ping", description="Check that the bot is online.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Pong!", ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set. Copy .env.example to .env and fill in your bot token.")
    bot.run(TOKEN)
