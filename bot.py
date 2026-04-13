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
    {"name": "Sungai Tuaran",            "lat": 6.1833, "lon": 116.3500, "radius_m": 1500, "risk": "HIGH",   "notes": "Tembaga crocodile sightings reported frequently.",       "fisher_warning": True,  "fisher_note": "Nelayan kerap menangkap ikan di kawasan ini — BERHATI-HATI."},
    {"name": "Teluk Likas (Pantai Likas)","lat": 5.9928, "lon": 116.0742, "radius_m": 1000, "risk": "HIGH",   "notes": "Mangrove area — active crocodile habitat.",              "fisher_warning": True,  "fisher_note": "Kawasan bakau — buaya aktif terutama waktu fajar dan senja."},
    {"name": "Sungai Kalumpang",          "lat": 5.8500, "lon": 116.1000, "radius_m": 2000, "risk": "MEDIUM", "notes": "Occasional sightings during low tide.",                  "fisher_warning": True,  "fisher_note": "Aktiviti memancing tinggi di sini — jangan pergi bersendirian."},
    {"name": "Kuala Penyu Estuary",       "lat": 5.6167, "lon": 115.6000, "radius_m": 3000, "risk": "HIGH",   "notes": "Remote estuary — high crocodile population.",            "fisher_warning": True,  "fisher_note": "Kuala sungai terpencil — populasi buaya sangat tinggi."},
    {"name": "Sungai Kinabatangan",       "lat": 5.4167, "lon": 118.0833, "radius_m": 5000, "risk": "HIGH",   "notes": "World-famous crocodile habitat. Do NOT swim here.",      "fisher_warning": True,  "fisher_note": "Sungai paling berbahaya di Sabah — JANGAN berenang sama sekali."},
    {"name": "Pulau Tiga Waters",         "lat": 5.6700, "lon": 115.6700, "radius_m": 2500, "risk": "MEDIUM", "notes": "Surrounding waters reported with crocodile activity.",   "fisher_warning": False, "fisher_note": ""},
]

CCTV_URL = "http://192.168.0.54:5000/"

# ── Helpers ──────────────────────────────────────────────────

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def risk_emoji(risk):
    return {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(risk, "⚪")

def line():
    return "─" * 30

# ── Message builders ──────────────────────────────────────────

def format_scheduled_alert():
    now = datetime.now().strftime("%d %b %Y | %H:%M")
    zones_text = ""
    for z in DANGER_ZONES:
        zones_text += (
            f"\n{risk_emoji(z['risk'])} <b>{z['name']}</b>\n"
            f"   Risk: <code>{z['risk']}</code> | Radius: <code>{z['radius_m']} m</code>\n"
            f"   <i>{z['notes']}</i>\n"
        )
    return (
        f"🐊 <b>CROCODILE SAFETY ALERT</b>\n"
        f"{line()}\n"
        f"🕐 {now}\n\n"
        f"⚠️ <b>ACTIVE DANGER ZONES IN SABAH</b> ⚠️\n"
        f"{zones_text}\n"
        f"{line()}\n"
        f"🛡️ <b>SAFETY REMINDERS:</b>\n"
        f"• Do NOT swim in rivers, estuaries or mangroves\n"
        f"• Keep children away from riverbanks\n"
        f"• Do NOT feed or approach crocodiles\n"
        f"• Report sightings to Jabatan Hidupan Liar Sabah\n"
        f"  📞 <b>088-251566</b>\n\n"
        f"<i>Use /check_location (in DM) to check if you are near a danger zone.</i>"
    )

def format_fisher_alert():
    now = datetime.now()
    time_str = now.strftime("%d %b %Y | %H:%M")
    if now.hour < 12:
        time_context = "🌅 <b>AMARAN PAGI — Sebelum Anda Turun Memancing!</b>"
        time_advice = "Waktu fajar adalah masa buaya paling aktif mencari makan."
    else:
        time_context = "🌇 <b>AMARAN PETANG — Sebelum Anda Pulang!</b>"
        time_advice = "Waktu senja adalah masa buaya paling berbahaya di tepi sungai."

    fisher_zones = [z for z in DANGER_ZONES if z.get("fisher_warning")]
    zones_text = ""
    for z in fisher_zones:
        zones_text += (
            f"\n{risk_emoji(z['risk'])} <b>{z['name']}</b>\n"
            f"   Tahap Risiko: <code>{z['risk']}</code> | Zon Bahaya: <code>{z['radius_m']} m</code>\n"
            f"   ⚠️ <i>{z['fisher_note']}</i>\n"
        )

    return (
        f"🎣🐊 <b>AMARAN KESELAMATAN UNTUK NELAYAN</b>\n"
        f"{line()}\n"
        f"🕐 {time_str}\n\n"
        f"{time_context}\n"
        f"<i>{time_advice}</i>\n\n"
        f"⚠️ <b>KAWASAN BERBAHAYA BERDEKATAN TASIK DAN SUNGAI:</b>\n"
        f"{zones_text}\n"
        f"{line()}\n"
        f"🛡️ <b>TIPS KESELAMATAN NELAYAN:</b>\n"
        f"• Jangan memancing bersendirian — bawa rakan\n"
        f"• Elakkan duduk terlalu dekat dengan tepi air\n"
        f"• Jangan buang sisa ikan ke dalam sungai\n"
        f"• Jangan memancing dalam gelap tanpa lampu\n"
        f"• Jika nampak buaya — BERUNDUR dengan tenang\n"
        f"• JANGAN berlari atau buat bunyi yang kuat\n\n"
        f"📹 <b>Pantau Kawasan Secara Langsung (CCTV Live):</b>\n"
        f"<a href=\"{CCTV_URL}\">{CCTV_URL}</a>\n\n"
        f"📞 <b>Kecemasan:</b> 999\n"
        f"📞 <b>Jabatan Hidupan Liar Sabah:</b> 088-251566\n\n"
        f"<i>Selamat memancing. Ingat — keselamatan lebih penting!</i> 🙏"
    )

def format_location_result(user_lat, user_lon):
    results = []
    for zone in DANGER_ZONES:
        dist = haversine_distance(user_lat, user_lon, zone["lat"], zone["lon"])
        results.append({"zone": zone, "distance_m": dist, "inside": dist <= zone["radius_m"]})
    results.sort(key=lambda x: x["distance_m"])
    inside_list = [r for r in results if r["inside"]]
    is_safe = len(inside_list) == 0

    if is_safe:
        header = (
            "✅ <b>YOU ARE CURRENTLY SAFE</b>\n"
            "You are not within any known crocodile danger zone.\n"
            "<i>However, always stay alert near water bodies.</i>\n"
        )
    else:
        header = (
            f"🚨 <b>DANGER! YOU ARE IN A CROCODILE ZONE!</b>\n"
            f"You are inside <b>{len(inside_list)}</b> danger zone(s)!\n"
            f"<b>LEAVE THE AREA IMMEDIATELY.</b>\n"
        )

    details = "\n📍 <b>NEAREST DANGER ZONES:</b>\n"
    for r in results[:4]:
        z = r["zone"]
        status = "⚠️ YOU ARE INSIDE!" if r["inside"] else "✅ Safe distance"
        details += (
            f"\n{risk_emoji(z['risk'])} <b>{z['name']}</b>\n"
            f"   Status: {status}\n"
            f"   Distance: <code>{r['distance_m']/1000:.2f} km</code>\n"
            f"   Risk: <code>{z['risk']}</code>\n"
            f"   <i>{z['notes']}</i>\n"
        )

    return (
        f"🐊 <b>LOCATION SAFETY CHECK</b>\n"
        f"{line()}\n"
        f"{header}"
        f"{details}\n"
        f"{line()}\n"
        f"📞 <b>Emergency:</b> 999\n"
        f"📞 <b>Wildlife Dept:</b> 088-251566\n"
        f"<i>Data: Jabatan Hidupan Liar Sabah</i>"
    )

def build_zones_text():
    text = f"🗺️ <b>ALL CROCODILE DANGER ZONES IN SABAH</b>\n{line()}\n"
    for i, z in enumerate(DANGER_ZONES, 1):
        fisher_tag = " 🎣" if z.get("fisher_warning") else ""
        text += (
            f"\n<b>{i}. {z['name']}</b>{fisher_tag}\n"
            f"   {risk_emoji(z['risk'])} Risk: <code>{z['risk']}</code>\n"
            f"   📍 <code>{z['lat']}, {z['lon']}</code>\n"
            f"   ⭕ Radius: <code>{z['radius_m']} m</code>\n"
            f"   📝 <i>{z['notes']}</i>\n"
        )
    text += "\n🎣 = Active fishing area with special fisher warnings\n"
    text += "<i>Use /check_location (in DM) to check your distance.</i>"
    return text

# ── Global app reference for scheduler ──
_app_ref = None
_event_loop = None  # FIX: store the event loop explicitly

# ── Handlers ─────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        # FIX: updated label to clarify DM-only for location check
        [InlineKeyboardButton("📍 Check My Location (only works in DM)", callback_data="check_location")],
        [InlineKeyboardButton("🗺️ List All Danger Zones",                callback_data="list_zones")],
        [InlineKeyboardButton("🎣 Fisher Safety Alert",                  callback_data="fisher_alert")],
        [InlineKeyboardButton("📹 Live CCTV Feed",                       callback_data="cctv")],
        [InlineKeyboardButton("ℹ️ About This Bot",                       callback_data="about")],
    ]
    await update.message.reply_text(
        "🐊 <b>Welcome to Crocodile Safety Alert Bot!</b>\n\n"
        "This bot helps keep you safe in Sabah by:\n"
        "• Sending daily safety alerts at 6AM and 6PM\n"
        "• Special warnings for fishers near rivers and lakes\n"
        "• Checking if you are near a danger zone\n"
        "• Live CCTV monitoring feed\n\n"
        "Choose an option below:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>AVAILABLE COMMANDS</b>\n\n"
        "/start — Show main menu\n"
        "/check_location — Check if you are near a danger zone <i>(DM only)</i>\n"
        "/list_zones — List all danger zones\n"
        "/alert — Send general safety alert now\n"
        "/fisher — Send fisher warning now\n"
        "/cctv — Get live CCTV feed link\n"
        "/help — Show this help message\n\n"
        "<i>Automatic alerts at 6:00 AM and 6:00 PM daily.</i>",
        parse_mode="HTML",
    )

async def cmd_list_zones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_zones_text(), parse_mode="HTML")

async def cmd_check_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Warn if used in a group
    if update.message.chat.type != "private":
        await update.message.reply_text(
            "⚠️ <b>Sila guna arahan ini dalam DM (chat persendirian) dengan bot.</b>\n\n"
            "Cari bot ini dan hantar /check_location secara terus.",
            parse_mode="HTML",
        )
        return
    location_button = KeyboardButton("📍 Share My Location", request_location=True)
    await update.message.reply_text(
        "📍 <b>Share your location to check safety</b>\n\n"
        "Press the button below to share your GPS location.\n"
        "<i>Your location is only used for this check and is not stored.</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True),
    )

async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_scheduled_alert(), parse_mode="HTML")

async def cmd_fisher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_fisher_alert(), parse_mode="HTML")

async def cmd_cctv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📹 <b>Live CCTV Feed</b>\n\n"
        f"Pantau kawasan secara langsung:\n"
        f"<a href=\"{CCTV_URL}\">{CCTV_URL}</a>\n\n"
        f"<i>Pastikan anda bersambung ke rangkaian yang sama untuk akses.</i>",
        parse_mode="HTML",
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    await update.message.reply_text("🔍 Checking your location...", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(format_location_result(loc.latitude, loc.longitude), parse_mode="HTML")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_location":
        # If in group, redirect to DM
        if query.message.chat.type != "private":
            await query.message.reply_text(
                "⚠️ <b>Fungsi ini hanya boleh digunakan dalam DM.</b>\n\n"
                "Buka chat persendirian dengan bot ini dan taip /check_location.",
                parse_mode="HTML",
            )
            return
        location_button = KeyboardButton("📍 Share My Location", request_location=True)
        await query.message.reply_text(
            "📍 <b>Share your location to check safety</b>\n\n"
            "Press the button below to share your GPS location.\n"
            "<i>Your location is only used for this check and is not stored.</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True),
        )
    elif query.data == "list_zones":
        await query.message.reply_text(build_zones_text(), parse_mode="HTML")
    elif query.data == "fisher_alert":
        await query.message.reply_text(format_fisher_alert(), parse_mode="HTML")
    elif query.data == "cctv":
        await query.message.reply_text(
            f"📹 <b>Live CCTV Feed</b>\n\n"
            f"Pantau kawasan secara langsung:\n"
            f"<a href=\"{CCTV_URL}\">{CCTV_URL}</a>\n\n"
            f"<i>Pastikan anda bersambung ke rangkaian yang sama untuk akses.</i>",
            parse_mode="HTML",
        )
    elif query.data == "about":
        await query.message.reply_text(
            "🐊 <b>About Crocodile Safety Alert Bot</b>\n\n"
            "Built as a PBL project by students of\n"
            "SM Lok Yuk Likas (CF), Kota Kinabalu, Sabah.\n\n"
            "<b>Project:</b> Buaya Tembaga di Sabah\n"
            "<b>Purpose:</b> Public and fisher safety awareness\n"
            "<b>Data source:</b> Jabatan Hidupan Liar Sabah\n\n"
            "<i>Crocodylus porosus</i> — dilindungi tapi berbahaya.",
            parse_mode="HTML",
        )

# ── Scheduler ────────────────────────────────────────────────
# FIX: Instead of using _app_ref._loop (unreliable),
# we store the running event loop explicitly when main() starts,
# then use asyncio.run_coroutine_threadsafe with that stored loop.

def _send_general_alert():
    if _app_ref and _event_loop:
        future = asyncio.run_coroutine_threadsafe(
            _app_ref.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=format_scheduled_alert(),
                parse_mode="HTML",
            ),
            _event_loop,
        )
        try:
            future.result(timeout=15)  # wait up to 15s for confirmation
            logger.info("General alert sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send general alert: {e}")

def _send_fisher_alert():
    if _app_ref and _event_loop:
        future = asyncio.run_coroutine_threadsafe(
            _app_ref.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=format_fisher_alert(),
                parse_mode="HTML",
            ),
            _event_loop,
        )
        try:
            future.result(timeout=15)
            logger.info("Fisher alert sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send fisher alert: {e}")

def run_scheduler():
    schedule.every().day.at("06:00").do(_send_fisher_alert)
    schedule.every().day.at("06:01").do(_send_general_alert)
    schedule.every().day.at("18:00").do(_send_fisher_alert)
    schedule.every().day.at("18:01").do(_send_general_alert)
    logger.info("Scheduler ready: 06:00 and 18:00 daily")
    while True:
        schedule.run_pending()
        time.sleep(30)

# ── Post-init hook to capture the running event loop ─────────

async def on_startup(app: Application):
    """Called after the bot starts — captures the running event loop."""
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    logger.info(f"Event loop captured. Scheduler will use this loop.")
    logger.info(f"Bot started. Zones: {len(DANGER_ZONES)} | Group: {GROUP_CHAT_ID}")

# ── Main ─────────────────────────────────────────────────────

def main():
    global _app_ref
    if not BOT_TOKEN or not GROUP_CHAT_ID:
        print("ERROR: BOT_TOKEN or GROUP_CHAT_ID not set!")
        return
    print("Starting Crocodile Safety Alert Bot...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)   # FIX: capture event loop after bot starts
        .build()
    )
    _app_ref = app

    app.add_handler(CommandHandler("start",          cmd_start))
    app.add_handler(CommandHandler("help",           cmd_help))
    app.add_handler(CommandHandler("list_zones",     cmd_list_zones))
    app.add_handler(CommandHandler("check_location", cmd_check_location))
    app.add_handler(CommandHandler("alert",          cmd_alert))
    app.add_handler(CommandHandler("fisher",         cmd_fisher))
    app.add_handler(CommandHandler("cctv",           cmd_cctv))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Start scheduler in background thread
    threading.Thread(target=run_scheduler, daemon=True).start()

    fisher_count = sum(1 for z in DANGER_ZONES if z.get("fisher_warning"))
    print(f"Bot running! Zones: {len(DANGER_ZONES)} | Fisher zones: {fisher_count}")
    print("Scheduled: 06:00 and 18:00 daily")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
