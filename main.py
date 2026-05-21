import logging
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

========== 여기만 수정 ==========
BOT_TOKEN = “8989509783: AAF×BCvBIkN1b8PPSDNW8
U-3HV_KRBhlA3M”
ALLOWED_USERS = [8058101860]

=================================
KST = pytz.timezone(‘Asia/Seoul’)

def t(h, m):
return h * 60 + m

def fmt(minutes):
return f”{minutes // 60:02d}:{minutes % 60:02d}”

========== 주말 시간표 ==========
def build_weekend_trips():
trips = []

역방향 L → J (매 시 :33, :36)
for h in range(8, 17):
trips.append([(“L”, t(h, 33)), (“J”, t(h, 36))])

단방향 J → L → P (매 시 :47, :50, :57)
for h in range(8, 17):
trips.append([(“J”, t(h, 47)), (“L”, t(h, 50)), (“P”, t(h, 57))])

역방향 P → L → J (매 시+1 :08, :11, :14)
for h in range(9, 18):
trips.append([(“P”, t(h, 8)), (“L”, t(h, 11)), (“J”, t(h, 14))])
trips.sort(key=lambda trip: trip[0][1])
return trips

========== 평일 시간표 (나중에 추가) ==========
def build_weekday_trips():
trips = []

나중에 평일 데이터 여기에 입력
예시: trips.append([(“J”, t(7, 30)), (“L”, t(7, 35)), (“P”, t(7, 42))])
return trips

WEEKEND_TRIPS = build_weekend_trips()
WEEKDAY_TRIPS = build_weekday_trips()

def find_next_bus(from_stop, to_stop, trips, now_min, delay=0):
for trip in trips:
stops = [s[0] for s in trip]
if from_stop in stops and to_stop in stops:
fi = stops.index(from_stop)
ti = stops.index(to_stop)
if fi < ti:
dep = trip[fi][1] + delay
arr = trip[ti][1] + delay
if dep >= now_min:
return dep, arr
return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
if update.effective_user.id not in ALLOWED_USERS:
await update.message.reply_text(“❌ 권한이 없습니다.”)
return
msg = (
“🚌 버스 시간표 봇\n\n”
“📋 명령어 목록:\n”
“j-p → J에서 P까지\n”
“p-j → P에서 J까지\n”
“j-l → J에서 L까지\n”
“l-j → L에서 J까지\n”
“l-p → L에서 P까지\n”
“p-l → P에서 L까지\n\n”
“⚡ g를 앞에 붙이면 30분 지연 적용\n”
“예: g j-p\n\n”
“📅 주말/평일 자동 감지”
)
await update.message.reply_text(msg)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id
if user_id not in ALLOWED_USERS:
await update.message.reply_text(“❌ 권한이 없습니다.”)
return

text = update.message.text.strip().lower()
# 지연 파싱
delay = 0
if text.startswith("g ") or text.startswith("g"):
    delay = 30
    text = text.lstrip("g").strip()
# 현재 시각 및 요일
now = datetime.now(KST)
now_min = now.hour * 60 + now.minute
is_weekend = now.weekday() >= 5
sched_name = "주말" if is_weekend else "평일"
trips = WEEKEND_TRIPS if is_weekend else WEEKDAY_TRIPS
if not trips:
    await update.message.reply_text(f"⚠️ {sched_name} 시간표가 아직 없습니다.\n/start 로 사용법 확인")
    return
# 명령어 파싱
valid = ["j", "l", "p"]
parts = text.split("-")
if len(parts) != 2 or parts[0] not in valid or parts[1] not in valid or parts[0] == parts[1]:
    await update.message.reply_text("❓ 예: j-p / p-j / g l-p\n/start 로 전체 목록 확인")
    return
frm = parts[0].upper()
to = parts[1].upper()
dep, arr = find_next_bus(frm, to, trips, now_min, delay)
if dep is None:
    await update.message.reply_text(f"🚫 오늘 {frm} → {to} 버스는 더 없습니다.")
    return
wait = dep - now_min
duration = arr - dep
delay_tag = "  ⚡지연 +30분" if delay else ""
msg = (
    f"🚌  {frm} → {to}{delay_tag}\n"
    f"📅  {sched_name} 시간표\n"
    f"─────────────\n"
    f"🕐  출발: {fmt(dep)}  ({frm})\n"
    f"🏁  도착: {fmt(arr)}  ({to})\n"
    f"⌛  소요: {duration}분\n"
    f"─────────────\n"
    f"⏰  지금 {now.strftime('%H:%M')} → {wait}분 후 출발"
)
await update.message.reply_text(msg)
if name == “main”:
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
print(“🚌 봇 시작!”)
app.run_polling()
