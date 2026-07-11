import os
from datetime import datetime
import pytz
from fastapi import FastAPI, Request

app = FastAPI()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USERS = [8058101860, 5209319564]
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


def current_trips():
    now = datetime.now(KST)
    now_min = now.hour * 60 + now.minute
    is_weekend = now.weekday() >= 5
    sched_name = "주말" if is_weekend else "평일"
    trips = WEEKEND_TRIPS if is_weekend else WEEKDAY_TRIPS
    return now_min, sched_name, trips


def route_msg(frm, to, trips, now_min, delay, sched_name):
    buses = find_next_buses(frm, to, trips, now_min, delay, 3)
    if not buses:
        return f"오늘 {frm}->{to} 버스는 더 없습니다."
    delay_tag = " [지연+30분]" if delay else ""
    msg = f"버스 {frm}->{to}{delay_tag} ({sched_name})\n---\n"
    for i, (dep, arr) in enumerate(buses):
        wait = dep - now_min
        duration = arr - dep
        if i == 0:
            msg += f"다음: {fmt(dep)}->{fmt(arr)} ({wait}분후, {duration}분소요)\n"
        else:
            msg += f"{i+1}번째: {fmt(dep)}->{fmt(arr)}\n"
    return msg


def handle_text(text: str) -> str:
    text = text.strip().lower()

    if text == "/start":
        return ("버스 시간표 봇\n\n즐겨찾기:\n/1 L->P\n/2 P->L\n/3 L->P 지연\n/4 P->L 지연\n\n"
                 "직접입력: j-p, l-p 등\n지연: g l-p\n\n/all 전체보기\n/last 막차확인")

    now_min, sched_name, trips = current_trips()

    if text == "/1":
        return route_msg("L", "P", trips, now_min, 0, sched_name)
    if text == "/2":
        return route_msg("P", "L", trips, now_min, 0, sched_name)
    if text == "/3":
        return route_msg("L", "P", trips, now_min, 30, sched_name)
    if text == "/4":
        return route_msg("P", "L", trips, now_min, 30, sched_name)

    if text == "/all":
        routes = [("J", "P"), ("P", "J"), ("J", "L"), ("L", "J"), ("L", "P"), ("P", "L")]
        msg = f"오늘 남은 버스 ({sched_name})\n---\n"
        for frm, to in routes:
            buses = find_next_buses(frm, to, trips, now_min, 0, 3)
            if buses:
                msg += f"{frm}->{to}: " + ", ".join(fmt(dep) for dep, arr in buses) + "\n"
        return msg

    if text == "/last":
        routes = [("J", "P"), ("P", "J"), ("J", "L"), ("L", "J"), ("L", "P"), ("P", "L")]
        msg = f"막차 시간 ({sched_name})\n---\n"
        for frm, to in routes:
            last = find_last_bus(frm, to, trips)
            if last:
                dep, arr = last
                wait = dep - now_min
                if wait > 0:
                    msg += f"{frm}->{to}: {fmt(dep)} ({wait}분후)\n"
                else:
                    msg += f"{frm}->{to}: 막차지남\n"
        return msg

    delay = 0
    if text.startswith("g "):
        delay = 30
        text = text.lstrip("g").strip()
    elif text.startswith("g"):
        delay = 30
        text = text.lstrip("g").strip()

    valid = ["j", "l", "p"]
    parts = text.split("-")
    if len(parts) != 2 or parts[0] not in valid or parts[1] not in valid or parts[0] == parts[1]:
        return "예: j-p / p-j / g l-p\n/start 로 목록 확인"

    frm, to = parts[0].upper(), parts[1].upper()
    return route_msg(frm, to, trips, now_min, delay, sched_name)


@app.get("/")
async def health():
    return {"status": "ok"}


@app.post("/")
async def telegram_webhook(request: Request):
    body = await request.json()
    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}

    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if user_id not in ALLOWED_USERS:
        reply = "권한이 없습니다."
    else:
        reply = handle_text(text)

    return {"method": "sendMessage", "chat_id": chat_id, "text": reply}
