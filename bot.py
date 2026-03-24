import asyncio
import aiohttp
import json
import os
import struct
import random
import ssl
import re
import sys
import traceback
import base64
import urllib.parse
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== VERCEL PATH & IMPORT PROTECTOR ====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)
    sys.path.append(os.getcwd())

import MajoRLoGinrEq_pb2
import MajoRLoGinrEs_pb2
import PlayerPersonalShow_pb2

# ==================== BOT CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = "8352132120:AAFGtA_ChS-diB3NNYXeDUsRCqP7QFHmvCc"

SHRINK_API = "860321374ebd153019407a635e12a63b56feadce"
ALLOWED_GROUP_IDS = [-1003550876057, -1003258005381]
REDIRECT_LINK = "https://t.me/SulavXMRCLIKES"
OWNERS = "@MRCxCheats and @sulav_codex_ff"

# Super admins — these IDs are always admins and can never be removed
SUPER_ADMINS = {8399116292, 5938491424}

# ==================== ADMIN / MAINTENANCE / WARNING SYSTEM ====================
DATA_FILE = "bot_data.json"
WARNING_THRESHOLD = 3
FAST_COMPLETION_SEC = 5
TOKEN_EXPIRE_SEC = 600

# Auto scheduler settings
AUTO_INTERVAL_HOURS = 0
LIKES_PER_DAY = 100000

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault("admins", [])
            data.setdefault("banned", [])
            data.setdefault("warnings", {})
            data.setdefault("maintenance", False)
            data.setdefault("tokens", {})
            data.setdefault("auto_tasks", [])
            data.setdefault("likes_per_day", LIKES_PER_DAY)
            data.setdefault("total_likes_sent", 0)
            data.setdefault("total_visits_sent", 0)
            data.setdefault("total_spam_sent", 0)
            return data
    return {
        "admins": [],
        "banned": [],
        "warnings": {},
        "maintenance": False,
        "tokens": {},
        "auto_tasks": [],
        "likes_per_day": LIKES_PER_DAY,
        "total_likes_sent": 0,
        "total_visits_sent": 0,
        "total_spam_sent": 0,
    }

def save_data(d):
    with open(DATA_FILE, 'w') as f:
        json.dump(d, f, indent=2)

data = load_data()
admins = set(data.get("admins", [])) | SUPER_ADMINS
banned = set(data.get("banned", []))
warnings = data.get("warnings", {})
maintenance_mode = data.get("maintenance", False)
tokens = data.get("tokens", {})
auto_tasks = data.get("auto_tasks", [])
likes_per_day_setting = data.get("likes_per_day", LIKES_PER_DAY)
total_likes_sent = data.get("total_likes_sent", 0)
total_visits_sent = data.get("total_visits_sent", 0)
total_spam_sent = data.get("total_spam_sent", 0)

def save_all():
    data["admins"] = list(admins - SUPER_ADMINS)
    data["banned"] = list(banned)
    data["warnings"] = warnings
    data["maintenance"] = maintenance_mode
    data["tokens"] = tokens
    data["auto_tasks"] = auto_tasks
    data["likes_per_day"] = likes_per_day_setting
    data["total_likes_sent"] = total_likes_sent
    data["total_visits_sent"] = total_visits_sent
    data["total_spam_sent"] = total_spam_sent
    save_data(data)

def is_admin(user_id):
    return user_id in admins or user_id in SUPER_ADMINS

def is_super_admin(user_id):
    return user_id in SUPER_ADMINS

def is_banned(user_id):
    return user_id in banned

def add_warning(user_id):
    count = warnings.get(str(user_id), 0) + 1
    warnings[str(user_id)] = count
    save_all()
    return count

def clear_warnings(user_id):
    warnings.pop(str(user_id), None)
    save_all()

def ban_user(user_id, reason=None):
    if user_id in SUPER_ADMINS:
        return False
    banned.add(user_id)
    admins.discard(user_id)
    save_all()
    return True

def unban_user(user_id):
    banned.discard(user_id)
    clear_warnings(user_id)
    save_all()

async def kick_from_all_groups(bot_instance, user_id):
    for group_id in ALLOWED_GROUP_IDS:
        try:
            await bot_instance.ban_chat_member(group_id, user_id)
            await bot_instance.unban_chat_member(group_id, user_id)
        except Exception as e:
            print(f"Could not kick from {group_id}: {e}")

def create_auto_task(command_type, uid, region, days, added_by=None):
    return {
        "id": secrets.token_urlsafe(8),
        "type": command_type,
        "uid": uid,
        "region": region,
        "start_date": datetime.now().isoformat(),
        "end_date": (datetime.now() + timedelta(days=int(days))).isoformat(),
        "days": int(days),
        "likes_per_day": likes_per_day_setting,
        "last_sent_date": None,
        "added_by": added_by,
    }

# ==================== LIKE ENGINE CONFIGURATION ====================
STATIC_KEY = b'Yg&tc%DEuh6%Zc^8'
STATIC_IV = b'6oyZDr22E3ychjM%'

BASE_DIR = os.getcwd()

def get_acc_path(filename):
    paths_to_check = [
        os.path.join(BASE_DIR, "like-accs", filename),
        os.path.join(BASE_DIR, "like-api", "like-accs", filename),
        os.path.join(CURRENT_DIR, "like-accs", filename),
        os.path.join("/var/task", "like-accs", filename),
        os.path.join("/var/task", "like-api", "like-accs", filename)
    ]
    for p in paths_to_check:
        if os.path.exists(p):
            return p
    return paths_to_check[0]

REGION_CONFIGS = {
    "BD": {"major": "loginbp.ggblueshark.com", "client": "clientbp.ggblueshark.com", "opcode": b"\x05\x19", "file": "accs_bd.json"},
    "SG": {"major": "loginbp.ggpolarbear.com", "client": "clientbp.ggpolarbear.com", "opcode": b"\x05\x15", "file": "accs_sg.json"},
    "EU": {"major": "loginbp.ggpolarbear.com", "client": "clientbp.ggpolarbear.com", "opcode": b"\x05\x15", "file": "accs_sg.json"},
    "IND": {"major": "login.ind.freefiremobile.com", "client": "client.ind.freefiremobile.com", "opcode": b"\x05\x14", "file": "accs_ind.json"}
}

# ==================== CRYPTO & ENCODING ====================
def encrypt_aes(data_bytes):
    if isinstance(data_bytes, bytearray): data_bytes = bytes(data_bytes)
    cipher = AES.new(STATIC_KEY, AES.MODE_CBC, STATIC_IV)
    return cipher.encrypt(pad(data_bytes, 16))

def write_varint(val):
    pkt = bytearray()
    val = int(val or 0)
    while val >= 0x80:
        pkt.append((val & 0x7F) | 0x80); val >>= 7
    pkt.append(val & 0x7F)
    return pkt

async def create_minimal_proto(fields):
    pkt = bytearray()
    for fn, fv in fields.items():
        fn = int(fn)
        if isinstance(fv, int):
            pkt.extend(write_varint((fn << 3) | 0))
            pkt.extend(write_varint(fv))
        elif isinstance(fv, str):
            b = fv.encode()
            pkt.extend(write_varint((fn << 3) | 2))
            pkt.extend(write_varint(len(b)))
            pkt.extend(b)
        elif isinstance(fv, dict):
            nested = await create_minimal_proto(fv)
            pkt.extend(write_varint((fn << 3) | 2))
            pkt.extend(write_varint(len(nested)))
            pkt.extend(nested)
    return pkt

def get_headers(host, auth_token=None, content_len=None):
    hdrs = {
        "Host": host,
        "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Authorization": f"Bearer {auth_token}" if auth_token else "Bearer",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB52",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2022.3.47f1"
    }
    if content_len: hdrs["Content-Length"] = str(content_len)
    return hdrs

# ==================== THE HEARTBEAT MOTOR ====================
async def tcp_ping_loop(writer, stop_event, opcode):
    try:
        while not stop_event.is_set():
            fields = {"1": 99, "2": {"1": int(datetime.now().timestamp()), "2": 1}}
            proto = await create_minimal_proto(fields)
            enc = encrypt_aes(bytes(proto))
            writer.write(opcode + struct.pack(">I", len(enc)) + enc)
            await writer.drain()
            await asyncio.sleep(8)
    except:
        pass

async def login_and_tcp_auth(uid, token, key, iv, ts, ip_port, opcode):
    try:
        if not ip_port: return None, None
        ip, port = ip_port.split(":")
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, int(port)), timeout=2.0)
        k, v = bytes.fromhex(key), bytes.fromhex(iv)
        cipher = AES.new(k, AES.MODE_CBC, v)
        enc_token = cipher.encrypt(pad(str(token).encode(), 16))
        auth_p = struct.pack(">Q", int(uid)) + struct.pack(">I", int(ts)) + struct.pack(">I", len(enc_token)) + enc_token
        writer.write(b"\x01\x15" + struct.pack(">I", len(auth_p)) + auth_p)
        await writer.drain()
        stop_event = asyncio.Event()
        asyncio.create_task(tcp_ping_loop(writer, stop_event, opcode))
        return writer, stop_event
    except:
        return None, None

# ==================== BOT WORKER POWERHOUSE ====================
async def bot_worker(acc, session, target_uid, region_key, conf, semaphore, only_login=False):
    async with semaphore:
        writer, stop_evt = None, None
        try:
            uid_bot, pw_bot = str(acc["uid"]), str(acc.get("password", acc.get("pass", "")))

            async with session.post("https://100067.connect.garena.com/oauth/guest/token/grant",
                                    data={"uid": uid_bot, "password": pw_bot, "response_type": "token", "client_id": "100067", "client_type": "2", "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"}) as r:
                if r.status != 200: return {"success": False, "error": f"Garena HTTP {r.status}"}
                js = await r.json(); oid, gat = js.get("open_id"), js.get("access_token")

            ml = MajoRLoGinrEq_pb2.MajorLogin()
            ml.event_time = str(datetime.now())[:-7]
            ml.game_name = "free fire"
            ml.platform_id = 1
            ml.client_version = "1.120.1"
            ml.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
            ml.system_hardware = "Handheld"
            ml.telecom_operator = "Verizon"
            ml.network_type = "WIFI"
            ml.screen_width = 1920
            ml.screen_height = 1080
            ml.screen_dpi = "280"
            ml.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
            ml.memory = 3003
            ml.gpu_renderer = "Adreno (TM) 640"
            ml.gpu_version = "OpenGL ES 3.1 v1.46"
            ml.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
            ml.client_ip = "223.191.51.89"
            ml.language = "en"
            ml.open_id = str(oid)
            ml.open_id_type = "4"
            ml.device_type = "Handheld"
            ml.memory_available.version = 55
            ml.memory_available.hidden_value = 81
            ml.access_token = str(gat)
            ml.platform_sdk_id = 1
            ml.network_operator_a = "Verizon"
            ml.network_type_a = "WIFI"
            ml.client_using_version = "7428b253defc164018c604a1ebbfebdf"
            ml.external_storage_total = 36235
            ml.external_storage_available = 31335
            ml.internal_storage_total = 2519
            ml.internal_storage_available = 703
            ml.game_disk_storage_available = 25010
            ml.game_disk_storage_total = 26628
            ml.external_sdcard_avail_storage = 32992
            ml.external_sdcard_total_storage = 36235
            ml.login_by = 3
            ml.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
            ml.reg_avatar = 1
            ml.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
            ml.channel_type = 3
            ml.cpu_type = 2
            ml.cpu_architecture = "64"
            ml.client_version_code = "2019118695"
            ml.graphics_api = "OpenGLES2"
            ml.supported_astc_bitset = 16383
            ml.login_open_id_type = 4
            ml.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg=="
            ml.loading_time = 13564
            ml.release_channel = "android"
            ml.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
            ml.android_engine_init_flag = 110009
            ml.if_push = 1
            ml.is_vpn = 1
            ml.origin_platform_type = "4"
            ml.primary_platform_type = "4"

            payload = encrypt_aes(ml.SerializeToString())
            async with session.post(f"https://{conf['major']}/MajorLogin", data=payload, headers=get_headers(conf['major'])) as r:
                if r.status != 200: return {"success": False, "error": f"MajorLogin HTTP {r.status}"}
                ml_res = MajoRLoGinrEs_pb2.MajorLoginRes()
                ml_res.ParseFromString(await r.read())
                jwt = ml_res.token

            if only_login: return {"token": jwt, "success": True, "uid": ml_res.account_uid}

            async with session.post(f"{ml_res.url}/GetLoginData", data=payload, headers=get_headers(conf['client'], jwt)) as r:
                raw = (await r.read()).decode(errors='ignore')
                ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+', raw)
                lobby_ip = ips[0] if ips else None

            writer, stop_evt = await login_and_tcp_auth(ml_res.account_uid, jwt, ml_res.key, ml_res.iv, ml_res.timestamp, lobby_ip, conf['opcode'])

            like_proto = await create_minimal_proto({"1": int(target_uid), "2": region_key})
            enc_l = encrypt_aes(bytes(like_proto))
            async with session.post(f"https://{conf['client']}/LikeProfile", data=enc_l, headers=get_headers(conf['client'], jwt, len(enc_l))) as r:
                pass

            if stop_evt: stop_evt.set()
            if writer:
                writer.close()
                try: await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                except: pass
            return {"success": True}
        except Exception as e:
            if stop_evt: stop_evt.set()
            if writer: writer.close()
            return {"success": False, "error": str(e)}

async def run_global_like_engine(target_uid, region_key):
    global total_likes_sent
    conf = REGION_CONFIGS.get(region_key, REGION_CONFIGS["BD"])
    acc_p = get_acc_path(conf["file"])
    if not os.path.exists(acc_p): raise Exception(f"Account list missing: {acc_p}")

    with open(acc_p, "r") as f: accounts = json.load(f)

    ssl_ctx = ssl.create_default_context(); ssl_ctx.check_hostname = False; ssl_ctx.verify_mode = ssl.CERT_NONE
    semaphore = asyncio.Semaphore(4)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx)) as session:
        pre = await bot_worker(accounts[0], session, target_uid, region_key, conf, semaphore, only_login=True)
        jwt = pre.get("token")
        if not jwt: raise Exception(f"Bot 0 Core Failure: {pre.get('error')}")

        await asyncio.sleep(0.4)
        info_proto = await create_minimal_proto({"1": int(target_uid), "2": 7, "4": 1})
        info_enc = encrypt_aes(bytes(info_proto))
        name, lb = "Unknown", 0
        async with session.post(f"https://{conf['client']}/GetPlayerPersonalShow", data=info_enc, headers=get_headers(conf['client'], jwt)) as r:
            if r.status == 200:
                show = PlayerPersonalShow_pb2.response(); show.ParseFromString(await r.read())
                name, lb = show.basicinfo.nickname, show.basicinfo.liked

        tasks = [bot_worker(acc, session, target_uid, region_key, conf, semaphore) for acc in accounts]
        await asyncio.gather(*tasks, return_exceptions=True)

        await asyncio.sleep(0.4)
        la = 0
        async with session.post(f"https://{conf['client']}/GetPlayerPersonalShow", data=info_enc, headers=get_headers(conf['client'], jwt)) as r:
            if r.status == 200:
                show = PlayerPersonalShow_pb2.response(); show.ParseFromString(await r.read()); la = show.basicinfo.liked

    added = int(la) - int(lb)
    total_likes_sent += max(added, 0)
    save_all()
    return {
        "name": name, "uid": str(target_uid), "LikesBefore": str(lb), "LikeAfter": str(la),
        "LikesAddedByMrcSulav": str(added), "status": "success"
    }

INFO_API_URL = "https://free-fire-api--tsandesh756.replit.app/get_player_personal_show"

# Region code mapping for the info API
INFO_API_REGION_MAP = {
    "BD": None,   # Not supported by this API
    "SG": "SG",
    "IND": "IND",
    "EU": "SG",
}

async def get_player_info_api(target_uid, region_key):
    """Fetch player info using the external REST API."""
    api_region = INFO_API_REGION_MAP.get(region_key)
    if api_region is None:
        raise Exception(f"Region <b>{region_key}</b> is not supported by the info API.\nSupported: <code>SG, IND</code>")
    async with aiohttp.ClientSession() as session:
        url = f"{INFO_API_URL}?server={api_region}&uid={target_uid}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json()
    if data.get("status") == "error" or "error" in data:
        raise Exception(data.get("message") or data.get("error") or "Unknown API error")
    return data

# ==================== AUTO SCHEDULER ====================
async def auto_scheduler():
    global total_likes_sent, total_visits_sent, total_spam_sent
    while True:
        try:
            now = datetime.now()
            today = now.date()
            tasks_to_remove = []
            for task in list(auto_tasks):
                end_date = datetime.fromisoformat(task["end_date"]).date()
                if end_date < today:
                    tasks_to_remove.append(task)
                    continue
                last_sent = task.get("last_sent_date")
                if last_sent:
                    last_date = datetime.fromisoformat(last_sent).date()
                    if last_date == today:
                        continue
                try:
                    if task["type"] == "like":
                        await run_global_like_engine(task["uid"], task["region"])
                    elif task["type"] == "visit":
                        async with aiohttp.ClientSession() as sess:
                            api_url = f"https://mrc-visit-api.vercel.app/api/visit_player?target_id={task['uid']}&region={task['region'].lower()}"
                            await sess.get(api_url)
                        total_visits_sent += 1
                    elif task["type"] == "spam":
                        async with aiohttp.ClientSession() as sess:
                            api_url = f"https://mrc-spam-api.vercel.app/api/spam_friend?target_id={task['uid']}&region={task['region'].lower()}"
                            await sess.get(api_url)
                        total_spam_sent += 1
                except Exception as e:
                    print(f"Auto task error ({task['id']}): {e}")
                task["last_sent_date"] = now.isoformat()
                save_all()
            for task in tasks_to_remove:
                if task in auto_tasks:
                    auto_tasks.remove(task)
            if tasks_to_remove:
                save_all()
        except Exception as e:
            print(f"Scheduler error: {e}")
        await asyncio.sleep(AUTO_INTERVAL_HOURS * 3600)

# ==================== TELEGRAM BOT ====================
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

async def check_group(message: types.Message) -> bool:
    if message.chat.type == "private":
        if message.text and message.text.startswith("/start "):
            return True
        await message.answer(
            f"❌ <b>Access Denied!</b>\n\nThis bot only works in our official groups.\n"
            f"👉 <b>Join Here:</b> {REDIRECT_LINK}",
            parse_mode=ParseMode.HTML
        )
        return False
    if message.chat.id not in ALLOWED_GROUP_IDS:
        await message.answer(
            f"❌ <b>Restricted Group!</b>\n\nJoin our official groups to use this bot.\n"
            f"👉 {REDIRECT_LINK}",
            parse_mode=ParseMode.HTML
        )
        return False
    return True

async def get_short_link(long_url):
    try:
        encoded_url = urllib.parse.quote(long_url, safe='')
        api_url = f"https://shrinkearn.com/api?api={SHRINK_API}&url={encoded_url}&format=text"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                text = await resp.text()
                if "http" in text:
                    return text.strip()
    except Exception as e:
        print(f"ShrinkEarn Error: {e}")
    return None

# ==================== DECORATORS ====================
def admin_required(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            await message.reply("❌ <b>Admin only command.</b>", parse_mode=ParseMode.HTML)
            return
        return await func(message, *args, **kwargs)
    return wrapper

def super_admin_required(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if not is_super_admin(message.from_user.id):
            await message.reply("❌ <b>Super admin only command.</b>", parse_mode=ParseMode.HTML)
            return
        return await func(message, *args, **kwargs)
    return wrapper

# ==================== GENERAL COMMANDS ====================
@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    if message.chat.type != "private":
        if not await check_group(message): return
        badge = "👑 ADMIN" if is_admin(message.from_user.id) else "👤 USER"
        await message.reply(
            f"🔥 <b>MRC x SULAV FF BOT</b> 🔥\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Status: <b>{badge}</b>\n\n"
            f"<b>📋 Commands:</b>\n"
            f"• /like &lt;region&gt; &lt;uid&gt;\n"
            f"• /visits &lt;region&gt; &lt;uid&gt;\n"
            f"• /spam &lt;region&gt; &lt;uid&gt;\n"
            f"• /info &lt;region&gt; &lt;uid&gt;\n"
            f"• /help — full command list\n\n"
            f"🌍 Regions: <code>BD</code> | <code>SG</code> | <code>IND</code>\n"
            f"👑 Owners: {OWNERS}\n"
            f"📢 Channel: {REDIRECT_LINK}",
            parse_mode=ParseMode.HTML
        )
        return

    # Private chat — token verification flow
    if not command.args:
        return await message.answer(
            f"❌ <b>Access Denied!</b>\n\nThis bot works inside official groups only.\n"
            f"👉 Join: {REDIRECT_LINK}",
            parse_mode=ParseMode.HTML
        )

    token = command.args.strip()
    token_data = tokens.get(token)
    if not token_data:
        return await message.answer("❌ <b>Invalid or expired verification link!</b>", parse_mode=ParseMode.HTML)

    user_id = token_data["user_id"]
    if user_id != message.from_user.id:
        return await message.answer("❌ <b>This link is not for you!</b>", parse_mode=ParseMode.HTML)

    if is_banned(user_id):
        tokens.pop(token, None); save_all()
        return await message.answer("🚫 You are banned from this bot.", parse_mode=ParseMode.HTML)

    if maintenance_mode and not is_admin(user_id):
        tokens.pop(token, None); save_all()
        return await message.answer("🔧 Bot is under maintenance. Try later.", parse_mode=ParseMode.HTML)

    now_ts = time.time()
    elapsed = now_ts - token_data["timestamp"]
    if elapsed < FAST_COMPLETION_SEC:
        count = add_warning(user_id)
        await message.answer(
            f"⚠️ <b>Warning {count}/{WARNING_THRESHOLD}</b>\nVerification too fast! Possible bypass attempt.",
            parse_mode=ParseMode.HTML
        )
        if count >= WARNING_THRESHOLD:
            ban_user(user_id, "Repeated fast bypass.")
            tokens.pop(token, None); save_all()
            await message.answer("🚫 Banned for repeated fast completions.")
            await kick_from_all_groups(bot, user_id)
            return

    tokens.pop(token, None); save_all()

    cmd = token_data["command"]
    region = token_data["region"]
    uid = token_data["uid"]

    proc_msg = await message.answer(
        f"✅ <b>Verified!</b>\n\n"
        f"⏳ Processing <b>{cmd.upper()}</b> for UID <code>{uid}</code> [{region}]...",
        parse_mode=ParseMode.HTML
    )
    await _execute_command(proc_msg, cmd, region, uid)

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    if not await check_group(message): return
    user_id = message.from_user.id
    admin_section = ""
    if is_admin(user_id):
        admin_section = (
            "\n\n<b>🔧 Admin Commands:</b>\n"
            "• /autolike &lt;region&gt; &lt;uid&gt; &lt;days&gt;\n"
            "• /autovisit &lt;region&gt; &lt;uid&gt; &lt;days&gt;\n"
            "• /autospam &lt;region&gt; &lt;uid&gt; &lt;days&gt;\n"
            "• /autolist — list active tasks\n"
            "• /autocancel &lt;task_id&gt; — cancel a task\n"
            "• /autostatus — detailed auto task stats\n"
            "• /add_admin &lt;id&gt; | /remove_admin &lt;id&gt;\n"
            "• /ban &lt;id&gt; [reason] | /unban &lt;id&gt;\n"
            "• /warn &lt;id&gt; [reason] | /clear_warnings &lt;id&gt;\n"
            "• /maintenance on|off\n"
            "• /setlimit &lt;n&gt; — set daily likes/visits\n"
            "• /broadcast &lt;message&gt;\n"
            "• /stats — full bot statistics\n"
            "• /admin — admin control panel\n"
        )
    await message.reply(
        f"🔥 <b>MRC x SULAV FF BOT — Commands</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>🎮 User Commands:</b>\n"
        f"• /like &lt;region&gt; &lt;uid&gt; — Send likes\n"
        f"• /visits &lt;region&gt; &lt;uid&gt; — Send visits\n"
        f"• /spam &lt;region&gt; &lt;uid&gt; — Send friend requests\n"
        f"• /info &lt;region&gt; &lt;uid&gt; — View player info\n"
        f"• /ping — Check bot status\n"
        f"• /help — Show this message\n\n"
        f"🌍 <b>Regions:</b> <code>BD</code> | <code>SG</code> | <code>IND</code>"
        f"{admin_section}\n\n"
        f"👑 Owners: {OWNERS}\n"
        f"📢 {REDIRECT_LINK}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("ping"))
async def ping_cmd(message: types.Message):
    if not await check_group(message): return
    start = time.time()
    msg = await message.reply("🏓 Pinging...")
    elapsed = round((time.time() - start) * 1000)
    active_tasks = len([t for t in auto_tasks if datetime.fromisoformat(t["end_date"]).date() >= datetime.now().date()])
    await msg.edit_text(
        f"🏓 <b>Pong!</b> <code>{elapsed}ms</code>\n\n"
        f"🤖 Bot: <b>Online</b> ✅\n"
        f"🔧 Maintenance: {'ON ⚠️' if maintenance_mode else 'OFF ✅'}\n"
        f"📋 Active auto tasks: <b>{active_tasks}</b>\n"
        f"👑 Owners: {OWNERS}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("info"))
async def info_cmd(message: types.Message, command: CommandObject):
    if not await check_group(message): return
    if is_banned(message.from_user.id):
        return await message.reply("🚫 You are banned.", parse_mode=ParseMode.HTML)
    if maintenance_mode and not is_admin(message.from_user.id):
        return await message.reply("🔧 Bot under maintenance.", parse_mode=ParseMode.HTML)
    if not command.args:
        return await message.reply(
            "Usage: <code>/info &lt;region&gt; &lt;uid&gt;</code>\n"
            "Supported regions: <code>SG, IND</code>",
            parse_mode=ParseMode.HTML
        )
    parts = command.args.split()
    if len(parts) != 2:
        return await message.reply("Usage: <code>/info &lt;region&gt; &lt;uid&gt;</code>", parse_mode=ParseMode.HTML)
    region, uid = parts[0].upper(), parts[1]
    if region not in REGION_CONFIGS:
        return await message.reply("⚠️ Invalid region. Use: <code>BD, SG, IND</code>", parse_mode=ParseMode.HTML)
    if not uid.isdigit():
        return await message.reply("⚠️ UID must be numeric.", parse_mode=ParseMode.HTML)

    proc = await message.reply(
        f"🔍 <i>Fetching player info for <code>{uid}</code> [{region}]...</i>",
        parse_mode=ParseMode.HTML
    )
    try:
        res = await get_player_info_api(uid, region)

        # Extract fields — handle both flat and nested JSON structures
        basic = res.get("basicInfo", res.get("basic_info", res))
        social = res.get("socialInfo", res.get("social_info", {}))
        pet    = res.get("petInfo", res.get("pet_info", {}))
        clan   = res.get("clanBasicInfo", res.get("clan_info", {}))

        name       = basic.get("nickname",    basic.get("name",        res.get("nickname",    "Unknown")))
        level      = basic.get("level",                                res.get("level",       "—"))
        liked      = basic.get("liked",       basic.get("likes",       res.get("liked",       "—")))
        br_rank    = basic.get("rank",        basic.get("br_rank",     res.get("rank",        "—")))
        cs_rank    = basic.get("csRank",      basic.get("cs_rank",     res.get("cs_rank",     "—")))
        exp        = basic.get("exp",                                  res.get("exp",         "—"))
        region_out = basic.get("region",                               res.get("region",      region))
        account_id = basic.get("accountId",   basic.get("uid",        res.get("uid",         uid)))

        # Optional extras
        bio        = social.get("signature",  social.get("bio",        ""))
        pet_name   = pet.get("name",          "")
        clan_name  = clan.get("clanName",     clan.get("name",        ""))

        lines = [
            f"📊 <b>PLAYER INFO</b>",
            f"━━━━━━━━━━━━━━━━━━━",
            f"👤 <b>Name:</b> {name}",
            f"🆔 <b>UID:</b> <code>{account_id}</code>",
            f"🌍 <b>Region:</b> {region_out}",
            f"⭐ <b>Level:</b> {level}",
            f"💎 <b>EXP:</b> {exp}",
            f"❤️ <b>Likes:</b> {liked}",
            f"🏆 <b>BR Rank:</b> {br_rank}",
            f"🎖️ <b>CS Rank:</b> {cs_rank}",
        ]
        if clan_name:
            lines.append(f"🛡️ <b>Guild:</b> {clan_name}")
        if pet_name:
            lines.append(f"🐾 <b>Pet:</b> {pet_name}")
        if bio:
            lines.append(f"📝 <b>Bio:</b> {bio}")
        lines += [
            f"",
            f"👑 {OWNERS}",
            f"📢 {REDIRECT_LINK}",
        ]
        await proc.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)

    except Exception as e:
        await proc.edit_text(
            f"❌ <b>Failed to fetch info:</b>\n{str(e)}",
            parse_mode=ParseMode.HTML
        )

# ==================== ADMIN COMMANDS ====================
@dp.message(Command("admin"))
@admin_required
async def admin_panel(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Admin", callback_data="admin_add"),
         InlineKeyboardButton(text="➖ Remove Admin", callback_data="admin_remove")],
        [InlineKeyboardButton(text="📜 List Admins", callback_data="admin_list"),
         InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔧 Maintenance", callback_data="admin_maintenance"),
         InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚠️ Warn User", callback_data="admin_warn"),
         InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban")],
        [InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban"),
         InlineKeyboardButton(text="📋 Banned List", callback_data="admin_banned")],
        [InlineKeyboardButton(text="❌ Clear Warnings", callback_data="admin_clearwarnings"),
         InlineKeyboardButton(text="🔄 Auto Tasks", callback_data="admin_auto")],
        [InlineKeyboardButton(text="⚡ Set Daily Limit", callback_data="admin_setlimit")],
    ])
    await message.reply(
        f"🔧 <b>Admin Control Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Logged in as: <code>{message.from_user.id}</code>\n"
        f"{'🌟 Super Admin' if is_super_admin(message.from_user.id) else '🔑 Admin'}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("You are not admin.", show_alert=True)
        return
    await callback.answer()
    action = callback.data[len("admin_"):]

    if action == "add":
        await callback.message.reply("📝 Send: <code>/add_admin &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    elif action == "remove":
        await callback.message.reply("📝 Send: <code>/remove_admin &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    elif action == "list":
        all_admins = admins | SUPER_ADMINS
        if all_admins:
            lines = []
            for uid in all_admins:
                tag = " 🌟" if uid in SUPER_ADMINS else ""
                lines.append(f"<code>{uid}</code>{tag}")
            await callback.message.reply(f"<b>Admins:</b>\n" + "\n".join(lines), parse_mode=ParseMode.HTML)
        else:
            await callback.message.reply("No admins configured.")
    elif action == "maintenance":
        global maintenance_mode
        maintenance_mode = not maintenance_mode
        save_all()
        await callback.message.reply(f"🔧 Maintenance: <b>{'ON ⚠️' if maintenance_mode else 'OFF ✅'}</b>", parse_mode=ParseMode.HTML)
    elif action == "broadcast":
        await callback.message.reply("📝 Send: <code>/broadcast &lt;message&gt;</code>", parse_mode=ParseMode.HTML)
    elif action == "warn":
        await callback.message.reply("📝 Send: <code>/warn &lt;user_id&gt; [reason]</code>", parse_mode=ParseMode.HTML)
    elif action == "ban":
        await callback.message.reply("📝 Send: <code>/ban &lt;user_id&gt; [reason]</code>", parse_mode=ParseMode.HTML)
    elif action == "unban":
        await callback.message.reply("📝 Send: <code>/unban &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    elif action == "banned":
        if banned:
            await callback.message.reply("<b>Banned users:</b>\n" + "\n".join([f"<code>{u}</code>" for u in banned]), parse_mode=ParseMode.HTML)
        else:
            await callback.message.reply("No banned users.")
    elif action == "clearwarnings":
        await callback.message.reply("📝 Send: <code>/clear_warnings &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    elif action == "stats":
        active_tasks = len([t for t in auto_tasks if datetime.fromisoformat(t["end_date"]).date() >= datetime.now().date()])
        await callback.message.reply(
            f"📊 <b>Bot Statistics</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Admins: <b>{len(admins | SUPER_ADMINS)}</b>\n"
            f"🚫 Banned: <b>{len(banned)}</b>\n"
            f"⚠️ Warned: <b>{len(warnings)}</b>\n"
            f"🔑 Tokens: <b>{len(tokens)}</b>\n"
            f"📋 Auto tasks: <b>{active_tasks}</b>\n"
            f"❤️ Total likes: <b>{total_likes_sent}</b>\n"
            f"👀 Total visits: <b>{total_visits_sent}</b>\n"
            f"📨 Total spam: <b>{total_spam_sent}</b>\n"
            f"⚡ Daily limit: <b>{likes_per_day_setting}</b>\n"
            f"🔧 Maintenance: {'ON ⚠️' if maintenance_mode else 'OFF ✅'}",
            parse_mode=ParseMode.HTML
        )
    elif action == "auto":
        await callback.message.reply(
            "📋 <b>Auto-task commands:</b>\n\n"
            "/autolike &lt;region&gt; &lt;uid&gt; &lt;days&gt;\n"
            "/autovisit &lt;region&gt; &lt;uid&gt; &lt;days&gt;\n"
            "/autospam &lt;region&gt; &lt;uid&gt; &lt;days&gt;\n"
            "/autolist — list tasks\n"
            "/autocancel &lt;task_id&gt; — cancel\n"
            "/autostatus — detailed status",
            parse_mode=ParseMode.HTML
        )
    elif action == "setlimit":
        await callback.message.reply("📝 Send: <code>/setlimit &lt;number&gt;</code>\nExample: <code>/setlimit 200</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("add_admin"))
@admin_required
async def add_admin_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/add_admin &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    try:
        new_admin = int(command.args.split()[0])
        admins.add(new_admin)
        save_all()
        await message.reply(f"✅ <code>{new_admin}</code> added as admin.", parse_mode=ParseMode.HTML)
    except:
        await message.reply("❌ Invalid user ID.")

@dp.message(Command("remove_admin"))
@admin_required
async def remove_admin_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/remove_admin &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    try:
        admin_id = int(command.args.split()[0])
        if admin_id in SUPER_ADMINS:
            return await message.reply("❌ Cannot remove a super admin.", parse_mode=ParseMode.HTML)
        if admin_id in admins:
            admins.discard(admin_id)
            save_all()
            await message.reply(f"✅ <code>{admin_id}</code> removed from admins.", parse_mode=ParseMode.HTML)
        else:
            await message.reply("User is not an admin.")
    except:
        await message.reply("❌ Invalid user ID.")

@dp.message(Command("list_admins"))
@admin_required
async def list_admins_cmd(message: types.Message):
    all_admins = admins | SUPER_ADMINS
    lines = []
    for uid in all_admins:
        tag = " 🌟" if uid in SUPER_ADMINS else ""
        lines.append(f"<code>{uid}</code>{tag}")
    await message.reply(f"<b>Admins ({len(all_admins)}):</b>\n" + "\n".join(lines), parse_mode=ParseMode.HTML)

@dp.message(Command("maintenance"))
@admin_required
async def maintenance_cmd(message: types.Message, command: CommandObject):
    global maintenance_mode
    arg = command.args.strip().lower() if command.args else ""
    if arg == "on":
        maintenance_mode = True
    elif arg == "off":
        maintenance_mode = False
    else:
        return await message.reply("Usage: <code>/maintenance on|off</code>", parse_mode=ParseMode.HTML)
    save_all()
    await message.reply(f"🔧 Maintenance: <b>{'ON ⚠️' if maintenance_mode else 'OFF ✅'}</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("warn"))
@admin_required
async def warn_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/warn &lt;user_id&gt; [reason]</code>", parse_mode=ParseMode.HTML)
    parts = command.args.split(maxsplit=1)
    try:
        target = int(parts[0])
    except:
        return await message.reply("❌ Invalid user ID.")
    if target in SUPER_ADMINS:
        return await message.reply("❌ Cannot warn a super admin.", parse_mode=ParseMode.HTML)
    reason = parts[1] if len(parts) > 1 else "No reason provided."
    if target in banned:
        return await message.reply("User is already banned.")
    count = add_warning(target)
    await message.reply(f"⚠️ <code>{target}</code> warned ({reason}). Warnings: <b>{count}/{WARNING_THRESHOLD}</b>", parse_mode=ParseMode.HTML)
    if count >= WARNING_THRESHOLD:
        ban_user(target, f"Exceeded {WARNING_THRESHOLD} warnings.")
        await message.reply(f"🚫 <code>{target}</code> auto-banned for exceeding warnings.", parse_mode=ParseMode.HTML)
        await kick_from_all_groups(bot, target)

@dp.message(Command("ban"))
@admin_required
async def ban_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/ban &lt;user_id&gt; [reason]</code>", parse_mode=ParseMode.HTML)
    parts = command.args.split(maxsplit=1)
    try:
        target = int(parts[0])
    except:
        return await message.reply("❌ Invalid user ID.")
    if target in SUPER_ADMINS:
        return await message.reply("❌ Cannot ban a super admin.", parse_mode=ParseMode.HTML)
    reason = parts[1] if len(parts) > 1 else "No reason provided."
    if target in banned:
        return await message.reply("User already banned.")
    if ban_user(target, reason):
        await message.reply(f"🚫 <code>{target}</code> banned.\nReason: {reason}", parse_mode=ParseMode.HTML)
        await kick_from_all_groups(bot, target)

@dp.message(Command("unban"))
@admin_required
async def unban_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/unban &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    try:
        target = int(command.args.split()[0])
    except:
        return await message.reply("❌ Invalid user ID.")
    if target not in banned:
        return await message.reply("User is not banned.")
    unban_user(target)
    await message.reply(f"✅ <code>{target}</code> unbanned.", parse_mode=ParseMode.HTML)

@dp.message(Command("list_banned"))
@admin_required
async def list_banned_cmd(message: types.Message):
    if banned:
        await message.reply("<b>Banned users:</b>\n" + "\n".join([f"<code>{u}</code>" for u in banned]), parse_mode=ParseMode.HTML)
    else:
        await message.reply("No banned users.")

@dp.message(Command("clear_warnings"))
@admin_required
async def clear_warnings_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/clear_warnings &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
    try:
        target = int(command.args.split()[0])
    except:
        return await message.reply("❌ Invalid user ID.")
    clear_warnings(target)
    await message.reply(f"✅ Warnings cleared for <code>{target}</code>.", parse_mode=ParseMode.HTML)

@dp.message(Command("stats"))
@admin_required
async def stats_cmd(message: types.Message):
    active_tasks = len([t for t in auto_tasks if datetime.fromisoformat(t["end_date"]).date() >= datetime.now().date()])
    await message.reply(
        f"📊 <b>Bot Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Admins: <b>{len(admins | SUPER_ADMINS)}</b>\n"
        f"🚫 Banned: <b>{len(banned)}</b>\n"
        f"⚠️ Warned: <b>{len(warnings)}</b>\n"
        f"🔑 Active tokens: <b>{len(tokens)}</b>\n"
        f"📋 Auto tasks: <b>{active_tasks}</b>\n"
        f"❤️ Total likes sent: <b>{total_likes_sent}</b>\n"
        f"👀 Total visits sent: <b>{total_visits_sent}</b>\n"
        f"📨 Total spam sent: <b>{total_spam_sent}</b>\n"
        f"⚡ Daily limit: <b>{likes_per_day_setting}</b>\n"
        f"🔧 Maintenance: {'ON ⚠️' if maintenance_mode else 'OFF ✅'}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("setlimit"))
@admin_required
async def setlimit_cmd(message: types.Message, command: CommandObject):
    global likes_per_day_setting
    if not command.args:
        return await message.reply(
            f"Usage: <code>/setlimit &lt;number&gt;</code>\nCurrent limit: <b>{likes_per_day_setting}</b>/day",
            parse_mode=ParseMode.HTML
        )
    try:
        n = int(command.args.strip())
        if n <= 0 or n > 10000:
            return await message.reply("❌ Limit must be between 1 and 10000.")
        likes_per_day_setting = n
        save_all()
        await message.reply(f"✅ Daily limit set to <b>{n}</b> likes/visits per auto task.", parse_mode=ParseMode.HTML)
    except:
        await message.reply("❌ Invalid number.")

@dp.message(Command("broadcast"))
@admin_required
async def broadcast_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/broadcast &lt;message&gt;</code>", parse_mode=ParseMode.HTML)
    text = command.args.strip()
    sent, failed = 0, 0
    broadcast_text = (
        f"📢 <b>BROADCAST FROM ADMIN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{text}\n\n"
        f"👑 {OWNERS}"
    )
    for group_id in ALLOWED_GROUP_IDS:
        try:
            await bot.send_message(group_id, broadcast_text, parse_mode=ParseMode.HTML)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"Broadcast failed for {group_id}: {e}")
    await message.reply(f"📢 Broadcast sent to <b>{sent}</b> group(s). Failed: <b>{failed}</b>.", parse_mode=ParseMode.HTML)

# ==================== AUTO TASK COMMANDS ====================
@dp.message(Command("autolike"))
@admin_required
async def auto_like_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply(
            "Usage: <code>/autolike &lt;region&gt; &lt;uid&gt; &lt;days&gt;</code>\n"
            "Example: <code>/autolike BD 3074306062 30</code>",
            parse_mode=ParseMode.HTML
        )
    parts = command.args.split()
    if len(parts) != 3:
        return await message.reply("❌ Invalid format. Use: <code>/autolike BD 3074306062 30</code>", parse_mode=ParseMode.HTML)
    region, uid, days = parts[0].upper(), parts[1], parts[2]
    if region not in REGION_CONFIGS:
        return await message.reply("❌ Invalid region. Choose: <code>SG, BD, IND</code>", parse_mode=ParseMode.HTML)
    if not uid.isdigit():
        return await message.reply("❌ UID must be numeric.", parse_mode=ParseMode.HTML)
    if not days.isdigit() or int(days) <= 0:
        return await message.reply("❌ Days must be a positive number.", parse_mode=ParseMode.HTML)
    task = create_auto_task("like", uid, region, days, added_by=message.from_user.id)
    auto_tasks.append(task); save_all()
    expiry = datetime.fromisoformat(task["end_date"]).strftime("%Y-%m-%d")
    await message.reply(
        f"✅ <b>Auto Like Activated!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 UID: <code>{uid}</code>\n"
        f"🌍 Region: <b>{region}</b>\n"
        f"📅 Expiry: <b>{expiry}</b>\n"
        f"⚡ Likes/Day: <b>{likes_per_day_setting}</b>\n"
        f"🔑 Task ID: <code>{task['id']}</code>\n\n"
        f"👑 {OWNERS}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("autovisit"))
@admin_required
async def auto_visit_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply(
            "Usage: <code>/autovisit &lt;region&gt; &lt;uid&gt; &lt;days&gt;</code>",
            parse_mode=ParseMode.HTML
        )
    parts = command.args.split()
    if len(parts) != 3:
        return await message.reply("❌ Invalid format. Use: <code>/autovisit BD 3074306062 30</code>", parse_mode=ParseMode.HTML)
    region, uid, days = parts[0].upper(), parts[1], parts[2]
    if region not in REGION_CONFIGS:
        return await message.reply("❌ Invalid region.", parse_mode=ParseMode.HTML)
    if not uid.isdigit():
        return await message.reply("❌ UID must be numeric.", parse_mode=ParseMode.HTML)
    if not days.isdigit() or int(days) <= 0:
        return await message.reply("❌ Days must be a positive number.", parse_mode=ParseMode.HTML)
    task = create_auto_task("visit", uid, region, days, added_by=message.from_user.id)
    auto_tasks.append(task); save_all()
    expiry = datetime.fromisoformat(task["end_date"]).strftime("%Y-%m-%d")
    await message.reply(
        f"✅ <b>Auto Visit Activated!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 UID: <code>{uid}</code>\n"
        f"🌍 Region: <b>{region}</b>\n"
        f"📅 Expiry: <b>{expiry}</b>\n"
        f"⚡ Visits/Day: <b>{likes_per_day_setting}</b>\n"
        f"🔑 Task ID: <code>{task['id']}</code>\n\n"
        f"👑 {OWNERS}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("autospam"))
@admin_required
async def auto_spam_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply(
            "Usage: <code>/autospam &lt;region&gt; &lt;uid&gt; &lt;days&gt;</code>\n"
            "Example: <code>/autospam BD 3074306062 30</code>",
            parse_mode=ParseMode.HTML
        )
    parts = command.args.split()
    if len(parts) != 3:
        return await message.reply("❌ Invalid format. Use: <code>/autospam BD 3074306062 30</code>", parse_mode=ParseMode.HTML)
    region, uid, days = parts[0].upper(), parts[1], parts[2]
    if region not in REGION_CONFIGS:
        return await message.reply("❌ Invalid region.", parse_mode=ParseMode.HTML)
    if not uid.isdigit():
        return await message.reply("❌ UID must be numeric.", parse_mode=ParseMode.HTML)
    if not days.isdigit() or int(days) <= 0:
        return await message.reply("❌ Days must be a positive number.", parse_mode=ParseMode.HTML)
    task = create_auto_task("spam", uid, region, days, added_by=message.from_user.id)
    auto_tasks.append(task); save_all()
    expiry = datetime.fromisoformat(task["end_date"]).strftime("%Y-%m-%d")
    await message.reply(
        f"✅ <b>Auto Spam Activated!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 UID: <code>{uid}</code>\n"
        f"🌍 Region: <b>{region}</b>\n"
        f"📅 Expiry: <b>{expiry}</b>\n"
        f"⚡ Spam/Day: <b>{likes_per_day_setting}</b>\n"
        f"🔑 Task ID: <code>{task['id']}</code>\n\n"
        f"👑 {OWNERS}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("autolist"))
@admin_required
async def list_auto_tasks(message: types.Message):
    today = datetime.now().date()
    active = [t for t in auto_tasks if datetime.fromisoformat(t["end_date"]).date() >= today]
    if not active:
        return await message.reply("📭 No active auto tasks.", parse_mode=ParseMode.HTML)
    lines = [f"📋 <b>Active Auto Tasks ({len(active)})</b>\n━━━━━━━━━━━━━━━━━━━"]
    for t in active:
        expiry = datetime.fromisoformat(t["end_date"]).strftime("%Y-%m-%d")
        last = t.get("last_sent_date")
        last_str = datetime.fromisoformat(last).strftime("%m-%d %H:%M") if last else "Never"
        lines.append(
            f"\n🔑 ID: <code>{t['id']}</code>\n"
            f"📌 Type: <b>{t['type'].upper()}</b> | Region: <b>{t['region']}</b>\n"
            f"🆔 UID: <code>{t['uid']}</code>\n"
            f"📅 Expiry: <b>{expiry}</b>\n"
            f"⏱️ Last sent: {last_str}"
        )
    await message.reply("\n".join(lines), parse_mode=ParseMode.HTML)

@dp.message(Command("autostatus"))
@admin_required
async def auto_status_cmd(message: types.Message):
    today = datetime.now().date()
    active = [t for t in auto_tasks if datetime.fromisoformat(t["end_date"]).date() >= today]
    expired = [t for t in auto_tasks if datetime.fromisoformat(t["end_date"]).date() < today]
    sent_today = [t for t in active if t.get("last_sent_date") and datetime.fromisoformat(t["last_sent_date"]).date() == today]
    await message.reply(
        f"⚡ <b>Auto Task Status</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Active tasks: <b>{len(active)}</b>\n"
        f"❌ Expired tasks: <b>{len(expired)}</b>\n"
        f"📤 Sent today: <b>{len(sent_today)}</b>\n"
        f"⏰ Next check in: <b>{AUTO_INTERVAL_HOURS}h</b>\n"
        f"⚡ Daily limit: <b>{likes_per_day_setting}</b>\n\n"
        f"<b>Breakdown:</b>\n"
        f"❤️ Like tasks: {len([t for t in active if t['type']=='like'])}\n"
        f"👀 Visit tasks: {len([t for t in active if t['type']=='visit'])}\n"
        f"📨 Spam tasks: {len([t for t in active if t['type']=='spam'])}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("autocancel"))
@admin_required
async def cancel_auto_task(message: types.Message, command: CommandObject):
    if not command.args:
        return await message.reply("Usage: <code>/autocancel &lt;task_id&gt;</code>", parse_mode=ParseMode.HTML)
    task_id = command.args.strip()
    for i, t in enumerate(auto_tasks):
        if t["id"] == task_id:
            del auto_tasks[i]; save_all()
            return await message.reply(f"✅ Task <code>{task_id}</code> cancelled.", parse_mode=ParseMode.HTML)
    await message.reply("❌ Task ID not found.")

# ==================== MAIN USER COMMANDS ====================
async def _execute_command(proc_msg, cmd, region, uid):
    global total_likes_sent, total_visits_sent, total_spam_sent
    try:
        if cmd == "like":
            res = await run_global_like_engine(uid, region)
            await proc_msg.edit_text(
                f"🌟 <b>LIKES DELIVERED!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {res.get('name')}\n"
                f"🆔 <b>UID:</b> <code>{res.get('uid')}</code>\n"
                f"📈 <b>Before:</b> {res.get('LikesBefore')}\n"
                f"🚀 <b>After:</b> {res.get('LikeAfter')}\n"
                f"🔥 <b>Added:</b> +{res.get('LikesAddedByMrcSulav')}\n\n"
                f"👑 {OWNERS}\n📢 {REDIRECT_LINK}",
                parse_mode=ParseMode.HTML
            )
        elif cmd == "visits":
            async with aiohttp.ClientSession() as sess:
                api_url = f"https://mrc-visit-api.vercel.app/api/visit_player?target_id={uid}&region={region.lower()}"
                async with sess.get(api_url) as resp:
                    res = await resp.json()
            total_visits_sent += 1; save_all()
            await proc_msg.edit_text(
                f"👀 <b>VISITS DELIVERED!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {res.get('name', 'Unknown')}\n"
                f"🌍 <b>Server:</b> {res.get('server', region)}\n"
                f"✅ <b>Success:</b> {res.get('SuccesVisits')}\n"
                f"❌ <b>Failed:</b> {res.get('FailedVisits')}\n\n"
                f"👑 {OWNERS}\n📢 {REDIRECT_LINK}",
                parse_mode=ParseMode.HTML
            )
        elif cmd == "spam":
            async with aiohttp.ClientSession() as sess:
                api_url = f"https://mrc-spam-api.vercel.app/api/spam_friend?target_id={uid}&region={region.lower()}"
                async with sess.get(api_url) as resp:
                    res = await resp.json()
            total_spam_sent += 1; save_all()
            await proc_msg.edit_text(
                f"📨 <b>SPAM COMPLETED!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {res.get('name', 'Unknown')}\n"
                f"🌍 <b>Server:</b> {res.get('server', region)}\n"
                f"✅ <b>Success:</b> {res.get('SuccesCount')}\n"
                f"❌ <b>Failed:</b> {res.get('FailedCount')}\n\n"
                f"👑 {OWNERS}\n📢 {REDIRECT_LINK}",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await proc_msg.edit_text(
            f"❌ <b>Error:</b>\n<code>{str(e)}</code>\n\nCheck UID/Region and try again.",
            parse_mode=ParseMode.HTML
        )

@dp.message(Command("like", "visits", "spam"))
async def handle_main_commands(message: types.Message, command: CommandObject):
    if not await check_group(message): return
    user_id = message.from_user.id

    if is_banned(user_id):
        return await message.reply("🚫 You are banned from this bot.", parse_mode=ParseMode.HTML)
    if maintenance_mode and not is_admin(user_id):
        return await message.reply("🔧 Bot is under maintenance. Try later.", parse_mode=ParseMode.HTML)

    if not command.args:
        return await message.reply(
            f"⚠️ Usage: <code>/{command.command} &lt;region&gt; &lt;uid&gt;</code>\n"
            f"Regions: <code>BD</code> | <code>SG</code> | <code>IND</code>",
            parse_mode=ParseMode.HTML
        )
    parts = command.args.split()
    if len(parts) != 2:
        return await message.reply(
            f"⚠️ Usage: <code>/{command.command} &lt;region&gt; &lt;uid&gt;</code>",
            parse_mode=ParseMode.HTML
        )

    region, uid = parts[0].upper(), parts[1]
    if region not in REGION_CONFIGS:
        return await message.reply("⚠️ Invalid region. Use: <code>BD, SG, IND</code>", parse_mode=ParseMode.HTML)
    if not uid.isdigit():
        return await message.reply("⚠️ UID must be numeric.", parse_mode=ParseMode.HTML)

    # ---- ADMINS BYPASS VERIFICATION — EXECUTE DIRECTLY ----
    if is_admin(user_id):
        proc_msg = await message.reply(
            f"⚡ <b>Admin Direct Execute</b>\n\n"
            f"⏳ Processing <b>{command.command.upper()}</b> for UID <code>{uid}</code> [{region}]...",
            parse_mode=ParseMode.HTML
        )
        await _execute_command(proc_msg, command.command, region, uid)
        return

    # ---- REGULAR USERS — SHRINK LINK VERIFICATION ----
    token = secrets.token_urlsafe(16)
    tokens[token] = {
        "user_id": user_id,
        "command": command.command,
        "region": region,
        "uid": uid,
        "timestamp": time.time()
    }
    save_all()

    bot_me = await bot.get_me()
    long_url = f"https://t.me/{bot_me.username}?start={token}"

    wait_msg = await message.reply("⏳ <i>Generating verification link...</i>", parse_mode=ParseMode.HTML)
    short_url = await get_short_link(long_url)

    if not short_url:
        tokens.pop(token, None); save_all()
        return await wait_msg.edit_text(
            "❌ <b>ShrinkEarn API failed.</b> Please try again later.",
            parse_mode=ParseMode.HTML
        )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Verify & Execute 🔥", url=short_url)]
    ])
    await wait_msg.edit_text(
        f"🚀 <b>VERIFICATION REQUIRED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 UID: <code>{uid}</code> | 🌍 {region}\n"
        f"📌 Command: <b>{command.command.upper()}</b>\n\n"
        f"👇 Click below and complete the page to run your request:\n\n"
        f"👑 {OWNERS}",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )

# ==================== MAIN ====================
async def main():
    # Ensure super admins are always in the admins set
    for sa in SUPER_ADMINS:
        admins.add(sa)
    save_all()
    asyncio.create_task(auto_scheduler())
    print(f"✅ Bot running! Super admins: {SUPER_ADMINS} | Owners: {OWNERS}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
