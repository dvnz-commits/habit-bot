import os, json, time, threading, requests
from datetime import datetime, timezone, timedelta
from flask import Flask

TOKEN   = os.environ.get('BOT_TOKEN', '')
CHAT_ID = os.environ.get('CHAT_ID', '')
DATA_FILE = 'data.json'

# Timezone Indonesia WITA (UTC+7)
WITA = timezone(timedelta(hours=8))

HABITS = {
    'belajar':  '📚 Belajar',
    'olahraga': '🏃 Olahraga',
    'tidur':    '🌙 Tidur Cukup',
    'kerja':    '💼 Kerja',
    'makan':    '🍽️ Makan Cukup',
    'mandi':    '🚿 Mandi 2x Sehari',
    'sosmed':   '📵 Tidak Scroll Sosmed',
    'youtube':  '🎬 Nonton Video Bermanfaat',
}

app = Flask(__name__)

def load():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except: return {}

def dump(d):
    with open(DATA_FILE, 'w') as f: json.dump(d, f)

def send(text):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json={'chat_id': CHAT_ID, 'text': text},
            timeout=10
        )
    except: pass

def get_updates(offset=None):
    try:
        params = {'timeout': 30}
        if offset: params['offset'] = offset
        r = requests.get(
            f'https://api.telegram.org/bot{TOKEN}/getUpdates',
            params=params, timeout=35
        )
        return r.json().get('result', [])
    except: return []

def now_wib():
    return datetime.now(WITA)

def handle(msg):
    text    = msg.get('text', '').strip()
    chat_id = str(msg['chat']['id'])
    if chat_id != str(CHAT_ID): return

    data = load()

    if text in ['/mulai', '/start']:
        daftar = '\n'.join([f"  {k} → {v}" for k, v in HABITS.items()])
        send(
            f"🤖 Bot Habit Tracker aktif! (Waktu: WITA)\n\n"
            f"Perintah:\n"
            f"/set [habit] [jam] — tambah pengingat\n"
            f"   Contoh: /set belajar 08:00\n\n"
            f"/lihat — lihat semua pengingat\n\n"
            f"/hapus [habit] [jam] — hapus pengingat\n"
            f"   Contoh: /hapus belajar 08:00\n\n"
            f"/waktu — cek waktu server sekarang\n\n"
            f"Nama habit:\n{daftar}"
        )

    elif text.lower() == '/waktu':
        sekarang = now_wib().strftime('%H:%M WITA, %d %B %Y')
        send(f"🕐 Waktu server sekarang:\n{sekarang}")

    elif text.lower().startswith('/set '):
        parts = text.split()
        if len(parts) == 3:
            hid, jam = parts[1].lower(), parts[2]
            if hid not in HABITS:
                send(f"❌ Habit tidak dikenal.\nGunakan: {', '.join(HABITS.keys())}")
            elif ':' not in jam or len(jam) != 5:
                send("❌ Format jam salah. Gunakan HH:MM\nContoh: 08:00")
            else:
                if hid not in data: data[hid] = []
                if jam not in data[hid]: data[hid].append(jam)
                dump(data)
                send(f"✅ Pengingat {HABITS[hid]} ditambahkan\n⏰ Jam {jam} WITA setiap hari")
        else:
            send("Format: /set [habit] [jam]\nContoh: /set belajar 08:00")

    elif text.lower() == '/lihat':
        aktif = {k: v for k, v in data.items() if v}
        if not aktif:
            send("Belum ada pengingat.\nGunakan /set untuk menambahkan.")
        else:
            lines = [f"{HABITS.get(k,k)}: {', '.join(sorted(v))} WITA" for k,v in aktif.items()]
            send("📋 Pengingat aktif:\n\n" + '\n'.join(lines))

    elif text.lower().startswith('/hapus '):
        parts = text.split()
        if len(parts) == 3:
            hid, jam = parts[1].lower(), parts[2]
            if hid in data and jam in data[hid]:
                data[hid].remove(jam)
                dump(data)
                send(f"🗑️ Pengingat {HABITS.get(hid,hid)} jam {jam} WITA dihapus")
            else:
                send("Pengingat tidak ditemukan. Cek /lihat untuk melihat daftar.")
        else:
            send("Format: /hapus [habit] [jam]\nContoh: /hapus belajar 08:00")

    else:
        send("Perintah tidak dikenal. Kirim /mulai untuk bantuan.")

def scheduler():
    while True:
        try:
            data = load()
            now  = now_wib().strftime('%H:%M')
            for hid, times in data.items():
                if now in times:
                    send(f"⏰ Waktunya {HABITS.get(hid, hid)}!\n\nJangan lupa tandai habit kamu hari ini. Semangat! 💪")
        except: pass
        time.sleep(60)

def polling():
    offset = None
    while True:
        updates = get_updates(offset)
        for u in updates:
            offset = u['update_id'] + 1
            if 'message' in u:
                handle(u['message'])

@app.route('/')
def home():
    waktu = now_wib().strftime('%H:%M WITA')
    return f'🤖 Habit Tracker Bot aktif! Waktu server: {waktu}'

if __name__ == '__main__':
    threading.Thread(target=scheduler, daemon=True).start()
    threading.Thread(target=polling,   daemon=True).start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
