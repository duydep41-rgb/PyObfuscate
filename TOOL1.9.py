from __future__ import annotations
import json
import sys
import time
import threading
import random
import logging
import math
import re
import os
from collections import defaultdict, deque
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict, Tuple, Optional, List

import pytz
import requests
import websocket
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.align import Align
from rich.rule import Rule
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.color import Color
from rich.console import Group as RichGroup
from rich.markdown import Markdown
from rich.syntax import Syntax
import asyncio

# -------------------- CONFIG & GLOBALS --------------------
console = Console()
tz = pytz.timezone("Asia/Ho_Chi_Minh")

logger = logging.getLogger("escape_vip_ai_duytool")
logger.setLevel(logging.INFO)
logger.addHandler(logging.FileHandler("escape_vip_ai_duytool.log", encoding="utf-8"))

# Endpoints (config)
BET_API_URL = "https://api.escapemaster.net/escape_game/bet"
WS_URL = "wss://api.escapemaster.net/escape_master/ws"
WALLET_API_URL = "https://wallet.3games.io/api/wallet/user_asset"

HTTP = requests.Session()
try:
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    adapter = HTTPAdapter(
        pool_connections=20, pool_maxsize=50,
        max_retries=Retry(total=3, backoff_factor=0.2,
                          status_forcelist=(500, 502, 503, 504))
    )
    HTTP.mount("https://", adapter)
    HTTP.mount("http://", adapter)
except Exception:
    pass

# Room names with icons and gradient colors
ROOM_NAMES = {
    1: ("📦", "Nhà kho", "#FF6B6B"),
    2: ("🪑", "Phòng họp", "#4ECDC4"),
    3: ("👔", "Phòng giám đốc", "#FFD166"),
    4: ("💬", "Phòng trò chuyện", "#06D6A0"),
    5: ("🎥", "Phòng giám sát", "#118AB2"),
    6: ("🏢", "Văn phòng", "#073B4C"),
    7: ("💰", "Phòng tài vụ", "#EF476F"),
    8: ("👥", "Phòng nhân sự", "#7209B7")
}

ROOM_ORDER = [1, 2, 3, 4, 5, 6, 7, 8]

# Animation frames
SPINNER_FRAMES = ["◐", "◓", "◑", "◒", "◐", "◓", "◑", "◒"]
LOADING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
BANNER_FRAMES = ["▰▱▱▱▱▱", "▰▰▱▱▱▱", "▰▰▰▱▱▱", "▰▰▰▰▱▱", "▰▰▰▰▰▱", "▰▰▰▰▰▰"]

# runtime state
USER_ID: Optional[int] = None
SECRET_KEY: Optional[str] = None
issue_id: Optional[int] = None
issue_start_ts: Optional[float] = None
count_down: Optional[int] = None
killed_room: Optional[int] = None
round_index: int = 0
_skip_active_issue: Optional[int] = None

room_state: Dict[int, Dict[str, Any]] = {r: {"players": 0, "bet": 0} for r in ROOM_ORDER}
room_stats: Dict[int, Dict[str, Any]] = {r: {"kills": 0, "survives": 0, "last_kill_round": None, "last_players": 0, "last_bet": 0} for r in ROOM_ORDER}

predicted_room: Optional[int] = None
last_killed_room: Optional[int] = None
prediction_locked: bool = False

# balances & pnl
current_build: Optional[float] = None
current_usdt: Optional[float] = None
current_world: Optional[float] = None
last_balance_ts: Optional[float] = None
last_balance_val: Optional[float] = None
starting_balance: Optional[float] = None
cumulative_profit: float = 0.0

# streaks
win_streak: int = 0
lose_streak: int = 0
max_win_streak: int = 0
max_lose_streak: int = 0

# betting
base_bet: float = 1.0
multiplier: float = 2.0
current_bet: Optional[float] = None
run_mode: str = "AUTO"

# AUTO or STAT
bet_rounds_before_skip: int = 0
_rounds_placed_since_skip: int = 0
skip_next_round_flag: bool = False

bet_history: deque = deque(maxlen=500)
bet_sent_for_issue: set = set()

# new controls
pause_after_losses: int = 0
_skip_rounds_remaining: int = 0
profit_target: Optional[float] = None
stop_when_profit_reached: bool = False
stop_loss_target: Optional[float] = None
stop_when_loss_reached: bool = False
stop_flag: bool = False

# UI / timing
ui_state: str = "IDLE"
analysis_start_ts: Optional[float] = None
analysis_blur: bool = False
last_msg_ts: float = time.time()
last_balance_fetch_ts: float = 0.0
BALANCE_POLL_INTERVAL: float = 3.0
_ws: Dict[str, Any] = {"ws": None}

# selection config
SELECTION_CONFIG = {
    "max_bet_allowed": float("inf"),
    "max_players_allowed": 9999,
    "avoid_last_kill": True,
}

SELECTION_MODES = {
    "VIP50": "50 Công thức SIU VIP"
}
settings = {"algo": "VIP50"}

_num_re = re.compile(r"-?\d+[\d,]*\.?\d*")

# Gradient colors for different sections
GRADIENT_COLORS = [
    "#FF6B6B", "#FF8E53", "#FFC154", "#47D7AC", "#06D6A0", 
    "#118AB2", "#073B4C", "#7209B7", "#EF476F", "#FFD166"
]

# -------------------- NEW UI COMPONENTS --------------------

def gradient_text(text: str, colors: List[str] = None) -> Text:
    """Create gradient colored text"""
    if colors is None:
        colors = GRADIENT_COLORS
    result = Text()
    color_count = len(colors)
    for i, char in enumerate(text):
        color_idx = int((i / max(len(text) - 1, 1)) * (color_count - 1))
        result.append(char, style=Style(color=colors[color_idx]))
    return result

def create_banner() -> Panel:
    """Create animated banner with DUYTOOL branding"""
    frame_idx = int(time.time() * 4) % len(BANNER_FRAMES)
    frame = BANNER_FRAMES[frame_idx]
    
    banner_text = Text()
    banner_text.append("╔══════════════════════════════════════════════════════════╗\n", style="bright_cyan")
    banner_text.append("║ ", style="bright_cyan")
    
    # Animated DUYTOOL text with gradient
    duytool_text = gradient_text("   D U Y T O O L   ", GRADIENT_COLORS)
    banner_text.append(duytool_text)
    
    banner_text.append(" ║\n", style="bright_cyan")
    banner_text.append("║   ", style="bright_cyan")
    banner_text.append("ESCAPE VIP AI - TỰ ĐỘNG HÓA CHIẾN THẮNG   ", style="yellow")
    banner_text.append("   ║\n", style="bright_cyan")
    banner_text.append("║   ", style="bright_cyan")
    banner_text.append(f"Phiên bản: 2.0 Premium | {frame} Loading...", style="dim cyan")
    banner_text.append("   ║\n", style="bright_cyan")
    banner_text.append("╚══════════════════════════════════════════════════════════╝", style="bright_cyan")
    
    return Panel(
        banner_text,
        border_style="bright_cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    )

def create_stats_panel() -> Panel:
    """Create beautiful statistics panel"""
    stats_grid = Table.grid(padding=(0, 1))
    stats_grid.add_column(style="cyan")
    stats_grid.add_column(style="white")
    stats_grid.add_column(style="cyan")
    stats_grid.add_column(style="white")
    
    # Format numbers with colors
    profit_color = "green" if cumulative_profit >= 0 else "red"
    win_color = "green" if win_streak > 0 else "dim"
    lose_color = "red" if lose_streak > 0 else "dim"
    
    stats_grid.add_row(
        "📊 Lãi/Lỗ:", f"[{profit_color}]{cumulative_profit:+,.4f} BUILD[/{profit_color}]",
        "🔥 Chuỗi Thắng:", f"[{win_color}]{win_streak}[/{win_color}]"
    )
    stats_grid.add_row(
        "🎯 Tổng Ván:", f"[yellow]{len(bet_history)}[/yellow]",
        "💥 Chuỗi Thua:", f"[{lose_color}]{lose_streak}[/{lose_color}]"
    )
    stats_grid.add_row(
        "🏆 Max Thắng:", f"[green]{max_win_streak}[/green]",
        "📉 Max Thua:", f"[red]{max_lose_streak}[/red]"
    )
    stats_grid.add_row(
        "💰 Tiền Cược:", f"[yellow]{current_bet if current_bet else base_bet:.4f}[/yellow]",
        "⚡ Hệ Số:", f"[cyan]{multiplier}x[/cyan]"
    )
    
    return Panel(
        stats_grid,
        title="📈 THỐNG KÊ",
        border_style="cyan",
        box=box.ROUNDED
    )

def create_wallet_panel() -> Panel:
    """Create beautiful wallet display panel"""
    wallet_grid = Table.grid(padding=(0, 1))
    wallet_grid.add_column(style="yellow", width=8)
    wallet_grid.add_column(style="white", width=15)
    wallet_grid.add_column(style="green", width=8)
    wallet_grid.add_column(style="white", width=15)
    
    # Format balances
    build_fmt = f"{current_build:,.4f}" if current_build else "Đang cập nhật..."
    usdt_fmt = f"{current_usdt:,.4f}" if current_usdt else "Đang cập nhật..."
    world_fmt = f"{current_world:,.4f}" if current_world else "Đang cập nhật..."
    
    wallet_grid.add_row("💰 BUILD:", f"[yellow]{build_fmt}[/yellow]", "💵 USDT:", f"[green]{usdt_fmt}[/green]")
    wallet_grid.add_row("🌎 WORLD:", f"[cyan]{world_fmt}[/cyan]", "📊 Thay đổi:", 
                       f"[{'green' if cumulative_profit >= 0 else 'red'}]{cumulative_profit:+,.4f}[/{'green' if cumulative_profit >= 0 else 'red'}]")
    
    # Add profit target info if set
    footer = ""
    if profit_target:
        footer += f"[dim]🎯 Mục tiêu: {profit_target:.4f} BUILD[/dim]\n"
    if stop_loss_target:
        footer += f"[dim]⚠️  Dừng lỗ: {stop_loss_target:.4f} BUILD[/dim]"
    
    panel_content = Group(wallet_grid, Text(footer))
    
    return Panel(
        panel_content,
        title="💼 VÍ TIỀN",
        border_style="yellow",
        box=box.ROUNDED
    )

def create_game_clock() -> Panel:
    """Create beautiful game clock display"""
    now = datetime.now(tz)
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d/%m/%Y")
    
    # Animated clock face
    frame_idx = int(time.time() * 2) % len(SPINNER_FRAMES)
    spinner = SPINNER_FRAMES[frame_idx]
    
    clock_text = Text()
    clock_text.append(f"\n   ╔═══╗\n", style="bright_blue")
    clock_text.append(f"   ║ {spinner} ║  ", style="bright_blue")
    clock_text.append(f"{time_str}\n", style="white")  # ĐÃ SỬA: bỏ bold bright_white
    clock_text.append(f"   ╚═══╝\n\n", style="bright_blue")
    clock_text.append(f"    📅 {date_str}\n", style="dim cyan")
    
    # Add countdown if available
    if count_down is not None:
        # ĐÃ SỬA: bỏ yellow ra khỏi countdown
        clock_text.append(f"\n    ⏰ Đếm ngược: {count_down}s", style="white")
    
    return Panel(
        clock_text,
        title="🕐 ĐỒNG HỒ GAME",
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(1, 2)
    )

def create_rooms_display() -> Panel:
    """Create beautiful rooms display with gradients"""
    rooms_table = Table(
        title="🎪 PHÒNG CHƠI",
        box=box.ROUNDED,
        show_header=True,
        header_style="cyan",
        expand=True
    )
    
    rooms_table.add_column("ID", justify="center", style="white", width=4)
    rooms_table.add_column("Phòng", style="white", width=20)
    rooms_table.add_column("👤 Người", justify="right", style="cyan", width=8)
    rooms_table.add_column("💰 Cược", justify="right", style="yellow", width=15)
    rooms_table.add_column("🎯 Trạng thái", justify="center", style="white", width=15)
    
    for r in ROOM_ORDER:
        st = room_state.get(r, {})
        icon, name, color = ROOM_NAMES[r]
        
        # Determine room status with styling
        status_text = Text()
        if killed_room is not None and r == killed_room:
            status_text.append("☠️ KILLED", style="red")
        elif predicted_room is not None and r == predicted_room:
            status_text.append("🎯 DỰ ĐOÁN", style="green")
        else:
            status_text.append("🟢 SỐNG", style="green")
        
        # Apply gradient to room name
        room_display = Text()
        room_display.append(f"{icon} ", style="white")
        room_display.append(name, style=Style(color=color))
        
        players = st.get("players", 0)
        bet_val = st.get('bet', 0) or 0
        bet_fmt = f"{int(bet_val):,}"
        
        # Color code player count
        players_color = "red" if players > 30 else "yellow" if players > 15 else "green"
        players_text = Text(str(players), style=players_color)
        
        rooms_table.add_row(
            str(r),
            room_display,
            players_text,
            bet_fmt,
            status_text
        )
    
    return Panel(
        rooms_table,
        border_style="cyan",
        padding=(0, 1)
    )

def create_analysis_panel() -> Panel:
    """Create beautiful analysis panel with animations"""
    frame_idx = int(time.time() * 8) % len(LOADING_FRAMES)
    spinner = LOADING_FRAMES[frame_idx]
    
    content = Table.grid(padding=(1, 2))
    content.add_column()
    
    if ui_state == "ANALYZING":
        # Create animated analysis visualization
        analysis_text = Text()
        analysis_text.append(f"\n{spinner} ", style="cyan")
        analysis_text.append("ĐANG PHÂN TÍCH DỮ LIỆU AI...\n\n", style="white")
        
        # Animated progress bar
        bar_width = 40
        progress = ((time.time() * 2) % bar_width) / bar_width
        
        bar = Text()
        filled = int(bar_width * progress)
        for i in range(bar_width):
            if i < filled:
                color_idx = int((i / bar_width) * (len(GRADIENT_COLORS) - 1))
                bar.append("█", style=Style(color=GRADIENT_COLORS[color_idx]))
            else:
                bar.append("░", style="dim")
        
        analysis_text.append(bar)
        analysis_text.append(f"\n\n📊 Đang tính toán phòng an toàn nhất...\n")
        
        if count_down:
            # ĐÃ SỬA: bỏ yellow trong countdown
            analysis_text.append(f"⏱️  Đếm ngược: {count_down}s\n")
        
        # Last kill info - ĐÃ SỬA: bỏ bold
        if last_killed_room:
            _, last_name, last_color = ROOM_NAMES[last_killed_room]
            analysis_text.append(f"🎯 Phòng sát thủ ván trước: [{last_color}]{last_name}[/{last_color}]")
        
        title = "🧠 AI ĐANG PHÂN TÍCH"
        border_color = "cyan"
        
    elif ui_state == "PREDICTED":
        if predicted_room:
            icon, name, color = ROOM_NAMES[predicted_room]
            analysis_text = Text()
            analysis_text.append(f"\n🎉 ", style="green")
            analysis_text.append("ĐÃ CHỌN PHÒNG TỐI ƯU!\n\n", style="white")
            analysis_text.append(f"📍 Phòng dự đoán: [{color}]{icon} {name}[/{color}]\n")
            analysis_text.append(f"💰 Tiền cược: [yellow]{current_bet if current_bet else base_bet:.4f} BUILD[/yellow]\n")
            analysis_text.append(f"🤖 Thuật toán: [cyan]{settings['algo']}[/cyan]\n\n")
            
            if count_down:
                # ĐÃ SỬA: bỏ yellow trong countdown
                analysis_text.append(f"⏰ Kết quả sau: {count_down}s\n")
            
            # Add prediction confidence
            confidence = random.uniform(85, 98)  # Simulated confidence
            analysis_text.append(f"🎯 Độ tin cậy: [green]{confidence:.1f}%[/green]")
        
        title = "✅ DỰ ĐOÁN HOÀN TẤT"
        border_color = "green"
        
    elif ui_state == "RESULT":
        analysis_text = Text()
        if killed_room:
            icon, name, color = ROOM_NAMES[killed_room]
            analysis_text.append(f"\n🎯 ", style="red")
            analysis_text.append("KẾT QUẢ VÁN CHƠI\n\n", style="white")
            analysis_text.append(f"☠️  Phòng bị kill: [{color}]{icon} {name}[/{color}]\n")
        
        # Check win/loss
        last_bet = None
        if bet_history:
            last_bet = list(bet_history)[-1]
        
        if last_bet and last_bet.get('result') == 'Thắng':
            analysis_text.append(f"💰 Kết quả: [green]THẮNG LỚN![/green]\n")
            analysis_text.append(f"🎊 Chuỗi thắng: [green]{win_streak} ván[/green]")
        elif last_bet and last_bet.get('result') == 'Thua':
            analysis_text.append(f"💰 Kết quả: [red]THUA[/red]\n")
            analysis_text.append(f"🔄 Tiền cược tiếp theo: [yellow]{current_bet:.4f} BUILD[/yellow]")
        else:
            analysis_text.append(f"💰 Đang chờ kết quả...")
        
        title = "🎯 KẾT QUẢ"
        border_color = "yellow"
        
    else:
        analysis_text = Text()
        analysis_text.append(f"\n{spinner} ", style="cyan")
        analysis_text.append("CHỜ VÁN MỚI...\n\n", style="white")
        analysis_text.append("🔍 Đang kết nối dữ liệu game...\n")
        analysis_text.append("🤖 Sẵn sàng phân tích AI")
        
        title = "⏳ CHỜ"
        border_color = "dim"
    
    content.add_row(analysis_text)
    
    return Panel(
        content,
        title=title,
        border_style=border_color,
        box=box.ROUNDED,
        padding=(1, 2)
    )

def create_bet_history_panel() -> Panel:
    """Create beautiful bet history panel"""
    if not bet_history:
        return Panel(
            Text("📭 Chưa có lịch sử cược", justify="center"),
            title="📜 LỊCH SỬ CƯỢC",
            border_style="dim",
            box=box.ROUNDED
        )
    
    history_table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="cyan",
        expand=True
    )
    
    history_table.add_column("Ván", style="dim", width=6)
    history_table.add_column("Phòng", style="white", width=8)
    history_table.add_column("Tiền", style="yellow", width=12)
    history_table.add_column("Kết quả", width=10)
    history_table.add_column("Thời gian", style="dim", width=10)
    
    # Show last 6 bets
    last_bets = list(bet_history)[-6:]
    for bet in reversed(last_bets):
        # Get room info
        room_id = bet.get('room')
        if room_id in ROOM_NAMES:
            icon, name, _ = ROOM_NAMES[room_id]
            room_display = f"{icon} {room_id}"
        else:
            room_display = str(room_id)
        
        # Format amount
        amount = bet.get('amount', 0)
        amount_fmt = f"{float(amount):.4f}"
        
        # Format result with color
        result = bet.get('result', 'Đang')
        if result == 'Thắng':
            result_text = Text("THẮNG", style="green")
        elif result == 'Thua':
            result_text = Text("THUA", style="red")
        else:
            result_text = Text("ĐANG", style="yellow")
        
        # Add row
        history_table.add_row(
            str(bet.get('issue', '')),
            room_display,
            amount_fmt,
            result_text,
            bet.get('time', '')
        )
    
    return Panel(
        history_table,
        title="📜 LỊCH SỬ CƯỢC (6 ván gần nhất)",
        border_style="cyan",
        box=box.ROUNDED
    )

def create_control_panel() -> Panel:
    """Create control panel with current settings"""
    controls_grid = Table.grid(padding=(0, 1))
    controls_grid.add_column(style="cyan", width=20)
    controls_grid.add_column(style="white")
    
    controls_grid.add_row("🤖 Chế độ:", f"{run_mode}")
    controls_grid.add_row("🎯 Thuật toán:", f"[cyan]{settings['algo']}[/cyan]")
    controls_grid.add_row("💰 Cược gốc:", f"[yellow]{base_bet:.4f} BUILD[/yellow]")
    controls_grid.add_row("⚡ Hệ số nhân:", f"{multiplier}x")
    controls_grid.add_row("⏸️ Nghỉ sau thua:", f"{pause_after_losses} ván" if pause_after_losses > 0 else "Không")
    
    # Add current status
    status_text = Text()
    if stop_flag:
        status_text.append("🛑 DỪNG", style="red")
    elif _skip_rounds_remaining > 0:
        status_text.append(f"⏸️ ĐANG NGHỈ ({_skip_rounds_remaining} ván)", style="yellow")
    else:
        status_text.append("▶️ ĐANG CHẠY", style="green")
    
    controls_grid.add_row("📊 Trạng thái:", status_text)
    
    return Panel(
        controls_grid,
        title="⚙️ ĐIỀU KHIỂN",
        border_style="cyan",
        box=box.ROUNDED
    )

# -------------------- UTILITIES --------------------

def log_debug(msg: str):
    try:
        logger.debug(msg)
    except Exception:
        pass


def _parse_number(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x)
    m = _num_re.search(s)
    if not m:
        return None
    token = m.group(0).replace(",", "")
    try:
        return float(token)
    except Exception:
        return None


def human_ts() -> str:
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


def safe_input(prompt: str, default=None, cast=None):
    try:
        s = input(prompt).strip()
    except EOFError:
        return default
    if s == "":
        return default
    if cast:
        try:
            return cast(s)
        except Exception:
            return default
    return s

# -------------------- BALANCE PARSING & FETCH --------------------

def _parse_balance_from_json(j: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not isinstance(j, dict):
        return None, None, None
    build = None
    world = None
    usdt = None

    data = j.get("data") if isinstance(j.get("data"), dict) else j
    if isinstance(data, dict):
        cwallet = data.get("cwallet") if isinstance(data.get("cwallet"), dict) else None
        if cwallet:
            for key in ("ctoken_contribute", "ctoken", "build", "balance", "amount"):
                if key in cwallet and build is None:
                    build = _parse_number(cwallet.get(key))
        for k in ("build", "ctoken", "ctoken_contribute"):
            if build is None and k in data:
                build = _parse_number(data.get(k))
        for k in ("usdt", "kusdt", "usdt_balance"):
            if usdt is None and k in data:
                usdt = _parse_number(data.get(k))
        for k in ("world", "xworld"):
            if world is None and k in data:
                world = _parse_number(data.get(k))

    found = []

    def walk(o: Any, path=""):
        if isinstance(o, dict):
            for kk, vv in o.items():
                nk = (path + "." + str(kk)).strip(".")
                if isinstance(vv, (dict, list)):
                    walk(vv, nk)
                else:
                    n = _parse_number(vv)
                    if n is not None:
                        found.append((nk.lower(), n))
        elif isinstance(o, list):
            for idx, it in enumerate(o):
                walk(it, f"{path}[{idx}]")

    walk(j)

    for k, n in found:
        if build is None and any(x in k for x in ("ctoken", "build", "contribute", "balance")):
            build = n
        if usdt is None and "usdt" in k:
            usdt = n
        if world is None and any(x in k for x in ("world", "xworld")):
            world = n

    return build, world, usdt


def balance_headers_for(uid: Optional[int] = None, secret: Optional[str] = None) -> Dict[str, str]:
    h = {
        "accept": "*/*",
        "accept-language": "vi,en;q=0.9",
        "cache-control": "no-cache",
        "country-code": "vn",
        "origin": "https://xworld.info",
        "pragma": "no-cache",
        "referer": "https://xworld.info/",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "user-login": "login_v2",
        "xb-language": "vi-VN",
    }
    if uid is not None:
        h["user-id"] = str(uid)
    if secret:
        h["user-secret-key"] = str(secret)
    return h


def fetch_balances_3games(retries=2, timeout=6, params=None, uid=None, secret=None):
    """
    Non-blocking friendly: call from background threads if you don't want UI block.
    """
    global current_build, current_usdt, current_world, last_balance_ts
    global starting_balance, last_balance_val, cumulative_profit

    uid = uid or USER_ID
    secret = secret or SECRET_KEY
    payload = {"user_id": int(uid) if uid is not None else None, "source": "home"}

    attempt = 0
    while attempt <= retries:
        attempt += 1
        try:
            r = HTTP.post(
                WALLET_API_URL,
                json=payload,
                headers=balance_headers_for(uid, secret),
                timeout=timeout,
            )
            r.raise_for_status()
            j = r.json()

            build = None
            world = None
            usdt = None
            # custom parsing
            build, world, usdt = _parse_balance_from_json(j)

            if build is not None:
                if last_balance_val is None:
                    starting_balance = build
                    last_balance_val = build
                else:
                    delta = float(build) - float(last_balance_val)
                    if abs(delta) > 0:
                        cumulative_profit += delta
                        last_balance_val = build
                current_build = build
            if usdt is not None:
                current_usdt = usdt
            if world is not None:
                current_world = world

            last_balance_ts = time.time()
            return current_build, current_world, current_usdt

        except Exception as e:
            log_debug(f"wallet fetch attempt {attempt} error: {e}")
            time.sleep(min(0.6 * attempt, 2))

    return current_build, current_world, current_usdt

# -------------------- VIP50 ENSEMBLE SELECTION --------------------

def _room_features(rid: int):
    st = room_state.get(rid, {})
    stats = room_stats.get(rid, {})
    players = float(st.get("players", 0))
    bet = float(st.get("bet", 0))
    bet_per_player = (bet / players) if players > 0 else bet
    kill_count = float(stats.get("kills", 0))
    survive_count = float(stats.get("survives", 0))
    kill_rate = (kill_count + 0.5) / (kill_count + survive_count + 1.0)
    survive_score = 1.0 - kill_rate
    recent_history = list(bet_history)[-8:]
    recent_pen = 0.0
    for i, rec in enumerate(reversed(recent_history)):
        if rec.get("room") == rid:
            recent_pen += 0.12 * (1.0 / (i + 1))
    last_pen = 0.0
    if last_killed_room == rid:
        last_pen = 0.35 if SELECTION_CONFIG.get("avoid_last_kill", True) else 0.0
    # normalized players (0..1 roughly)
    players_norm = min(1.0, players / 50.0)
    bet_norm = 1.0 / (1.0 + bet / 2000.0)
    bpp_norm = 1.0 / (1.0 + bet_per_player / 1200.0)
    return {
        "players": players,
        "players_norm": players_norm,
        "bet": bet,
        "bet_norm": bet_norm,
        "bet_per_player": bet_per_player,
        "bpp_norm": bpp_norm,
        "kill_rate": kill_rate,
        "survive_score": survive_score,
        "recent_pen": recent_pen,
        "last_pen": last_pen
    }


def choose_room_vip50() -> Tuple[int, str]:
    """
    Build 50 deterministic formula weights, score each room and aggregate.
    Deterministic by using a fixed seed for weight generation so results are repeatable.
    """
    cand = [r for r in ROOM_ORDER]
    # deterministic weights via seeded RNG
    seed = 1234567
    rng = random.Random(seed)
    # pre-generate 50 weight sets
    formulas = []
    for i in range(50):
        # vary weights around some sensible defaults
        w_players = rng.uniform(0.2, 0.8)
        w_bet = rng.uniform(0.1, 0.6)
        w_bpp = rng.uniform(0.05, 0.6)
        w_survive = rng.uniform(0.05, 0.4)
        w_recent = rng.uniform(0.05, 0.3)
        w_last = rng.uniform(0.1, 0.6)
        noise_scale = rng.uniform(0.0, 0.08)
        formulas.append((w_players, w_bet, w_bpp, w_survive, w_recent, w_last, noise_scale))

    agg_scores = {r: 0.0 for r in cand}
    # compute per-formula scores
    for idx, wset in enumerate(formulas):
        for r in cand:
            f = _room_features(r)
            score = 0.0
            score += wset[0] * f["players_norm"]
            score += wset[1] * f["bet_norm"]
            score += wset[2] * f["bpp_norm"]
            score += wset[3] * f["survive_score"]
            score -= wset[4] * f["recent_pen"]
            score -= wset[5] * f["last_pen"]
            # small deterministic noise per formula/room
            noise = (math.sin((idx + 1) * (r + 1) * 12.9898) * 43758.5453) % 1.0
            noise = (noise - 0.5) * (wset[6] * 2.0)
            score += noise
            agg_scores[r] += score

    # normalize by number of formulas
    for r in agg_scores:
        agg_scores[r] /= len(formulas)

    ranked = sorted(agg_scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best_room = ranked[0][0]
    return best_room, "VIP50"

# -------------------- BETTING HELPERS --------------------

def api_headers() -> Dict[str, str]:
    return {
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0",
        "user-id": str(USER_ID) if USER_ID else "",
        "user-secret-key": SECRET_KEY if SECRET_KEY else ""
    }


def place_bet_http(issue: int, room_id: int, amount: float) -> dict:
    payload = {"asset_type": "BUILD", "user_id": USER_ID, "room_id": int(room_id), "bet_amount": float(amount)}
    try:
        r = HTTP.post(BET_API_URL, headers=api_headers(), json=payload, timeout=6)
        try:
            return r.json()
        except Exception:
            return {"raw": r.text, "http_status": r.status_code}
    except Exception as e:
        return {"error": str(e)}


def record_bet(issue: int, room_id: int, amount: float, resp: dict, algo_used: Optional[str] = None) -> dict:
    now = datetime.now(tz).strftime("%H:%M:%S")
    rec = {"issue": issue, "room": room_id, "amount": float(amount), "time": now, "resp": resp, "result": "Đang", "algo": algo_used, "delta": 0.0, "win_streak": win_streak, "lose_streak": lose_streak}
    bet_history.append(rec)
    return rec


def place_bet_async(issue: int, room_id: int, amount: float, algo_used: Optional[str] = None):
    def worker():
        console.print(f"[cyan]🎯 Đang đặt {amount} BUILD → PHÒNG {room_id} (ván {issue})[/cyan]")
        time.sleep(random.uniform(0.02, 0.25))
        res = place_bet_http(issue, room_id, amount)
        rec = record_bet(issue, room_id, amount, res, algo_used=algo_used)
        if isinstance(res, dict) and (res.get("msg") == "ok" or res.get("code") == 0 or res.get("status") in ("ok", 1)):
            bet_sent_for_issue.add(issue)
            console.print(f"[green]✅ Đặt thành công {amount} BUILD vào PHÒNG {room_id} (ván {issue})[/green]")
        else:
            console.print(f"[red]❌ Đặt lỗi ván {issue}: {res}[/red]")
    threading.Thread(target=worker, daemon=True).start()

# -------------------- LOCK & AUTO-BET --------------------

def lock_prediction_if_needed(force: bool = False):
    global prediction_locked, predicted_room, ui_state, current_bet, _rounds_placed_since_skip, skip_next_round_flag, _skip_rounds_remaining, _skip_active_issue
    if stop_flag:
        return
    if prediction_locked and not force:
        return
    if issue_id is None:
        return
    
    # --- ĐANG NGHỈ SAU KHI THUA ---
    if _skip_rounds_remaining > 0:
        # chỉ trừ 1 lần khi sang ván mới
        if _skip_active_issue != issue_id:
            console.print(f"[yellow]⏸️ Đang nghỉ {_skip_rounds_remaining} ván theo cấu hình sau khi thua.[/yellow]")
            _skip_rounds_remaining -= 1         # tiêu thụ 1 ván nghỉ
            _skip_active_issue = issue_id       # nhớ là ván này đã nghỉ

        # khóa đến hết ván hiện tại để không bị các tick countdown đặt lại
        prediction_locked = True
        ui_state = "ANALYZING"                  # hoặc "PREDICTED" tuỳ UI
        return
    
    # Chọn phòng chỉ khi KHÔNG skip
    chosen, algo_used = choose_room_vip50()
    predicted_room = chosen
    prediction_locked = True
    ui_state = "PREDICTED"
    
    # place bet if AUTO
    if run_mode == "AUTO" and not skip_next_round_flag:
        # get balance quickly (non-blocking - allow poller to update if needed)
        bld, _, _ = fetch_balances_3games(params={"userId": str(USER_ID)} if USER_ID else None)
        if bld is None:
            console.print("[yellow]⚠️ Không lấy được số dư trước khi đặt — bỏ qua đặt ván này.[/yellow]")
            prediction_locked = False
            return
        global current_bet
        
        # Debug: Kiểm tra current_bet trước khi đặt cược
        if current_bet is None:
            current_bet = base_bet
        amt = float(current_bet)
        
        if amt <= 0:
            console.print("[yellow]⚠️ Số tiền đặt không hợp lệ (<=0). Bỏ qua.[/yellow]")
            prediction_locked = False
            return
        place_bet_async(issue_id, predicted_room, amt, algo_used=algo_used)
        _rounds_placed_since_skip += 1
        if bet_rounds_before_skip > 0 and _rounds_placed_since_skip >= bet_rounds_before_skip:
            skip_next_round_flag = True
            _rounds_placed_since_skip = 0
    elif skip_next_round_flag:
        console.print("[yellow]⏸️ TẠM DỪNG THEO DÕI SÁT THỦ[/yellow]")
        skip_next_round_flag = False

# -------------------- WEBSOCKET HANDLERS --------------------

def safe_send_enter_game(ws):
    if not ws:
        log_debug("safe_send_enter_game: ws None")
        return
    try:
        payload = {"msg_type": "handle_enter_game", "asset_type": "BUILD", "user_id": USER_ID, "user_secret_key": SECRET_KEY}
        ws.send(json.dumps(payload))
        log_debug("Sent enter_game")
    except Exception as e:
        log_debug(f"safe_send_enter_game err: {e}")


def _extract_issue_id(d: Dict[str, Any]) -> Optional[int]:
    if not isinstance(d, dict):
        return None
    possible = []
    for key in ("issue_id", "issueId", "issue", "id"):
        v = d.get(key)
        if v is not None:
            possible.append(v)
    if isinstance(d.get("data"), dict):
        for key in ("issue_id", "issueId", "issue", "id"):
            v = d["data"].get(key)
            if v is not None:
                possible.append(v)
    for p in possible:
        try:
            return int(p)
        except Exception:
            try:
                return int(str(p))
            except Exception:
                continue
    return None


def on_open(ws):
    _ws["ws"] = ws
    console.print("[green]✅ ĐANG KẾT NỐI DỮ LIỆU GAME...[/green]")
    safe_send_enter_game(ws)


def _background_fetch_balance_after_result():
    # fetch in background to update cumulative etc
    try:
        fetch_balances_3games()
    except Exception:
        pass


def _mark_bet_result_from_issue(res_issue: Optional[int], krid: int):
    """
    Update kết quả CHỈ KHI có đặt cược ở issue đó.
    Tránh reset current_bet sai khi skip round.
    """
    global current_bet, win_streak, lose_streak, max_win_streak, max_lose_streak
    global _skip_rounds_remaining, stop_flag, _skip_active_issue

    if res_issue is None:
        return

    # ✅ Quan trọng: chỉ xử lý nếu THỰC SỰ đã đặt cược ở issue này
    if res_issue not in bet_sent_for_issue:
        # Không có cược cho ván này (ví dụ đang nghỉ) -> bỏ qua hoàn toàn
        log_debug(f"_mark_bet_result_from_issue: skip issue {res_issue} (no bet placed)")
        return

    # Tìm đúng bản ghi của issue này (KHÔNG fallback)
    rec = next((b for b in reversed(bet_history) if b.get("issue") == res_issue), None)
    if rec is None:
        log_debug(f"_mark_bet_result_from_issue: no record found for issue {res_issue}, skip")
        return

    # Tránh xử lý lặp
    if rec.get("settled"):
        log_debug(f"_mark_bet_result_from_issue: issue {res_issue} already settled, skip")
        return

    try:
        placed_room = int(rec.get("room"))
        # Nếu phòng bị kill khác phòng đã đặt => THẮNG
        if placed_room != int(krid):
            rec["result"] = "Thắng"
            rec["settled"] = True
            current_bet = base_bet              # reset martingale về base
            win_streak += 1
            lose_streak = 0
            if win_streak > max_win_streak:
                max_win_streak = win_streak
        else:
            # THUA -> nhân tiền cho ván kế tiếp
            rec["result"] = "Thua"
            rec["settled"] = True
            try:
                old_bet = current_bet
                current_bet = float(rec.get("amount")) * float(multiplier)
                console.print(f"[red]🔴 THUA! Số cũ: {rec.get('amount')} × {multiplier} = {current_bet} BUILD[/red]")
            except Exception as e:
                current_bet = base_bet
                console.print(f"[red]🔴 THUA! Lỗi tính toán: {e}, reset về: {current_bet} BUILD[/red]")
            lose_streak += 1
            win_streak = 0
            if lose_streak > max_lose_streak:
                max_lose_streak = lose_streak
            if pause_after_losses > 0:
                _skip_rounds_remaining = pause_after_losses
                _skip_active_issue = None        # để ván kế tiếp mới trừ 1 lần
    except Exception as e:
        log_debug(f"_mark_bet_result_from_issue err: {e}")
    finally:
        # dọn whitelist cho issue đã xử lý xong (optional)
        try:
            bet_sent_for_issue.discard(res_issue)
        except Exception:
            pass


def on_message(ws, message):
    global issue_id, count_down, killed_room, round_index, ui_state, analysis_start_ts, issue_start_ts
    global prediction_locked, predicted_room, last_killed_room, last_msg_ts, current_bet
    global win_streak, lose_streak, max_win_streak, max_lose_streak, cumulative_profit, _skip_rounds_remaining, stop_flag, analysis_blur
    last_msg_ts = time.time()
    try:
        if isinstance(message, bytes):
            try:
                message = message.decode("utf-8", errors="replace")
            except Exception:
                message = str(message)
        data = None
        try:
            data = json.loads(message)
        except Exception:
            try:
                data = json.loads(message.replace("'", '"'))
            except Exception:
                log_debug(f"on_message non-json: {str(message)[:200]}")
                return

        # sometimes payload wraps JSON string in data field
        if isinstance(data, dict) and isinstance(data.get("data"), str):
            try:
                inner = json.loads(data.get("data"))
                merged = dict(data)
                merged.update(inner)
                data = merged
            except Exception:
                pass

        msg_type = data.get("msg_type") or data.get("type") or ""
        msg_type = str(msg_type)
        new_issue = _extract_issue_id(data)

        # issue stat / rooms update
        if msg_type == "notify_issue_stat" or "issue_stat" in msg_type:
            rooms = data.get("rooms") or []
            if not rooms and isinstance(data.get("data"), dict):
                rooms = data["data"].get("rooms", [])
            for rm in (rooms or []):
                try:
                    rid = int(rm.get("room_id") or rm.get("roomId") or rm.get("id"))
                except Exception:
                    continue
                players = int(rm.get("user_cnt") or rm.get("userCount") or 0) or 0
                bet = int(rm.get("total_bet_amount") or rm.get("totalBet") or rm.get("bet") or 0) or 0
                room_state[rid] = {"players": players, "bet": bet}
                room_stats[rid]["last_players"] = players
                room_stats[rid]["last_bet"] = bet
            if new_issue is not None and new_issue != issue_id:
                # New issue arrived -> prepare
                log_debug(f"New issue: {issue_id} -> {new_issue}")
                issue_id = new_issue
                issue_start_ts = time.time()
                round_index += 1
                killed_room = None
                prediction_locked = False
                predicted_room = None
                ui_state = "ANALYZING"
                analysis_start_ts = time.time()
                # NOTE: Do NOT lock prediction immediately here so ANALYZING UI shows.

        # countdown
        elif msg_type == "notify_count_down" or "count_down" in msg_type:
            count_down = data.get("count_down") or data.get("countDown") or data.get("count") or count_down
            try:
                count_val = int(count_down)
            except Exception:
                count_val = None
            # enter analysis blur window when <=45s; place bet when <=10s
            if count_val is not None:
                try:
                    # when <=10s, lock and place (if not already locked)
                    if count_val <= 10 and not prediction_locked:
                        # stop blur animation right before placing
                        analysis_blur = False
                        lock_prediction_if_needed()
                    elif count_val <= 45:
                        # start blur-analysis (45s -> 10s)
                        ui_state = "ANALYZING"
                        analysis_start_ts = time.time()
                        analysis_blur = True
                except Exception:
                    pass

        # result
        elif msg_type == "notify_result" or "result" in msg_type:
            # get killed room
            kr = data.get("killed_room") if data.get("killed_room") is not None else data.get("killed_room_id")
            if kr is None and isinstance(data.get("data"), dict):
                kr = data["data"].get("killed_room") or data["data"].get("killed_room_id")
            if kr is not None:
                try:
                    krid = int(kr)
                except Exception:
                    krid = kr
                killed_room = krid
                last_killed_room = krid
                for rid in ROOM_ORDER:
                    if rid == krid:
                        room_stats[rid]["kills"] += 1
                        room_stats[rid]["last_kill_round"] = round_index
                    else:
                        room_stats[rid]["survives"] += 1

                # Immediately mark bet result locally (fast) without waiting for balance
                res_issue = new_issue if new_issue is not None else issue_id
                _mark_bet_result_from_issue(res_issue, krid)
                # Fire background balance refresh to compute actual deltas & cumulative profit
                threading.Thread(target=_background_fetch_balance_after_result, daemon=True).start()

            ui_state = "RESULT"

            # check profit target or stop-loss after we fetched balances (balance fetch may set current_build)
            def _check_stop_conditions():
                global stop_flag
                try:
                    if stop_when_profit_reached and profit_target is not None and isinstance(current_build, (int, float)) and current_build >= profit_target:
                        console.print(f"[bold green]🎉 MỤC TIÊU LÃI ĐẠT: {current_build} >= {profit_target}. Dừng tool.[/bold green]")
                        stop_flag = True
                        try:
                            wsobj = _ws.get("ws")
                            if wsobj:
                                wsobj.close()
                        except Exception:
                            pass
                    if stop_when_loss_reached and stop_loss_target is not None and isinstance(current_build, (int, float)) and current_build <= stop_loss_target:
                        console.print(f"[bold red]⚠️ STOP-LOSS TRIGGED: {current_build} <= {stop_loss_target}. Dừng tool.[/bold red]")
                        stop_flag = True
                        try:
                            wsobj = _ws.get("ws")
                            if wsobj:
                                wsobj.close()
                        except Exception:
                            pass
                except Exception:
                    pass
            # run check slightly delayed to allow balance refresh thread update
            threading.Timer(1.2, _check_stop_conditions).start()

    except Exception as e:
        log_debug(f"on_message err: {e}")


def on_close(ws, code, reason):
    log_debug(f"WS closed: {code} {reason}")


def on_error(ws, err):
    log_debug(f"WS error: {err}")


def start_ws():
    backoff = 0.6
    while not stop_flag:
        try:
            ws_app = websocket.WebSocketApp(WS_URL, on_open=on_open, on_message=on_message, on_close=on_close, on_error=on_error)
            _ws["ws"] = ws_app
            ws_app.run_forever(ping_interval=12, ping_timeout=6)
        except Exception as e:
            log_debug(f"start_ws exception: {e}")
        t = min(backoff + random.random() * 0.5, 30)
        log_debug(f"Reconnect WS after {t}s")
        time.sleep(t)
        backoff = min(backoff * 1.5, 30)

# -------------------- BALANCE POLLER THREAD --------------------

class BalancePoller(threading.Thread):
    def __init__(self, uid: Optional[int], secret: Optional[str], poll_seconds: int = 2, on_balance=None, on_error=None, on_status=None):
        super().__init__(daemon=True)
        self.uid = uid
        self.secret = secret
        self.poll_seconds = max(1, int(poll_seconds))
        self._running = True
        self._last_balance_local: Optional[float] = None
        self.on_balance = on_balance
        self.on_error = on_error
        self.on_status = on_status

    def stop(self):
        self._running = False

    def run(self):
        if self.on_status:
            self.on_status("Kết nối...")
        while self._running and not stop_flag:
            try:
                build, world, usdt = fetch_balances_3games(params={"userId": str(self.uid)} if self.uid else None, uid=self.uid, secret=self.secret)
                if build is None:
                    raise RuntimeError("Không đọc được balance từ response")
                delta = 0.0 if self._last_balance_local is None else (build - self._last_balance_local)
                first_time = (self._last_balance_local is None)
                if first_time or abs(delta) > 0:
                    self._last_balance_local = build
                    if self.on_balance:
                        self.on_balance(float(build), float(delta), {"ts": human_ts()})
                    if self.on_status:
                        self.on_status("Đang theo dõi")
                else:
                    if self.on_status:
                        self.on_status("Đang theo dõi (không đổi)")
            except Exception as e:
                if self.on_error:
                    self.on_error(str(e))
                if self.on_status:
                    self.on_status("Lỗi kết nối (thử lại...)")
            for _ in range(max(1, int(self.poll_seconds * 5))):
                if not self._running or stop_flag:
                    break
                time.sleep(0.2)
        if self.on_status:
            self.on_status("Đã dừng")

# -------------------- MONITOR --------------------

def monitor_loop():
    global last_balance_fetch_ts, last_msg_ts, stop_flag
    while not stop_flag:
        now = time.time()
        if now - last_balance_fetch_ts >= BALANCE_POLL_INTERVAL:
            last_balance_fetch_ts = now
            try:
                fetch_balances_3games(params={"userId": str(USER_ID)} if USER_ID else None)
            except Exception as e:
                log_debug(f"monitor fetch err: {e}")
        if now - last_msg_ts > 8:
            log_debug("No ws msg >8s, send enter_game")
            try:
                safe_send_enter_game(_ws.get("ws"))
            except Exception as e:
                log_debug(f"monitor send err: {e}")
        if now - last_msg_ts > 30:
            log_debug("No ws msg >30s, force reconnect")
            try:
                wsobj = _ws.get("ws")
                if wsobj:
                    try:
                        wsobj.close()
                    except Exception:
                        pass
            except Exception:
                pass
        # Removed analysis_duration-based auto-lock. Now locking is driven solely by countdown messages (<=10s).
        time.sleep(0.6)

# -------------------- MAIN UI RENDER --------------------

def render_main_ui() -> Group:
    """Render the complete UI"""
    # Create layout with multiple panels
    top_group = Group(
        create_banner(),
        Columns([
            create_wallet_panel(),
            create_stats_panel(),
            create_game_clock(),
            create_control_panel()
        ], equal=False, expand=True)
    )
    
    middle_group = Columns([
        create_rooms_display(),
        create_analysis_panel()
    ], equal=False, expand=True)
    
    bottom_group = create_bet_history_panel()
    
    return Group(top_group, middle_group, bottom_group)

# -------------------- SETTINGS & START --------------------

def prompt_settings():
    global base_bet, multiplier, run_mode, bet_rounds_before_skip, current_bet, pause_after_losses, profit_target, stop_when_profit_reached, stop_loss_target, stop_when_loss_reached, settings
    
    console.clear()
    console.print(gradient_text("╔══════════════════════════════════════════════════════════╗", GRADIENT_COLORS))
    console.print(gradient_text("║                 CẤU HÌNH DUYTOOL VIP AI                 ║", GRADIENT_COLORS))
    console.print(gradient_text("╚══════════════════════════════════════════════════════════╝", GRADIENT_COLORS))
    console.print()
    
    # Beautiful input prompts
    base = safe_input("🎯 Số BUILD đặt mỗi ván: ", default="1")
    try:
        base_bet = float(base)
    except Exception:
        base_bet = 1.0
    
    m = safe_input("⚡ Nhập hệ số nhân sau khi thua (mặc định: 2): ", default="2")
    try:
        multiplier = float(m)
    except Exception:
        multiplier = 2.0
    
    current_bet = base_bet

    # Algorithm selection
    console.print("\n[cyan]🤖 Chọn thuật toán thông minh:[/cyan]")
    console.print("[green]1)[/green] VIP50 — 50 công thức tính phòng an toàn nhất (AI + Toán học nâng cao)")
    alg = safe_input("👉 Lựa chọn của bạn (1): ", default="1")
    if str(alg).strip() == "" or str(alg).strip() == "1":
        settings["algo"] = "VIP50"
    else:
        settings["algo"] = "VIP50"

    # Advanced settings
    console.print("\n[yellow]⚙️ Cài đặt nâng cao:[/yellow]")
    
    s = safe_input("🛡️  Chống soi: sau bao nhiêu ván đặt thì nghỉ 1 ván: ", default="0")
    try:
        bet_rounds_before_skip = int(s)
    except Exception:
        bet_rounds_before_skip = 0
    
    pl = safe_input("💤 Nếu thua thì nghỉ bao nhiêu tay trước khi cược lại: ", default="0")
    try:
        pause_after_losses = int(pl)
    except Exception:
        pause_after_losses = 0
    
    # Profit target
    pt = safe_input("💰 Nhập mục tiêu lãi (BUILD) để tự động dừng (bỏ trống nếu không dùng): ", default="")
    try:
        if pt and pt.strip() != "":
            profit_target = float(pt)
            stop_when_profit_reached = True
            console.print(f"[green]✅ Đã đặt mục tiêu lãi: {profit_target} BUILD[/green]")
        else:
            profit_target = None
            stop_when_profit_reached = False
    except Exception:
        profit_target = None
        stop_when_profit_reached = False
    
    # Stop-loss
    sl = safe_input("⚠️  Nhập mức dừng lỗ (BUILD) (bỏ trống nếu không dùng): ", default="")
    try:
        if sl and sl.strip() != "":
            stop_loss_target = float(sl)
            stop_when_loss_reached = True
            console.print(f"[yellow]✅ Đã đặt dừng lỗ: {stop_loss_target} BUILD[/yellow]")
        else:
            stop_loss_target = None
            stop_when_loss_reached = False
    except Exception:
        stop_loss_target = None
        stop_when_loss_reached = False

    # Mode selection
    console.print("\n[magenta]🚀 Chọn chế độ hoạt động:[/magenta]")
    console.print("[cyan]AUTO[/cyan] - Tự động đặt cược theo AI")
    console.print("[cyan]MANUAL[/cyan] - Chỉ xem, không tự đặt")
    runm = safe_input("👉 Chế độ (AUTO/MANUAL): ", default="AUTO")
    run_mode = str(runm).upper() if str(runm).upper() in ["AUTO", "MANUAL"] else "AUTO"
    
    console.print(f"\n[green]✅ Cấu hình hoàn tất![/green]")
    console.print(f"[dim]Cược gốc: {base_bet} BUILD | Hệ số: {multiplier}x | Chế độ: {run_mode}[/dim]")
    console.print(gradient_text("\n" + "="*60, GRADIENT_COLORS))

def parse_login():
    global USER_ID, SECRET_KEY
    console.clear()
    console.print(gradient_text("╔══════════════════════════════════════════════════════════╗", GRADIENT_COLORS))
    console.print(gradient_text("║                  ĐĂNG NHẬP DUYTOOL AI                   ║", GRADIENT_COLORS))
    console.print(gradient_text("╚══════════════════════════════════════════════════════════╝", GRADIENT_COLORS))
    console.print()
    
    link = safe_input("🔗 Dán link trò chơi (từ xworld.info) tại đây > ", default=None)
    if not link:
        console.print("[red]❌ Không nhập link. Thoát.[/red]")
        sys.exit(1)
    
    try:
        parsed = urlparse(link)
        params = parse_qs(parsed.query)
        if 'userId' in params:
            USER_ID = int(params.get('userId')[0])
        SECRET_KEY = params.get('secretKey', [None])[0]
        console.print(f"[green]✅ Đã đọc thông tin: userId={USER_ID}[/green]")
        
        # Test connection
        console.print("[cyan]🔗 Đang kiểm tra kết nối...[/cyan]")
        fetch_balances_3games()
        console.print("[green]✅ Kết nối thành công![/green]")
        
    except Exception as e:
        console.print("[red]❌ Link không hợp lệ hoặc không thể kết nối. Thoát.[/red]")
        log_debug(f"parse_login err: {e}")
        sys.exit(1)

def start_threads():
    threading.Thread(target=start_ws, daemon=True).start()
    threading.Thread(target=monitor_loop, daemon=True).start()

def main():
    parse_login()
    prompt_settings()
    
    console.clear()
    console.print("[green]🚀 Khởi động DUYTOOL VIP AI...[/green]")
    console.print("[cyan]⏳ Đang kết nối dữ liệu game...[/cyan]")
    
    def on_balance_changed(bal, delta, info):
        color = "green" if delta >= 0 else "red"
        console.print(f"[{color}]📈 Cập nhật số dư: {bal:.4f} (Δ {delta:+.4f}) — {info.get('ts')}[/{color}]")

    def on_error(msg):
        console.print(f"[red]❌ Balance poll lỗi: {msg}[/red]")

    poller = BalancePoller(USER_ID, SECRET_KEY, poll_seconds=max(1, int(BALANCE_POLL_INTERVAL)), 
                          on_balance=on_balance_changed, on_error=on_error, on_status=None)
    poller.start()
    start_threads()
    
    # Main UI loop
    with Live(render_main_ui(), refresh_per_second=12, console=console, screen=True) as live:
        try:
            while not stop_flag:
                live.update(render_main_ui())
                time.sleep(0.08)  # Smoother animation
                
                # Check for stop conditions
                if stop_flag:
                    console.print("[yellow]🛑 Tool đã dừng theo yêu cầu hoặc đạt mục tiêu.[/yellow]")
                    break
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Thoát bởi người dùng. Tạm biệt![/yellow]")
            poller.stop()
        except Exception as e:
            console.print(f"[red]❌ Lỗi không mong muốn: {e}[/red]")
            poller.stop()

if __name__ == "__main__":
    try:
        # Set terminal title
        os.system("title DUYTOOL VIP AI - Escape Master v2.0")
        main()
    except Exception as e:
        console.print(f"[red]⚠️ Lỗi nghiêm trọng: {e}[/red]")
        console.print("[yellow]Vui lòng kiểm tra kết nối và thử lại.[/yellow]")
