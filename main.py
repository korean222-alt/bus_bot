import logging
import os
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USERS = [8058101860]

KST = pytz.timezone('Asia/Seoul')

def t(h, m):
    return h * 60 + m

def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def build_weekend_trips():
    trips = []
    for h in range(8, 17):
        trips.append([("L", t(h, 33)), ("J", t(h, 36))])
    for h in range(8, 17):
        trips.append([("J", t(h, 47)), ("L", t(h, 50)), ("P", t(h, 57))])
    for h in range(9, 18):
        trips.append([("P", t(h, 8)), ("L", t(h, 11)), ("J", t(h, 14))])
    trips.sort(key=lambda trip: trip[0][1])
    return trips

def build_weekday_trips():
    trips = []
    trips.append([("L", t(16, 17)), ("P", t(16, 21))])
    trips.append([("L", t(17, 12)), ("P", t(17, 16))])
    trips.append([("L", t(17, 37)), ("P", t(17, 40))])
    trips.append([("P", t(16, 34)), ("L", t(16, 36))])
    trips.append([("P", t(17, 30)), ("L", t(17, 32))])
    trips.append([("P", t(17, 54)), ("L", t(17, 57))])
    trips.sort(key=lambda trip: trip[0][1])
    return trips

WEEKEND_TRIPS = build_weekend_trips()
WEEKDAY_TRIPS = build_weekday_trips()

def find_next_buses(from_stop, to_stop, trips, now_min, delay=0, count=3):
    results = []
    for trip in trips:
        stops = [s[0] for s in trip]
        if from_stop in stops and to_stop in stops:
            fi = stops.index(from_stop)
            ti = stops.index(to_stop)
            if fi < ti:
                dep = trip[fi][1] + delay
                arr = trip[ti][1] + delay
                if dep >= now_min:
                    results.append((dep, arr))
                    if len(results) >= count:
                        break
    return results

def find_last_bus(from_stop, to_stop, trips):
    last = None
    for trip in trips:
        stops = [s[0] for s in trip]
        if from_stop in stops and to_stop in stops:
            fi = stops.index(from_stop)
            ti = stops.index(to_stop)
            if fi < ti:
                last = (trip[fi][1], trip[ti][1])
    return last

async def query_buses(update, from_stop, to_stop, delay=0):
    now = datetime.now(KST)
    now_min = now.hour * 60 + now.minute
    is_weekend = now.weekday() >= 5
    sched_name = "주말" if is_weekend else "평일"
    trips = WEEKEND_TRIPS if is_weekend else WEEKDAY_TRIPS
    buses = find_next_buses(from_stop, to_stop, trips, now_min, delay, count=3)
    if not buses:
        await update.message.reply_text("오늘 " + from_stop + "->" + to_stop + " 버스는 더 없습니다.")
        return
    delay_tag = " [지연+30분]" if delay else ""
    msg = "버스 " + from_stop + "->" + to_stop + delay_tag + " (" + sched_name + ")\n"
    msg += "---\n"
    for i, (dep, arr) in enumerate(buses):
        wait = dep - now_min
        duration = arr - dep
        if i == 0:
            msg += "다음: " + fmt(dep) + "->" + fmt(arr) + " (" + str(wait) + "분후, " + str(duration) + "분소요)\n"
        else:
            msg += str(i+1) + "번째: " + fmt(dep) + "->" + fmt(arr) + "\n"
    await update.message.reply_text(msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("권한이 없습니다.")
        return
    msg = "버스 시간표 봇\n\n즐겨찾기:\n/1 L->P\n/2 P->L\n/3 L->P 지연\n/4 P->L 지연\n\n직접입력: j-p, l-p 등\n지연: g l-p\n\n/all 전체보기\n/last 막차확인"
    await update.message.reply_text(msg)

async def fav1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("권한이 없습니다.")
        return
    await query_buses(update, "L", "P", delay=0)

async def fav2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("권한이 없습니다.")
        return
    await query_buses(update, "P", "L", delay=0)

async def fav3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("권한이 없습니다.")
        return
    await query_buses(update, "L", "P", delay=30)

async def fav4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("권한이 없습니다.")
        return
    await query_buses(update, "P", "L", delay=30)

async def all_buses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("권한이 없습니다.")
        return
    now = datetime.now(KST)
    now_min = now.hour * 60 + now.minute
    is_weekend = now.weekday() >= 5
    sched_name = "주말" if is_weekend else "평일"
    trips = WEEKEND_TRIPS if is_weekend else WEEKDAY_TRIPS
    routes = [("J","P"), ("P","J"), ("J","L"), ("L","J"), ("L","P"), ("P","L")]
    msg = "오늘 남은 버스 (" + sched_name + ")\n---\n"
    for frm, to in routes:
        buses = find_next_buses(frm, to, trips, now_min, count=3)
        if buses:
            msg += frm + "->" + to + ": " + ", ".join([fmt(dep) for dep, arr in buses]) + "\n"
    await update.message.reply_text(msg)

async def last_bus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("권한이 없습니다.")
        return
    now = datetime.now(KST)
    now_min = now.hour * 60 + now.minute
    is_weekend = now.weekday() >= 5
    sched_name = "주말" if is_weekend else "평일"
    trips = WEEKEND_TRIPS if is_weekend else WEEKDAY_TRIPS
    routes = [("J","P"), ("P","J"), ("J","L"), ("L","J"), ("L","P"), ("P","L")]
