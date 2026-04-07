"""
=============================================================
  TELEGRAM CROCODILE SAFETY ALERT SYSTEM
  For SM Lok Yuk Likas PBL Project
  Author: Student Project
=============================================================

HOW TO RUN:
1. Install libraries:  pip install python-telegram-bot==20.7 schedule requests
2. Fill in your BOT_TOKEN and GROUP_CHAT_ID below
3. Run:  python bot.py
"""


import asyncio
import logging
import math
import schedule
import time
import threading
from datetime import datetime

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────────
#   ⚙️  CONFIGURATION  — FILL THESE IN!
# ─────────────────────────────────────────────

import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

# Set up logging so we can see what the bot is doing
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#   🐊  DANGER ZONE DATA
#   Add or edit locations here!
# ─────────────────────────────────────────────

DANGER_ZONES = [
    {
        "name": "Sungai Tuaran",
        "lat": 6.1833,
        "lon": 116.3500,
        "radius_m": 1500,       # metres
        "risk": "HIGH",
        "notes": "Tembaga crocodile sightings reported frequently.",
    },
    {
        "name": "Teluk Likas (Pantai Likas)",
        "lat": 5.9928,
        "lon": 116.0742,
        "radius_m": 1000,
        "risk": "HIGH",
        "notes": "Mangrove area — active crocodile habitat.",
    },
    {
        "name": "Sungai Kalumpang",
        "lat": 5.8500,
        "lon": 116.1000,
        "radius_m": 2000,
        "risk": "MEDIUM",
        "notes": "Occasional sightings during low tide.",
    },
    {
        "name": "Kuala Penyu Estuary",
        "lat": 5.6167,
        "lon": 115.6000,
        "radius_m": 3000,
        "risk": "HIGH",
        "notes": "Remote estuary — high crocodile population.",
    },
    {
        "name": "Sungai Kinabatangan",
        "lat": 5.4167,
        "lon": 118.0833,
        "radius_m": 5000,
        "risk": "HIGH",
        "notes": "World-famous crocodile habitat. Do NOT swim here.",
    },
    {
        "name": "Pulau Tiga Waters",
        "lat": 5.6700,
        "lon": 115.6700,
        "radius_m": 2500,
        "risk": "MEDIUM",
        "notes": "Surrounding waters reported with croc activity.",
    },
]

# ─────────────────────────────────────────────
#   📐  HAVERSINE FORMULA
#   Calculates real-world distance between two
#   GPS coordinates (in metres).
# ─────────────────────────────────────────────

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance in metres between two GPS points.
    Uses the Haversine formula (great-circle distance).
    """
    R = 6_371_000  # Earth's radius in metres

    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    # Haversine formula
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # distance in metres


# ─────────────────────────────────────────────
#   🎨  MESSAGE FORMATTERS
# ─────────────────────────────────────────────

def risk_emoji(risk: str) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(risk, "⚪")


def format_scheduled_alert() -> str:
    now = datetime.now().strftime("%d %b %Y  |  %H:%M")
    zones_text = ""
    for z in DANGER_ZONES:
        zones_text += (
            f"\n{risk_emoji(z['risk'])} *{z['name']}*"
            f"\n   ├ Risk   : `{z['risk']}`"
            f"\n   ├ Radius : `{z['radius_m']} m`"
            f"\n   └ Note   : _{z['notes']}_\n"
        )

    return (
        f"🐊 *CROCODILE SAFETY ALERT*\n"
        f"{'─' * 30}\n"
        f"🕐 {now}\n\n"
        f"⚠️ *ACTIVE DANGER ZONES IN SABAH* ⚠️\n"
        f"{zones_text}\n"
        f"{'─' * 30}\n"
        f"🛡️ *SAFETY REMINDERS:*\n"
        f"• Do NOT swim in rivers, estuaries or mangroves\n"
        f"• Keep children away from riverbanks\n"
        f"• Do NOT feed or approach crocodiles\n"
        f"• Report sightings to Jabatan Hidupan Liar Sabah\n"
        f"  📞 *088-251566*\n\n"
        f"_Use /check\\_location to check if you are near a danger zone._"
    )


def format_location_result(user_lat, user_lon) -> str:
    """Build the full location-check result message."""
    results = []

    for zone in DANGER_ZONES:
        dist = haversine_distance(user_lat, user_lon, zone["lat"], zone["lon"])
        inside = dist <= zone["radius_m"]
        results.append({
            "zone": zone,
            "distance_m": dist,
            "inside": inside,
        })

    # Sort: nearest first
    results.sort(key=lambda x: x["distance_m"])

    # Check if user is inside ANY zone
    danger_zones_inside = [r for r in results if r["inside"]]
    is_safe = len(danger_zones_inside) == 0

    # Header
    if is_safe:
        header = (
            "✅ *YOU ARE CURRENTLY SAFE*\n"
            "You are not within any known crocodile danger zone.\n"
            "_However, always stay alert near water bodies._\n"
        )
    else:
        header = (
            f"🚨 *DANGER! YOU ARE IN A CROCODILE ZONE!*\n"
            f"You are inside *{len(danger_zones_inside)}* danger zone(s)!\n"
            f"*LEAVE THE AREA IMMEDIATELY.*\n"
        )

    # Details for each zone
    details = "\n📍 *NEAREST DANGER ZONES:*\n"
    for r in results[:4]:  # Show top 4 nearest
        z = r["zone"]
        dist_km = r["distance_m"] / 1000
        status = "⚠️ YOU ARE INSIDE!" if r["inside"] else "✅ Safe distance"

        details += (
            f"\n{risk_emoji(z['risk'])} *{z['name']}*\n"
            f"   ├ Status   : {status}\n"
            f"   ├ Distance : `{dist_km:.2f} km`\n"
            f"   ├ Risk     : `{z['risk']}`\n"
            f"   └ Note     : _{z['notes']}_\n"
        )

    footer = (
        f"\n{'─'*30}\n"
        f"📞 *Emergency:* 999\n"
        f"📞 *Wildlife Dept:* 088-251566\n"
        f"_Data: Jabatan Hidupan Liar Sabah_"
    )

    return f"🐊 *LOCATION SAFETY CHECK*\n{'─'*30}\n{header}{details}{footer}"


# ─────────────────────────────────────────────
#   🤖  BOT COMMAND HANDLERS
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    keyboard = [
        [InlineKeyboardButton("📍 Check My Location", callback_data="check_location")],
        [InlineKeyboardButton("🗺️ List All Danger Zones", callback_data="list_zones")],
        [InlineKeyboardButton("ℹ️ About This Bot", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🐊 *Welcome to Crocodile Safety Alert Bot!*\n\n"
        "This bot helps keep you safe in Sabah by:\n"
        "• Sending daily safety alerts\n"
        "• Checking if you are near a danger zone\n"
        "• Listing all known crocodile hotspots\n\n"
        "Choose an option below or type a command:",
        reply_markup=reply_markup,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command."""
    await update.message.reply_text(
        "📖 *AVAILABLE COMMANDS*\n\n"
        "/start — Show main menu\n"
        "/check\\_location — Check if you are near a danger zone\n"
        "/list\\_zones — List all danger zones\n"
        "/alert — Send a safety alert now (admin)\n"
        "/help — Show this help message\n\n"
        "_This bot sends automatic alerts at 6:00 AM and 6:00 PM daily._",
        parse_mode="Markdown",
    )


async def cmd_list_zones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /list_zones — shows all stored danger zones."""
    text = "🗺️ *ALL CROCODILE DANGER ZONES IN SABAH*\n" + "─" * 30 + "\n"
    for i, z in enumerate(DANGER_ZONES, 1):
        text += (
            f"\n*{i}. {z['name']}*\n"
            f"   {risk_emoji(z['risk'])} Risk: `{z['risk']}`\n"
            f"   📍 Coordinates: `{z['lat']}, {z['lon']}`\n"
            f"   ⭕ Danger radius: `{z['radius_m']} m`\n"
            f"   📝 {z['notes']}\n"
        )
    text += "\n_Use /check\\_location to check your distance from these zones._"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_check_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask the user to share their location."""
    # Create a button that requests live location
    location_button = KeyboardButton(
        "📍 Share My Location",
        request_location=True,
    )
    keyboard = ReplyKeyboardMarkup(
        [[location_button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "📍 *Share your location to check safety*\n\n"
        "Press the button below to share your GPS location.\n"
        "_Your location is only used for this check and is not stored._",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send an immediate alert (admin command)."""
    msg = format_scheduled_alert()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process shared location from user."""
    user_location = update.message.location
    user_lat = user_location.latitude
    user_lon = user_location.longitude

    logger.info(f"Location received: {user_lat}, {user_lon}")

    # Remove the location keyboard
    await update.message.reply_text(
        "🔍 Checking your location...",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Build and send the result
    result_text = format_location_result(user_lat, user_lon)
    await update.message.reply_text(result_text, parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    if query.data == "check_location":
        # Send a new message asking for location
        location_button = KeyboardButton("📍 Share My Location", request_location=True)
        keyboard = ReplyKeyboardMarkup(
            [[location_button]], resize_keyboard=True, one_time_keyboard=True
        )
        await query.message.reply_text(
            "📍 Press the button below to share your GPS location:",
            reply_markup=keyboard,
        )

    elif query.data == "list_zones":
        text = "🗺️ *ALL CROCODILE DANGER ZONES*\n" + "─" * 28 + "\n"
        for i, z in enumerate(DANGER_ZONES, 1):
            text += (
                f"\n*{i}. {z['name']}*"
                f"\n   {risk_emoji(z['risk'])} `{z['risk']}` — radius `{z['radius_m']}m`"
                f"\n   _{z['notes']}_\n"
            )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif query.data == "about":
        await query.message.reply_text(
            "🐊 *About Crocodile Safety Alert Bot*\n\n"
            "Built as a PBL (Project-Based Learning) project\n"
            "by a student of SM Lok Yuk Likas (CF), Kota Kinabalu.\n\n"
            "*Project:* Buaya Tembaga di Sabah\n"
            "*Purpose:* Public safety awareness\n"
            "*Data source:* Jabatan Hidupan Liar Sabah\n\n"
            "_Crocodylus porosus_ (Buaya Tembaga) is a protected\n"
            "but dangerous species. Coexistence requires awareness.",
            parse_mode="Markdown",
        )


# ─────────────────────────────────────────────
#   ⏰  SCHEDULER (runs in background thread)
# ─────────────────────────────────────────────

# We keep a reference to the application so the scheduler can use it
_app_ref = None


def send_scheduled_alert():
    """Called by schedule — sends alert to the group chat."""
    if _app_ref is None:
        return
    msg = format_scheduled_alert()
    asyncio.run_coroutine_threadsafe(
        _app_ref.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=msg,
            parse_mode="Markdown",
        ),
        _app_ref._loop,
    )
    logger.info("Scheduled alert sent to group.")


def run_scheduler():
    """Background thread that runs the schedule loop."""
    # Set times for daily alerts (24-hour format)
    schedule.every().day.at("06:00").do(send_scheduled_alert)
    schedule.every().day.at("18:00").do(send_scheduled_alert)

    logger.info("Scheduler started. Alerts at 06:00 and 18:00 daily.")

    while True:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds


# ─────────────────────────────────────────────
#   🚀  MAIN — START THE BOT
# ─────────────────────────────────────────────

async def debug_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Print the chat ID to your console immediately
    print("✅ CHAT ID:", chat_id)
    # Optional: send a message back to confirm
    await update.message.reply_text(f"This chat ID is:\n`{chat_id}`")

def main():
    global _app_ref

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please fill in your BOT_TOKEN in bot.py!")
        return

    if GROUP_CHAT_ID.endswith('`'):
        print("❌ ERROR: Remove backtick from GROUP_CHAT_ID!")
        return

    print("🐊 Starting Crocodile Safety Alert Bot...")

    # Build the application (async v20+ style)
    app = Application.builder().token(BOT_TOKEN).build()
    _app_ref = app

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list_zones", cmd_list_zones))
    app.add_handler(CommandHandler("check_location", cmd_check_location))
    app.add_handler(CommandHandler("alert", cmd_alert))

    # Register location handler (user shares GPS)
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Register inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    print("✅ Bot is running! Press Ctrl+C to stop.")
    print(f"⏰ Scheduled alerts: 06:00 and 18:00 daily")
    print(f"📍 Location checking: ENABLED")
    print(f"🗺️  Danger zones loaded: {len(DANGER_ZONES)}")

    # Start polling (async v20+)
    app.run_polling()
