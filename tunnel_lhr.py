import subprocess
import re
import sys
import time
import os
import threading
import urllib.request
import qrcode

URL_FILE = "current_public_url.txt"
QR_FILE = "qr_public.png"
ARTIFACT_QR = r"C:\Users\quoc\.gemini\antigravity\brain\1a3f1ada-6c32-4202-95be-30efc04b91ec\qr_public.png"

current_url = None

def keep_alive_worker():
    """Gửi request định kỳ để giữ tunnel không bị timeout do không có traffic"""
    while True:
        time.sleep(90)
        if current_url:
            try:
                req = urllib.request.Request(current_url, headers={'User-Agent': 'KeepAlive/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    pass
            except Exception:
                pass

t = threading.Thread(target=keep_alive_worker, daemon=True)
t.start()

def update_url(url):
    global current_url
    current_url = url
    print(f"\n==================================================")
    print(f"🚀 PUBLIC LINK HIỆN TẠI: {url}")
    print(f"==================================================\n")
    sys.stdout.flush()

    try:
        with open(URL_FILE, "w", encoding="utf-8") as f:
            f.write(url)
    except Exception:
        pass

    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=3)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(QR_FILE)
        if os.path.exists(os.path.dirname(ARTIFACT_QR)):
            img.save(ARTIFACT_QR)
    except Exception:
        pass

cmd = [
    "ssh",
    "-R", "80:127.0.0.1:8888",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=NUL",
    "-o", "ServerAliveInterval=20",
    "-o", "ServerAliveCountMax=3",
    "nokey@localhost.run"
]

print("Bắt đầu khởi chạy SSH tunnel tới localhost.run...")
sys.stdout.flush()

while True:
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in iter(process.stdout.readline, ''):
            line_clean = line.strip()
            if line_clean:
                print(line_clean)
                sys.stdout.flush()

                # Tìm link dạng https://xxxx.lhr.life
                m = re.search(r'(https://[a-zA-Z0-9\.\-]+\.lhr\.life)', line_clean)
                if m:
                    found_url = m.group(1)
                    if found_url != current_url:
                        update_url(found_url)

        process.wait()
        print("⚠️ Tunnel vừa ngắt kết nối, đang tự động kết nối lại sau 3 giây...")
        sys.stdout.flush()
        time.sleep(3)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Lỗi tunnel: {e}, thử lại sau 5 giây...")
        sys.stdout.flush()
        time.sleep(5)
