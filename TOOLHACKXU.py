import threading
import base64
import os
import time
import re
import json
import random
import requests
import socket
import sys
from time import sleep
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# Thư viện cần thiết
try:
    from faker import Faker
    from requests import session
    from colorama import Fore, Style, init
    import pystyle
    from tqdm import tqdm
    import pyfiglet
except ImportError:
    os.system("pip install faker requests colorama bs4 pystyle tqdm pyfiglet")
    os.system("pip3 install requests pysocks")
    print('__Vui Lòng Chạy Lại Tool__')
    sys.exit()

init(autoreset=True)
from pystyle import Colors, Colorate, Center, Add, Anime, Write, System

# ========= CẤU HÌNH MÀU SẮC ========= #
class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[35m'
    MAGENTA = '\033[35m'
    PINK = '\033[95m'
    ORANGE = '\033[38;5;214m'
    WHITE = '\033[37m'
    LIGHTBLACK_EX = '\033[90m'
    END = '\033[0m'
    
    @staticmethod
    def RAINBOW():
        return [Color.RED, Color.ORANGE, Color.YELLOW, Color.GREEN, Color.CYAN, Color.BLUE, Color.PURPLE]

# ========= DANH SÁCH KEY VIP ========= #
KEY_VIP = ["0345543851", "NOVELAH2024", "SUPERVIP999"]

# ========= HIỆU ỨNG CHỮ ========= #
def print_rainbow(text):
    """In chữ với hiệu ứng cầu vồng"""
    rainbow_text = ""
    for i, char in enumerate(text):
        color = Color.RAINBOW()[i % len(Color.RAINBOW())]
        rainbow_text += f"{color}{char}"
    print(rainbow_text + Color.END)

def print_gradient(text, color1=None, color2=None, end="\n"):
    """In chữ với hiệu ứng gradient - FIXED VERSION"""
    if color1 is None:
        color1 = Color.CYAN
    if color2 is None:
        color2 = Color.MAGENTA
    
    # Nếu là màu đơn, in bình thường
    if color1 == color2 or len(text) <= 1:
        print(f"{color1}{text}{Color.END}", end=end)
        return
    
    gradient_text = ""
    length = len(text)
    
    # Tạo gradient
    for i, char in enumerate(text):
        if length > 1:
            ratio = i / (length - 1)
        else:
            ratio = 0.5
        
        # Chuyển đổi màu RGB
        if color1 == Color.CYAN and color2 == Color.MAGENTA:
            r1, g1, b1 = 0, 191, 255  # CYAN
            r2, g2, b2 = 255, 0, 255  # MAGENTA
        elif color1 == Color.GREEN and color2 == Color.YELLOW:
            r1, g1, b1 = 0, 255, 0    # GREEN
            r2, g2, b2 = 255, 255, 0  # YELLOW
        elif color1 == Color.RED and color2 == Color.ORANGE:
            r1, g1, b1 = 255, 0, 0    # RED
            r2, g2, b2 = 255, 165, 0  # ORANGE
        elif color1 == Color.PURPLE and color2 == Color.PINK:
            r1, g1, b1 = 128, 0, 128  # PURPLE
            r2, g2, b2 = 255, 105, 180 # PINK
        else:
            # Màu mặc định
            r1, g1, b1 = 0, 191, 255
            r2, g2, b2 = 255, 0, 255
        
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        
        gradient_text += f"\033[38;2;{r};{g};{b}m{char}"
    
    print(gradient_text + Color.END, end=end)

def print_typing(text, delay=0.01, end="\n"):
    """Hiệu ứng gõ chữ"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    if end:
        print(end=end)

def animate_banner():
    """Hiệu ứng banner động"""
    banners = [
        """
╔═══╗╔═══╗╔═══╗╔═══╗╔══╗ ╔═══╗╔═══╗╔╗ ╔╗
║╔══╝║╔══╝║╔══╝║╔═╗║║╔╗║ ║╔═╗║║╔══╝║║ ║║
║╚══╗║╚══╗║╚══╗║╚═╝║║╚╝╚╗║╚═╝║║╚══╗║╚═╝║
║╔══╝║╔══╝║╔══╝║╔╗╔╝║╔═╗║║╔╗╔╝║╔══╝║╔═╗║
║╚══╗║╚══╗║╚══╗║║║╚╗║╚═╝║║║║╚╗║╚══╗║║ ║║
╚═══╝╚═══╝╚═══╝╚╝╚═╝╚═══╝╚╝╚═╝╚═══╝╚╝ ╚╝
        """,
        """
▓█████▄ ▓█████  ██▓     ██▓███   ██░ ██ ▓█████  ██▀███  
▒██▀ ██▌▓█   ▀ ▓██▒    ▓██░  ██▒▓██░ ██▒▓█   ▀ ▓██ ▒ ██▒
░██   █▌▒███   ▒██░    ▓██░ ██▓▒▒██▀▀██░▒███   ▓██ ░▄█ ▒
░▓█▄   ▌▒▓█  ▄ ▒██░    ▒██▄█▓▒ ▒░▓█ ░██ ▒▓█  ▄ ▒██▀▀█▄  
░▒████▓ ░▒████▒░██████▒▒██▒ ░  ░░▓█▒░██▓░▒████▒░██▓ ▒██▒
 ▒▒▓  ▒ ░░ ▒░ ░░ ▒░▓  ░▒▓▒░ ░  ░ ▒ ░░▒░▒░░ ▒░ ░░ ▒▓ ░▒▓░
 ░ ▒  ▒  ░ ░  ░░ ░ ▒  ░░▒ ░      ▒ ░▒░ ░ ░ ░  ░  ░▒ ░ ▒░
 ░ ░  ░    ░     ░ ░   ░░        ░  ░░ ░   ░     ░░   ░ 
   ░       ░  ░    ░  ░          ░  ░  ░   ░  ░   ░     
 ░                                                  
        """
    ]
    for banner in banners:
        os.system("clear")
        print_gradient(banner)
        time.sleep(0.3)

# ========= HỆ THỐNG KEY NÂNG CAO ========= #
def encrypt_data(data):
    return base64.b64encode(data.encode()).decode()

def decrypt_data(encrypted_data):
    return base64.b64decode(encrypted_data.encode()).decode()

def get_ip_address():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return None

def luu_thong_tin_ip(ip, key, expiration_date):
    data = {ip: {'key': key, 'expiration_date': expiration_date.isoformat()}}
    encrypted_data = encrypt_data(json.dumps(data))
    with open('ip_key.json', 'w') as f:
        f.write(encrypted_data)
    print_gradient(f"[✓] Đã lưu key cho IP: {ip}", Color.GREEN, Color.CYAN)

def tai_thong_tin_ip():
    try:
        with open('ip_key.json', 'r') as f:
            return json.loads(decrypt_data(f.read()))
    except:
        return None

def kiem_tra_ip(ip):
    data = tai_thong_tin_ip()
    if data and ip in data:
        expiration_date = datetime.fromisoformat(data[ip]['expiration_date'])
        if expiration_date > datetime.now():
            return data[ip]['key']
    return None

def generate_key_and_url(ip_address):
    ngay = int(datetime.now().day)
    key1 = str(ngay * 27 + 27)
    ip_numbers = ''.join(filter(str.isdigit, ip_address))
    key = f'NVL{key1}{ip_numbers}V3'
    expiration_date = datetime.now().replace(hour=23, minute=59, second=0, microsecond=0)
    url = f'https://www.webkey.x10.mx/?ma={key}'
    return url, key, expiration_date

def get_shortened_link(url):
    try:
        token = "66bc3245dfd246144040ac98"
        api_url = f"https://link4m.co/api-shorten/v2?api={token}&url={url}"
        res = requests.get(api_url, timeout=5)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": f"Lỗi: {e}"}

def display_key_menu():
    os.system("clear")
    print_gradient("=" * 60)
    
    # Banner chính
    try:
        banner = pyfiglet.figlet_format("NOVELAH", font="slant")
        print_gradient(banner)
    except:
        print_gradient("╔══════════════════════════════════════╗")
        print_gradient("║         NOVELAH AUTO TOOL            ║")
        print_gradient("╚══════════════════════════════════════╝")
    
    print_gradient("✨ AUTO TOOL V5 - PREMIUM EDITION ✨", Color.PINK, Color.YELLOW)
    print_gradient("=" * 60)
    
    # Info box
    print_gradient("[📡] THÔNG TIN HỆ THỐNG", Color.CYAN, Color.BLUE)
    print_gradient(f"  ├─ Ngày hệ thống: {datetime.now().strftime('%d/%m/%Y')}")
    print_gradient(f"  ├─ Giờ hệ thống: {datetime.now().strftime('%H:%M:%S')}")
    print_gradient(f"  └─ Phiên bản: V5.0 ULTIMATE")
    print_gradient("-" * 60)

def check_key():
    ip = get_ip_address()
    display_key_menu()
    
    if not ip:
        print_gradient("[✗] Không thể lấy IP! Vui lòng kiểm tra kết nối", Color.RED, Color.ORANGE)
        sys.exit()
    
    print_gradient(f"[🌐] IP CỦA BẠN: {ip}", Color.GREEN, Color.CYAN)
    print_gradient("-" * 60)
    
    existing_key = kiem_tra_ip(ip)
    if existing_key:
        print_gradient("[✓] KEY ĐÃ ĐƯỢC KÍCH HOẠT", Color.GREEN, Color.YELLOW)
        print_gradient("[→] Đang vào tool...", Color.CYAN, Color.MAGENTA)
        sleep(2)
        return True
    
    url, key, expiration_date = generate_key_and_url(ip)
    
    # Menu lựa chọn với animation
    print_gradient("🎮 CHỌN PHƯƠNG THỨC KÍCH HOẠT", Color.YELLOW, Color.ORANGE)
    
    options = [
        f"{Color.GREEN}⎈ 1. LẤY KEY MIỄN PHÍ (FREE){Color.END}",
        f"{Color.MAGENTA}✨ 2. KEY VIP PREMIUM{Color.END}",
        f"{Color.CYAN}⚡ 3. KIỂM TRA KEY HIỆN TẠI{Color.END}"
    ]
    
    for option in options:
        print_typing(option, 0.03)
    
    print_gradient("─" * 60)
    
    while True:
        print_gradient("[?] Lựa chọn của bạn (1-3): ", Color.PURPLE, Color.PINK, end="")
        ch = input()
        
        if ch == "1":
            print_gradient("[🌀] Đang tạo link kích hoạt...", Color.BLUE, Color.CYAN)
            for i in range(10):
                print_gradient(f"\r[🌀] Đang tạo link kích hoạt... [{i*10}%]", Color.BLUE, Color.CYAN, end="")
                time.sleep(0.1)
            print()
            
            data = get_shortened_link(url)
            if data.get("status") == "error":
                print_gradient(f"[✗] Lỗi: {data.get('message')}", Color.RED, Color.ORANGE)
                sys.exit()
            
            link = data.get("shortenedUrl")
            print_gradient("[🔗] LINK VƯỢT KEY:", Color.GREEN, Color.YELLOW)
            print_gradient(f"   ╰─➤ {link}", Color.CYAN, Color.MAGENTA)
            print_gradient("─" * 60)
            print_gradient("[📝] VUI LÒNG TRUY CẬP LINK TRÊN ĐỂ LẤY KEY", Color.YELLOW, Color.ORANGE)
            
            for i in range(3, 0, -1):
                print_gradient(f"[⌛] Đang chờ nhập key... {i}s", Color.CYAN, Color.BLUE, end="\r")
                time.sleep(1)
            print()
            
            while True:
                print_gradient("[🔑] NHẬP KEY ĐÃ VƯỢT: ", Color.PURPLE, Color.PINK, end="")
                key_inp = input()
                
                if key_inp == key:
                    print_gradient("[✓] KEY CHÍNH XÁC!", Color.GREEN, Color.YELLOW)
                    print_gradient("[⚡] Đang kích hoạt bản quyền...", Color.CYAN, Color.MAGENTA)
                    
                    for i in range(1, 4):
                        print_gradient(f"[{i}/3] Đang thiết lập...", Color.BLUE, Color.CYAN, end="\r")
                        time.sleep(1)
                    print()
                    
                    luu_thong_tin_ip(ip, key_inp, expiration_date)
                    print_gradient("[🎉] KÍCH HOẠT THÀNH CÔNG!", Color.GREEN, Color.YELLOW)
                    sleep(2)
                    return True
                else:
                    print_gradient("[✗] KEY KHÔNG CHÍNH XÁC!", Color.RED, Color.ORANGE)
                    print_gradient("[↻] Vui lòng thử lại...", Color.YELLOW, Color.PURPLE)
        
        elif ch == "2":
            print_gradient("[💰] NHẬP KEY VIP: ", Color.MAGENTA, Color.PINK, end="")
            key_inp = input()
            
            if key_inp in KEY_VIP:
                print_gradient("[✓] KEY VIP HỢP LỆ!", Color.GREEN, Color.YELLOW)
                print_gradient("[⚡] Đang kích hoạt VIP...", Color.MAGENTA, Color.PURPLE)
                
                # Hiệu ứng kích hoạt VIP
                for _ in range(3):
                    for symbol in ["✦", "✧", "✸", "✹"]:
                        print_gradient(f"[VIP] {symbol} Đang kích hoạt... {symbol}", Color.MAGENTA, Color.PINK, end="\r")
                        time.sleep(0.1)
                print()
                
                exp = datetime.now() + timedelta(days=3650)
                luu_thong_tin_ip(ip, key_inp, exp)
                print_gradient("[✨] KÍCH HOẠT VIP THÀNH CÔNG!", Color.MAGENTA, Color.PURPLE)
                print_gradient("[🌟] Hạn sử dụng: VĨNH VIỄN", Color.YELLOW, Color.ORANGE)
                sleep(2)
                return True
            else:
                print_gradient("[✗] KEY VIP KHÔNG HỢP LỆ!", Color.RED, Color.ORANGE)
        
        elif ch == "3":
            print_gradient("[🔍] KIỂM TRA THÔNG TIN KEY", Color.CYAN, Color.BLUE)
            data = tai_thong_tin_ip()
            if data and ip in data:
                exp_date = datetime.fromisoformat(data[ip]['expiration_date'])
                if exp_date > datetime.now():
                    print_gradient("[✓] KEY ĐANG HOẠT ĐỘNG", Color.GREEN, Color.YELLOW)
                    print_gradient(f"[📅] Hạn dùng đến: {exp_date.strftime('%d/%m/%Y %H:%M')}", Color.CYAN, Color.BLUE)
                else:
                    print_gradient("[✗] KEY ĐÃ HẾT HẠN", Color.RED, Color.ORANGE)
            else:
                print_gradient("[✗] CHƯA CÓ KEY KÍCH HOẠT", Color.RED, Color.ORANGE)
            input("\n[↵] Nhấn Enter để tiếp tục...")
            display_key_menu()
        
        else:
            print_gradient("[✗] VUI LÒNG CHỌN 1, 2 HOẶC 3!", Color.RED, Color.ORANGE)

# ========= HIỆU ỨNG NÂNG CAO ========= #
def animated_countdown(seconds, message):
    print_gradient(f"[⏳] {message}", Color.YELLOW, Color.ORANGE)
    for i in range(seconds, 0, -1):
        bar_length = 30
        filled = int((seconds - i) / seconds * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        percentage = ((seconds - i) / seconds) * 100
        print_gradient(f"[{bar}] {i}s - {percentage:.1f}%", Color.CYAN, Color.BLUE, end="\r")
        time.sleep(1)
    print_gradient("[✓] Hoàn tất!" + " " * 40, Color.GREEN, Color.YELLOW)

def loading_animation(task, duration=2):
    print_gradient(f"[🌀] {task}", Color.CYAN, Color.BLUE, end="")
    spinner = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    start_time = time.time()
    while time.time() - start_time < duration:
        for symbol in spinner:
            print_gradient(f"\r[🌀] {task} {symbol}", Color.CYAN, Color.BLUE, end="")
            time.sleep(0.1)
    print_gradient(f"\r[✓] {task} Hoàn tất!", Color.GREEN, Color.YELLOW)

# ========= NOVELAH TOOL NÂNG CAO ========= #
def display_main_menu():
    os.system("clear")
    print_gradient("=" * 60)
    
    # Animated title
    title = """
╔╦╗╦ ╦╔═╗╦  ╦  ╔═╗╔═╗╦ ╦
 ║ ║║║╠═╝║  ║  ║ ║║  ╠═╣
 ╩ ╚╩╝╩  ╩═╝╩═╝╚═╝╚═╝╩ ╩
    """
    print_gradient(title, Color.CYAN, Color.MAGENTA)
    print_gradient("✨ TOOL AUTO ULTIMATE V5 ✨", Color.PINK, Color.YELLOW)
    print_gradient("=" * 60)
    
    # User info
    print_gradient("[👤] THÔNG TIN NGƯỜI DÙNG", Color.GREEN, Color.CYAN)
    ip = get_ip_address()
    print_gradient(f"  ├─ IP: {ip}")
    print_gradient(f"  ├─ Thời gian: {datetime.now().strftime('%H:%M:%S')}")
    print_gradient(f"  └─ Trạng thái: PREMIUM ACTIVE")
    print_gradient("-" * 60)
    
    # Menu options với icon đẹp
    menu_items = [
        ("🌟", "AUTO ĐỌC TRUYỆN", "Tự động đọc truyện nhận coin", Color.YELLOW, Color.ORANGE),
        ("📅", "AUTO ĐIỂM DANH", "Điểm danh hàng ngày", Color.GREEN, Color.CYAN),
        ("⚡", "AUTO NHẬN QUÀ", "Nhận quà miễn phí", Color.MAGENTA, Color.PURPLE),
        ("📊", "THỐNG KÊ", "Xem thống kê coin", Color.BLUE, Color.CYAN),
        ("⚙️", "CÀI ĐẶT", "Cài đặt tool", Color.PURPLE, Color.PINK),
        ("🚪", "THOÁT", "Thoát tool", Color.RED, Color.ORANGE)
    ]
    
    print_gradient("[🎮] MENU CHỨC NĂNG", Color.YELLOW, Color.ORANGE)
    for i, (icon, name, desc, color1, color2) in enumerate(menu_items, 1):
        print_gradient(f"  {Color.WHITE}[{i}] {icon} {name}", color1, color2)
        print_gradient(f"      ╰─ {desc}", Color.WHITE, Color.LIGHTBLACK_EX)
    print_gradient("=" * 60)

def auto_read_premium():
    os.system("clear")
    
    # Banner auto read
    banner = """
    ╔══════════════════════════════════════╗
    ║        🌟 AUTO ĐỌC TRUYỆN 🌟         ║
    ╚══════════════════════════════════════╝
    """
    print_gradient(banner, Color.YELLOW, Color.ORANGE)
    
    while True:
        print_gradient("[🔢] NHẬP ID NGƯỜI DÙNG: ", Color.CYAN, Color.BLUE, end="")
        uid = input()
        
        if uid.isdigit() and len(uid) >= 5:
            break
        print_gradient("[✗] ID KHÔNG HỢP LỆ! Vui lòng nhập lại...", Color.RED, Color.ORANGE)
    
    print_gradient(f"[✓] ĐANG ĐỌC CHO ID: {uid}", Color.GREEN, Color.YELLOW)
    print_gradient("-" * 50)
    
    animated_countdown(5, "ĐANG KHỞI ĐỘNG HỆ THỐNG")
    
    session_count = 0
    total_coins = 0
    
    try:
        while True:
            session_count += 1
            coins = random.randint(30, 80)
            total_coins += coins
            
            # Animated coin earning
            print_gradient(f"[📚] PHIÊN ĐỌC #{session_count}", Color.MAGENTA, Color.PURPLE)
            print_gradient(f"[??] ĐANG NHẬN COIN: ", Color.YELLOW, Color.ORANGE, end="")
            
            for i in range(coins):
                print_gradient(f"\r[💰] ĐANG NHẬN COIN: +{i+1} ", Color.GREEN, Color.YELLOW, end="")
                time.sleep(0.01)
            print()
            
            print_gradient(f"[🎉] NHẬN ĐƯỢC: +{coins} coin", Color.GREEN, Color.YELLOW)
            print_gradient(f"[🏦] TỔNG COIN: {total_coins} coin", Color.CYAN, Color.BLUE)
            
            # Progress bar
            print_gradient("[⏳] THỜI GIAN CHỜ LƯỢT TIẾP: ", Color.PURPLE, Color.PINK)
            animated_countdown(10, "ĐANG CHỜ")
            
            print_gradient("-" * 50)
            
    except KeyboardInterrupt:
        print_gradient("\n[⚠️] DỪNG AUTO ĐỌC!", Color.RED, Color.ORANGE)
        print_gradient(f"[📊] TỔNG KẾT: {session_count} phiên - {total_coins} coin", Color.CYAN, Color.BLUE)
        input("\n[↵] Nhấn Enter để tiếp tục...")

def auto_checkin_premium():
    os.system("clear")
    
    banner = """
    ╔══════════════════════════════════════╗
    ║       📅 AUTO ĐIỂM DANH 📅           ║
    ╚══════════════════════════════════════╝
    """
    print_gradient(banner, Color.GREEN, Color.CYAN)
    
    print_gradient("[🔢] NHẬP ID NGƯỜI DÙNG: ", Color.CYAN, Color.BLUE, end="")
    uid = input()
    
    if not uid.isdigit() or len(uid) < 5:
        print_gradient("[✗] ID KHÔNG HỢP LỆ!", Color.RED, Color.ORANGE)
        return
    
    loading_animation(f"ĐANG ĐIỂM DANH CHO ID: {uid}", 3)
    
    # Animated success
    print_gradient("[✅] ĐIỂM DANH THÀNH CÔNG!", Color.GREEN, Color.YELLOW)
    
    # Reward animation
    rewards = ["+50 coin", "+1 lượt đọc", "+5 EXP", "VIP 1 ngày"]
    print_gradient("[🎁] PHẦN THƯỞNG NHẬN ĐƯỢC:", Color.MAGENTA, Color.PURPLE)
    
    for reward in rewards:
        print_gradient(f"  ├─ {reward}", Color.YELLOW, Color.ORANGE)
        time.sleep(0.5)
    
    print_gradient("  ╰─ 🎉 HOÀN TẤT!", Color.GREEN, Color.YELLOW)
    input("\n[↵] Nhấn Enter để về menu...")

def main_menu():
    while True:
        display_main_menu()
        print_gradient("[?] LỰA CHỌN CỦA BẠN (1-6): ", Color.PURPLE, Color.PINK, end="")
        choice = input()
        
        if choice == "1":
            auto_read_premium()
        elif choice == "2":
            auto_checkin_premium()
        elif choice == "3":
            print_gradient("[⚡] TÍNH NĂNG ĐANG PHÁT TRIỂN...", Color.CYAN, Color.BLUE)
            time.sleep(2)
        elif choice == "4":
            print_gradient("[📊] TÍNH NĂNG ĐANG PHÁT TRIỂN...", Color.CYAN, Color.BLUE)
            time.sleep(2)
        elif choice == "5":
            print_gradient("[⚙️] TÍNH NĂNG ĐANG PHÁT TRIỂN...", Color.CYAN, Color.BLUE)
            time.sleep(2)
        elif choice == "6":
            print_gradient("[🚪] ĐANG THOÁT TOOL...", Color.RED, Color.ORANGE)
            animated_countdown(3, "THOÁT")
            break
        else:
            print_gradient("[✗] LỰA CHỌN KHÔNG HỢP LỆ!", Color.RED, Color.ORANGE)
            time.sleep(1)

# ========= KHỞI CHẠY TOOL ========= #
if __name__ == "__main__":
    # Startup animation
    animate_banner()
    
    # Kiểm tra key
    if check_key():
        # Welcome animation
        os.system("clear")
        try:
            welcome_text = pyfiglet.figlet_format("WELCOME", font="starwars")
            print_gradient(welcome_text, Color.CYAN, Color.MAGENTA)
        except:
            print_gradient("╔══════════════════════════════════════╗")
            print_gradient("║          CHÀO MỪNG                   ║")
            print_gradient("╚══════════════════════════════════════╝")
        
        print_gradient("✨ CHÀO MỪNG ĐẾN VỚI NOVELAH TOOL ✨", Color.YELLOW, Color.ORANGE)
        print_gradient("⚡ PHIÊN BẢN PREMIUM - ULTIMATE V5 ⚡", Color.PINK, Color.PURPLE)
        
        animated_countdown(3, "ĐANG KHỞI ĐỘNG HỆ THỐNG")
        main_menu()
    
    print_gradient("\n[👋] CẢM ƠN ĐÃ SỬ DỤNG TOOL!", Color.CYAN, Color.BLUE)
    print_gradient("[💖] HẸN GẶP LẠI!", Color.PINK, Color.PURPLE)
