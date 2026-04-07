"""
=============================================================
  TELEGRAM CROCODILE SAFETY ALERT SYSTEM
  For SM Lok Yuk Likas PBL Project
  Author: Student Project
=============================================================

HOW TO RUN:
1. Install libraries:  pip install python-telegram-bot==20.7 schedule requests
2. Set environment variables: BOT_TOKEN, GROUP_CHAT_ID
3. Run:  python bot.py
"""

import asyncio
import logging
import math
import schedule
import time
import threading
from datetime import datetime
import os

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
#   ⚙️  CONFIGURATION
# ─────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#   🐊  DANGER ZONE DATA
# ─────────────────────────────────────────────
DANGER_ZONES = [
    {"name": "Sungai Tuaran", "lat": 6.1833, "lon": 116.3500, "radius_m": 1500, "risk": "HIGH", "notes": "Tembaga crocodile sightings reported frequently."},
    {"name": "Teluk Likas (Pantai Likas)", "lat": 5.9928, "lon": 116.0742, "radius_m": 1000, "risk": "HIGH", "notes": "Mangrove area — active crocodile habitat."},
    {"name": "Sungai Kalumpang", "lat": 5.8500, "lon": 116.1000, "radius_m": 2000, "risk": "MEDIUM", "notes": "Occasional sightings during low tide."},
    {"name": "Kuala Penyu Estuary", "lat": 5.6167, "lon": 115.6000, "radius_m": 3000, "risk": "HIGH", "notes": "Remote estuary — high crocodile population."},
    {"name": "Sungai Kinabatangan", "lat": 5.4167, "lon": 118.0833, "radius_m": 5000, "risk": "HIGH", "notes": "World-famous crocodile habitat. Do NOT swim here."},
    {"name": "Pulau Tiga Waters", "lat": 5.6700, "lon": 115.6700, "radius_m": 2500, "risk": "MEDIUM", "notes": "Surrounding waters reported with croc activity."},
]

# ─────────────────────────────────────────────
#   📐 Haversine formula
# ─────────────────────────────────────────────
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ─────────────────────────────────────────────
#   🎨 Message formatting
# ─────────────────────────────────────────────
def risk_emoji(risk: str) -> str:
    return {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(risk, "⚪")

def format_scheduled_alert() -> str:
    now = datetime.now().strftime("%d %b %Y  |  %H:%M")
    zones_text = ""
    for z in DANGER_ZONES:
        zones_text += f"\n{risk_emoji(z['risk'])} *{z['name']}*\n   ├ Risk : `{z['risk']}`\n   ├ Radius : `{z['radius_m']} m`\n   └ Note : _{z['notes']}_\n"
    return f"🐊 *CROCODILE SAFETY ALERT*\n{'─'*30}\n🕐 {now}\n\n⚠️ *ACTIVE DANGER ZONES IN SABAH* ⚠️\n{zones_text}\n{'─'*30}\n🛡️ *SAFETY REMINDERS:*\n• Do NOT swim in rivers, estuaries or mangroves\n• Keep children away from riverbanks\n• Do NOT feed or approach crocodiles\n• Report sightings to Jabatan Hidupan Liar Sabah\n  📞 *088-251566*\n\n_Use /check\\_location to check if you are near a danger zone._"

def format_location_result(user_lat, user_lon) -> str:
    results = []
    for zone in DANGER_ZONES:
        dist = haversine_distance(user_lat, user_lon, zone["lat"], zone["lon"])
        inside = dist <= zone["radius_m"]
        results.append({"zone": zone, "distance_m": dist, "inside": inside})
    results.sort(key=lambda x: x["distance_m"])
    danger_zones_inside = [r for r in results if r["inside"]]
    is_safe = len(danger_zones_inside) == 0

    header = "✅ *YOU ARE CURRENTLY SAFE*\nYou are not within any known crocodile danger zone.\n_However, always stay alert near water bodies._\n" if is_safe else f"🚨 *DANGER! YOU ARE IN A CROCODILE ZONE!*\nYou are inside *{len(danger_zones_inside)}* danger zone(s)!\n*LEAVE THE AREA IMMEDIATELY.*\n"

    details = "\n📍 *NEAREST DANGER ZONES:*\n"
    for r in results[:4]:
        z = r["zone"]
        dist_km = r["distance_m"] / 1000
        status = "⚠️ YOU ARE INSIDE!" if r["inside"] else "✅ Safe distance"
        details += f"\n{risk_emoji(z['risk'])} *{z['name']}*\n   ├ Status   : {status}\n   ├ Distance : `{dist_km:.2f} km`\n   ├ Risk     : `{z['risk']}`\n   └ Note     : _{z['notes']}_\n"

    footer = f"\n{'─'*30}\n📞 *Emergency:* 999\n📞 *Wildlife Dept:* 088-251566\n_Data: Jabatan Hidupan Liar Sabah_"
    return f"🐊 *LOCATION SAFETY CHECK*\n{'─'*30}\n{header}{details}{footer}"

# ─────────────────────────────────────────────
#   🤖 Bot Handlers
# ─────────────────────────────────────────────
_app_ref = None  # global reference for scheduler

async def async_scheduler():
    while True:
        now = datetime.now()
        if now.hour in [6, 18] and now.minute == 0 and _app_ref:
            msg = format_scheduled_alert()
            await _app_ref.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode="Markdown")
        await asyncio.sleep(60)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📍 Check My Location", callback_data="check_location")],
        [InlineKeyboardButton("🗺️ List All Danger Zones", callback_data="list_zones")],
        [InlineKeyboardButton("ℹ️ About This Bot", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🐊 *Welcome to Crocodile Safety Alert Bot!*\n\nThis bot helps keep you safe in Sabah by:\n• Sending daily safety alerts\n• Checking if you are near a danger zone\n• Listing all known crocodile hotspots\n\nChoose an option below or type a command:", reply_markup=reply_markup)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📖 *AVAILABLE COMMANDS*\n\n/start — Show main menu\n/check\\_location — Check if you are near a danger zone\n/list\\_zones — List all danger zones\n/alert — Send a safety alert now (admin)\n/help — Show this help message\n\n_This bot sends automatic alerts at 6:00 AM and 6:00 PM daily._", parse_mode="Markdown")

async def cmd_list_zones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🗺️ *ALL CROCODILE DANGER ZONES IN SABAH*\n" + "─"*30 + "\n"
    for i, z in enumerate(DANGER_ZONES, 1):
        text += f"\n*{i}. {z['name']}*\n   {risk_emoji(z['risk'])} Risk: `{z['risk']}`\n   📍 Coordinates: `{z['lat']}, {z['lon']}`\n   ⭕ Danger radius: `{z['radius_m']} m`\n   📝 {z['notes']}\n"
    text += "\n_Use /check\\_location to check your distance from these zones._"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_check_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_button = KeyboardButton("📍 Share My Location", request_location=True)
    keyboard = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("📍 *Share your location to check safety*\n\nPress the button below to share your GPS location.\n_Your location is only used for this check and is not stored._", parse_mode="Markdown", reply_markup=keyboard)

async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = format_scheduled_alert()
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_location = update.message.location
    result_text = format_location_result(user_location.latitude, user_location.longitude)
    await update.message.reply_text("🔍 Checking your location...", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(result_text, parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_location":
        await cmd_check_location(update, context)
    elif query.data == "list_zones":
        await cmd_list_zones(update, context)
    elif query.data == "about":
        await query.message.reply_text("🐊 *About Crocodile Safety Alert Bot*\nBuilt as a PBL project by SM Lok Yuk Likas students.\nData source: Jabatan Hidupan Liar Sabah.", parse_mode="Markdown")

def send_scheduled_alert():
    if _app_ref is None:
        return
    msg = format_scheduled_alert()
    asyncio.run_coroutine_threadsafe(_app_ref.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode="Markdown"), _app_ref._loop)
    logger.info("Scheduled alert sent.")

def run_scheduler():
    schedule.every().day.at("06:00").do(send_scheduled_alert)
    schedule.every().day.at("18:00").do(send_scheduled_alert)
    logger.info("Scheduler started: 06:00 & 18:00 daily")
    while True:
        schedule.run_pending()
        time.sleep(30)

# ─────────────────────────────────────────────
#   🚀 Main
# ─────────────────────────────────────────────
def main():
    global _app_ref

    if not BOT_TOKEN or not GROUP_CHAT_ID:
        print("❌ ERROR: BOT_TOKEN or GROUP_CHAT_ID not set!")
        return

    print("🐊 Starting Crocodile Safety Alert Bot...")

    app = Application.builder().token(BOT_TOKEN).build()
    _app_ref = app

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list_zones", cmd_list_zones))
    app.add_handler(CommandHandler("check_location", cmd_check_location))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Scheduler
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.create_task(async_scheduler())

    print(f"✅ Bot is running! Danger zones loaded: {len(DANGER_ZONES)}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
