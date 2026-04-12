"""
=============================================================
  TELEGRAM CROCODILE SAFETY ALERT SYSTEM
  For SM Lok Yuk Likas PBL Project
=============================================================
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
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DANGER_ZONES = [
    {"name": "Sungai Tuaran", "lat": 6.1833, "lon": 116.3500, "radius_m": 1500, "risk": "HIGH", "notes": "Tembaga crocodile sightings reported frequently.", "fisher_warning": True, "fisher_note": "Nelayan kerap menangkap ikan di kawasan ini — BERHATI-HATI."},
    {"name": "Teluk Likas (Pantai Likas)", "lat": 5.9928, "lon": 116.0742, "radius_m": 1000, "risk": "HIGH", "notes": "Mangrove area — active crocodile habitat.", "fisher_warning": True, "fisher_note": "Kawasan bakau — buaya aktif terutama waktu fajar & senja."},
    {"name": "Sungai Kalumpang", "lat": 5.8500, "lon": 116.1000, "radius_m": 2000, "risk": "MEDIUM", "notes": "Occasional sightings during low tide.", "fisher_warning": True, "fisher_note": "Aktiviti memancing tinggi di sini — jangan pergi bersendirian."},
    {"name": "Kuala Penyu Estuary", "lat": 5.6167, "lon": 115.6000, "radius_m": 3000, "risk": "HIGH", "notes": "Remote estuary — high crocodile population.", "fisher_warning": True, "fisher_note": "Kuala sungai terpencil — populasi buaya sangat tinggi."},
    {"name": "Sungai Kinabatangan", "lat": 5.4167, "lon": 118.0833, "radius_m": 5000, "risk": "HIGH", "notes": "World-famous crocodile habitat. Do NOT swim here.", "fisher_warning": True, "fisher_note": "Sungai paling berbahaya di Sabah — JANGAN berenang sama sekali."},
    {"name": "Pulau Tiga Waters", "lat": 5.6700, "lon": 115.6700, "radius_m": 2500, "risk": "MEDIUM", "notes": "Surrounding waters reported with croc activity.", "fisher_warning": False, "fisher_note": ""},
]

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def risk_emoji(risk):
    return {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(risk, "⚪")

def format_scheduled_alert():
    now = datetime.now().strftime("%d %b %Y  |  %H:%M")
    zones_text = ""
    for z in DANGER_ZONES:
        zones_text += f"\n{risk_emoji(z['risk'])} *{z['name']}*\n   ├ Risk   : `{z['risk']}`\n   ├ Radius : `{z['radius_m']} m`\n   └ Note   : _{z['notes']}_\n"
    return (f"🐊 *CROCODILE SAFETY ALERT*\n{'─'*30}\n🕐 {now}\n\n⚠️ *ACTIVE DANGER ZONES IN SABAH* ⚠️\n{zones_text}\n{'─'*30}\n🛡️ *SAFETY REMINDERS:*\n• Do NOT swim in rivers, estuaries or mangroves\n• Keep children away from riverbanks\n• Do NOT feed or approach crocodiles\n• Report sightings to Jabatan Hidupan Liar Sabah\n  📞 *088-251566*\n\n_Use /check\\_location to check if you are near a danger zone._")

def format_fisher_alert():
    now = datetime.now()
    time_str = now.strftime("%d %b %Y  |  %H:%M")
    if now.hour < 12:
        time_context = "🌅 *AMARAN PAGI — Sebelum Anda Turun Memancing!*"
        time_advice = "Waktu fajar adalah masa buaya paling aktif mencari makan."
    else:
        time_context = "🌇 *AMARAN PETANG — Sebelum Anda Pulang!*"
        time_advice = "Waktu senja adalah masa buaya paling berbahaya di tepi sungai."
    fisher_zones = [z for z in DANGER_ZONES if z.get("fisher_warning")]
    zones_text = ""
    for z in fisher_zones:
        zones_text += f"\n{risk_emoji(z['risk'])} *{z['name']}*\n   ├ Tahap Risiko : `{z['risk']}`\n   ├ Zon Bahaya   : `{z['radius_m']} m radius`\n   └ ⚠️ _{z['fisher_note']}_\n"
    return (f"🎣🐊 *AMARAN KESELAMATAN UNTUK NELAYAN*\n{'─'*32}\n🕐 {time_str}\n\n{time_context}\n_{time_advice}_\n\n⚠️ *KAWASAN BERBAHAYA BERDEKATAN TASIK & SUNGAI:*\n{zones_text}\n{'─'*32}\n🛡️ *TIPS KESELAMATAN NELAYAN:*\n• Jangan memancing bersendirian — bawa rakan\n• Elakkan duduk terlalu dekat dengan tepi air\n• Jangan buang sisa ikan ke dalam sungai\n• Jangan memancing dalam gelap tanpa lampu\n• Jika nampak buaya — BERUNDUR dengan tenang\n• JANGAN berlari atau buat bunyi yang kuat\n\n📞 *Kecemasan:* 999\n📞 *Jabatan Hidupan Liar Sabah:* 088-251566\n\n_Selamat memancing. Ingat — keselamatan lebih penting!_ 🙏")

def format_location_result(user_lat, user_lon):
    results = []
    for zone in DANGER_ZONES:
        dist = haversine_distance(user_lat, user_lon, zone["lat"], zone["lon"])
        results.append({"zone": zone, "distance_m": dist, "inside": dist <= zone["radius_m"]})
    results.sort(key=lambda x: x["distance_m"])
    inside_list = [r for r in results if r["inside"]]
    is_safe = len(inside_list) == 0
    header = ("✅ *YOU ARE CURRENTLY SAFE*\nYou are not within any known crocodile danger zone.\n_However, always stay alert near water bodies._\n" if is_safe else f"🚨 *DANGER! YOU ARE IN A CROCODILE ZONE!*\nYou are inside *{len(inside_list)}* danger zone(s)!\n*LEAVE THE AREA IMMEDIATELY.*\n")
    details = "\n📍 *NEAREST DANGER ZONES:*\n"
    for r in results[:4]:
        z = r["zone"]
        status = "⚠️ YOU ARE INSIDE!" if r["inside"] else "✅ Safe distance"
        details += f"\n{risk_emoji(z['risk'])} *{z['name']}*\n   ├ Status   : {status}\n   ├ Distance : `{r['distance_m']/1000:.2f} km`\n   ├ Risk     : `{z['risk']}`\n   └ Note     : _{z['notes']}_\n"
    return f"🐊 *LOCATION SAFETY CHECK*\n{'─'*30}\n{header}{details}\n{'─'*30}\n📞 *Emergency:* 999\n📞 *Wildlife Dept:* 088-251566\n_Data: Jabatan Hidupan Liar Sabah_"

def build_zones_text():
    text = "🗺️ *ALL CROCODILE DANGER ZONES IN SABAH*\n" + "─"*30 + "\n"
    for i, z in enumerate(DANGER_ZONES, 1):
        fisher_tag = " 🎣" if z.get("fisher_warning") else ""
        text += f"\n*{i}. {z['name']}*{fisher_tag}\n   {risk_emoji(z['risk'])} Risk: `{z['risk']}`\n   📍 `{z['lat']}, {z['lon']}`\n   ⭕ Radius: `{z['radius_m']} m`\n   📝 {z['notes']}\n"
    text += "\n🎣 = Active fishing area with special fisher warnings\n_Use /check\\_location to check your distance._"
    return text

# ── Global app reference for scheduler ──
_app_ref = None

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📍 Check My Location", callback_data="check_location")],
        [InlineKeyboardButton("🗺️ List All Danger Zones", callback_data="list_zones")],
        [InlineKeyboardButton("🎣 Fisher Safety Alert", callback_data="fisher_alert")],
        [InlineKeyboardButton("ℹ️ About This Bot", callback_data="about")],
    ]
    await update.message.reply_text(
        "🐊 *Welcome to Crocodile Safety Alert Bot!*\n\nThis bot helps keep you safe in Sabah by:\n• Sending daily safety alerts at 6AM & 6PM\n• Special warnings for fishers near rivers & lakes\n• Checking if you are near a danger zone\n\nChoose an option below:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *AVAILABLE COMMANDS*\n\n/start — Show main menu\n/check\\_location — Check if you are near a danger zone\n/list\\_zones — List all danger zones\n/alert — Send general safety alert now\n/fisher — Send fisher warning now\n/help — Show this help message\n\n_Automatic alerts at 6:00 AM and 6:00 PM daily._",
        parse_mode="Markdown",
    )

async def cmd_list_zones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_zones_text(), parse_mode="Markdown")

async def cmd_check_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_button = KeyboardButton("📍 Share My Location", request_location=True)
    await update.message.reply_text(
        "📍 *Share your location to check safety*\n\nPress the button below to share your GPS location.\n_Your location is only used for this check and is not stored._",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True),
    )

async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_scheduled_alert(), parse_mode="Markdown")

async def cmd_fisher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_fisher_alert(), parse_mode="Markdown")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    await update.message.reply_text("🔍 Checking your location...", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(format_location_result(loc.latitude, loc.longitude), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    BUG FIX: When an inline button is pressed, update.message is None.
    Must use query.message.reply_text() — NOT update.message.reply_text().
    """
    query = update.callback_query
    await query.answer()  # Always call this first

    if query.data == "check_location":
        location_button = KeyboardButton("📍 Share My Location", request_location=True)
        await query.message.reply_text(
            "📍 *Share your location to check safety*\n\nPress the button below to share your GPS location.\n_Your location is only used for this check and is not stored._",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True),
        )
    elif query.data == "list_zones":
        await query.message.reply_text(build_zones_text(), parse_mode="Markdown")
    elif query.data == "fisher_alert":
        await query.message.reply_text(format_fisher_alert(), parse_mode="Markdown")
    elif query.data == "about":
        await query.message.reply_text(
            "🐊 *About Crocodile Safety Alert Bot*\n\nBuilt as a PBL project by students of\nSM Lok Yuk Likas (CF), Kota Kinabalu, Sabah.\n\n*Project:* Buaya Tembaga di Sabah\n*Purpose:* Public & fisher safety awareness\n*Data source:* Jabatan Hidupan Liar Sabah\n\n_Crocodylus porosus_ — dilindungi tapi berbahaya.",
            parse_mode="Markdown",
        )

def _send_general_alert():
    if _app_ref:
        asyncio.run_coroutine_threadsafe(
            _app_ref.bot.send_message(chat_id=GROUP_CHAT_ID, text=format_scheduled_alert(), parse_mode="Markdown"),
            _app_ref._loop,
        )
        logger.info("General alert sent.")

def _send_fisher_alert():
    if _app_ref:
        asyncio.run_coroutine_threadsafe(
            _app_ref.bot.send_message(chat_id=GROUP_CHAT_ID, text=format_fisher_alert(), parse_mode="Markdown"),
            _app_ref._loop,
        )
        logger.info("Fisher alert sent.")

def run_scheduler():
    # 6:00 AM: fisher warning first, then general alert 1 min later
    schedule.every().day.at("06:00").do(_send_fisher_alert)
    schedule.every().day.at("06:01").do(_send_general_alert)
    # 6:00 PM: same pattern
    schedule.every().day.at("18:00").do(_send_fisher_alert)
    schedule.every().day.at("18:01").do(_send_general_alert)
    logger.info("Scheduler ready: 06:00 & 18:00 daily")
    while True:
        schedule.run_pending()
        time.sleep(30)

def main():
    global _app_ref
    if not BOT_TOKEN or not GROUP_CHAT_ID:
        print("ERROR: BOT_TOKEN or GROUP_CHAT_ID not set!")
        return
    print("Starting Crocodile Safety Alert Bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    _app_ref = app
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list_zones", cmd_list_zones))
    app.add_handler(CommandHandler("check_location", cmd_check_location))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("fisher", cmd_fisher))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback))
    threading.Thread(target=run_scheduler, daemon=True).start()
    fisher_count = sum(1 for z in DANGER_ZONES if z.get("fisher_warning"))
    print(f"Bot running! Total zones: {len(DANGER_ZONES)} | Fisher zones: {fisher_count}")
    print("Scheduled: fisher alert + general alert at 06:00 & 18:00 daily")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
