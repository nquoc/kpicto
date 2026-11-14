import os
import sys
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
import qrcode

PORT = 8888
HOST = "0.0.0.0"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def main():
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)

    local_ip = get_local_ip()
    url = f"http://{local_ip}:{PORT}"

    # Generate QR Code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_path = os.path.join(web_dir, "qr_phone.png")
    img.save(img_path)

    # Save to artifact directory as well for preview in UI
    artifact_qr = r"C:\Users\quoc\.gemini\antigravity\brain\1a3f1ada-6c32-4202-95be-30efc04b91ec\qr_phone.png"
    try:
        img.save(artifact_qr)
    except Exception:
        pass

    print("=" * 60)
    print("🚀 MÁY CHỦ WEB KPI DASHBOARD ĐANG HOẠT ĐỘNG!")
    print(f"📱 TRUY CẬP TRÊN ĐIỆN THOẠI (CÙNG MẠNG WI-FI):")
    print(f"👉 Link: {url}")
    print(f"🖼️ File mã QR đã lưu tại: qr_phone.png")
    print("=" * 60)
    print("\nQuét mã QR dưới đây bằng camera điện thoại:")
    qr.print_ascii(invert=True)
    print("=" * 60)
    print("Nhấn Ctrl + C để dừng máy chủ bất cứ lúc nào.")

    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã tắt máy chủ.")
        httpd.server_close()

if __name__ == "__main__":
    main()
