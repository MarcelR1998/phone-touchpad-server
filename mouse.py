"""
Mouse & keyboard control helper — cross-platform (Linux X11, macOS, Windows).
Reads JSON commands from stdin, one per line.
"""
import ctypes
import ctypes.util
import json
import platform
import sys
import time

SYSTEM = platform.system()

# ---------------------------------------------------------------------------
# Platform backend interface:
#   init() -> (screen_width, screen_height)
#   get_pointer() -> (x, y)
#   move_pointer(x, y)
#   mouse_button(button, pressed)   button: 1=left,2=mid,3=right
#   scroll_event(direction)         "up" or "down"
#   key_event(keycode, pressed)
#   get_keycode(key_name) -> int
#   needs_shift(char) -> bool
# ---------------------------------------------------------------------------

# Friendly key name mapping (resolved per-platform below)
KEY_MAP = {}


# ========================== LINUX / X11 ====================================
if SYSTEM == "Linux":
    x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
    xtst = ctypes.cdll.LoadLibrary("libXtst.so.6")

    display = x11.XOpenDisplay(None)
    if not display:
        print("ERROR: Cannot open X display", file=sys.stderr)
        sys.exit(1)

    _screen = x11.XDefaultScreen(display)
    _root = x11.XDefaultRootWindow(display)

    # XTest argtypes
    xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeMotionEvent.restype = ctypes.c_int
    xtst.XTestFakeButtonEvent.restype = ctypes.c_int
    xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeKeyEvent.restype = ctypes.c_int

    x11.XWarpPointer.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
        ctypes.c_int, ctypes.c_int
    ]
    x11.XWarpPointer.restype = ctypes.c_int
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XKeysymToKeycode.restype = ctypes.c_ubyte
    x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
    x11.XStringToKeysym.restype = ctypes.c_ulong

    _root_ret = ctypes.c_ulong()
    _child_ret = ctypes.c_ulong()
    _rx = ctypes.c_int()
    _ry = ctypes.c_int()
    _wx = ctypes.c_int()
    _wy = ctypes.c_int()
    _mask = ctypes.c_uint()

    KEY_MAP = {
        "Backspace": "BackSpace", "Enter": "Return", "Space": "space",
        "Tab": "Tab", "Escape": "Escape", "Delete": "Delete",
        "Home": "Home", "End": "End",
        "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
        "Shift": "Shift_L", "Ctrl": "Control_L", "Alt": "Alt_L", "Super": "Super_L",
        "CapsLock": "Caps_Lock",
        "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
        "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
        "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",
    }

    def init():
        w = x11.XDisplayWidth(display, _screen)
        h = x11.XDisplayHeight(display, _screen)
        return w, h

    def get_pointer():
        x11.XQueryPointer(
            display, _root,
            ctypes.byref(_root_ret), ctypes.byref(_child_ret),
            ctypes.byref(_rx), ctypes.byref(_ry),
            ctypes.byref(_wx), ctypes.byref(_wy),
            ctypes.byref(_mask)
        )
        return _rx.value, _ry.value

    def move_pointer(x, y):
        x11.XWarpPointer(display, 0, _root, 0, 0, 0, 0, x, y)
        x11.XFlush(display)

    def mouse_button(button, pressed):
        xtst.XTestFakeButtonEvent(display, button, int(pressed), 0)
        x11.XFlush(display)

    def scroll_event(direction):
        btn = 4 if direction == "up" else 5
        xtst.XTestFakeButtonEvent(display, btn, 1, 0)
        xtst.XTestFakeButtonEvent(display, btn, 0, 0)
        x11.XFlush(display)

    def key_event(keycode, pressed):
        xtst.XTestFakeKeyEvent(display, keycode, int(pressed), 0)
        x11.XFlush(display)

    def get_keycode(key_name):
        ks = x11.XStringToKeysym(key_name.encode())
        if ks == 0:
            return None
        kc = x11.XKeysymToKeycode(display, ks)
        return kc if kc else None


# ========================== macOS / Quartz (ctypes) ========================
elif SYSTEM == "Darwin":
    # Use CoreGraphics via ctypes — no PyObjC / pip install needed.
    _cg = ctypes.cdll.LoadLibrary(
        "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
    )
    _cf = ctypes.cdll.LoadLibrary(
        "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
    )

    class CGPoint(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

    # --- CoreGraphics constants ---
    _kCGEventMouseMoved       = 5
    _kCGEventLeftMouseDown    = 1
    _kCGEventLeftMouseUp      = 2
    _kCGEventRightMouseDown   = 3
    _kCGEventRightMouseUp     = 4
    _kCGEventOtherMouseDown   = 25
    _kCGEventOtherMouseUp     = 26
    _kCGScrollEventUnitLine   = 1
    _kCGHIDEventTap           = 0

    # --- function signatures ---
    _cg.CGMainDisplayID.restype = ctypes.c_uint32

    _cg.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
    _cg.CGDisplayPixelsWide.restype  = ctypes.c_size_t
    _cg.CGDisplayPixelsHigh.argtypes = [ctypes.c_uint32]
    _cg.CGDisplayPixelsHigh.restype  = ctypes.c_size_t

    _cg.CGEventCreate.argtypes = [ctypes.c_void_p]
    _cg.CGEventCreate.restype  = ctypes.c_void_p

    _cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
    _cg.CGEventGetLocation.restype  = CGPoint

    _cg.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32,
    ]
    _cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p

    _cg.CGEventCreateKeyboardEvent.argtypes = [
        ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool,
    ]
    _cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p

    _cg.CGEventCreateScrollWheelEvent.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int32,
    ]
    _cg.CGEventCreateScrollWheelEvent.restype = ctypes.c_void_p

    _cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    _cg.CGEventPost.restype  = None

    _cf.CFRelease.argtypes = [ctypes.c_void_p]
    _cf.CFRelease.restype  = None

    # --- button map ---
    _mouse_button_map = {
        1: (0, _kCGEventLeftMouseDown,  _kCGEventLeftMouseUp),
        2: (2, _kCGEventOtherMouseDown, _kCGEventOtherMouseUp),
        3: (1, _kCGEventRightMouseDown, _kCGEventRightMouseUp),
    }

    # macOS virtual keycodes for common keys
    _MAC_KEY_MAP = {
        "Backspace": 51, "Enter": 36, "Space": 49, "Tab": 48,
        "Escape": 53, "Delete": 117, "Home": 115, "End": 119,
        "Up": 126, "Down": 125, "Left": 123, "Right": 124,
        "Shift": 56, "Ctrl": 59, "Alt": 58, "Super": 55,
        "CapsLock": 57,
        "F1": 122, "F2": 120, "F3": 99, "F4": 118,
        "F5": 96, "F6": 97, "F7": 98, "F8": 100,
        "F9": 101, "F10": 109, "F11": 103, "F12": 111,
    }

    # Map printable characters to macOS virtual keycodes (US keyboard layout)
    _MAC_CHAR_MAP = {
        'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3, 'g': 5,
        'h': 4, 'i': 34, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45,
        'o': 31, 'p': 35, 'q': 12, 'r': 15, 's': 1, 't': 17, 'u': 32,
        'v': 9, 'w': 13, 'x': 7, 'y': 16, 'z': 6,
        '0': 29, '1': 18, '2': 19, '3': 20, '4': 21,
        '5': 23, '6': 22, '7': 26, '8': 28, '9': 25,
        '-': 27, '=': 24, '[': 33, ']': 30, '\\': 42,
        ';': 41, "'": 39, ',': 43, '.': 47, '/': 44, '`': 50,
    }
    # Shifted characters map to the same keycodes as their base
    _MAC_SHIFTED = {
        '~': '`', '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
        '^': '6', '&': '7', '*': '8', '(': '9', ')': '0', '_': '-',
        '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'",
        '<': ',', '>': '.', '?': '/',
    }

    KEY_MAP = {}  # Not used on macOS — we use _MAC_KEY_MAP directly

    def init():
        d = _cg.CGMainDisplayID()
        return int(_cg.CGDisplayPixelsWide(d)), int(_cg.CGDisplayPixelsHigh(d))

    def get_pointer():
        ev = _cg.CGEventCreate(None)
        loc = _cg.CGEventGetLocation(ev)
        _cf.CFRelease(ev)
        return int(loc.x), int(loc.y)

    def move_pointer(x, y):
        ev = _cg.CGEventCreateMouseEvent(
            None, _kCGEventMouseMoved, CGPoint(x, y), 0
        )
        _cg.CGEventPost(_kCGHIDEventTap, ev)
        _cf.CFRelease(ev)

    def mouse_button(button, pressed):
        info = _mouse_button_map.get(button, _mouse_button_map[1])
        cg_button, down_type, up_type = info
        etype = down_type if pressed else up_type
        loc = get_pointer()
        ev = _cg.CGEventCreateMouseEvent(
            None, etype, CGPoint(loc[0], loc[1]), cg_button
        )
        _cg.CGEventPost(_kCGHIDEventTap, ev)
        _cf.CFRelease(ev)

    def scroll_event(direction):
        delta = 3 if direction == "up" else -3
        ev = _cg.CGEventCreateScrollWheelEvent(
            None, _kCGScrollEventUnitLine, 1, delta
        )
        _cg.CGEventPost(_kCGHIDEventTap, ev)
        _cf.CFRelease(ev)

    def key_event(keycode, pressed):
        ev = _cg.CGEventCreateKeyboardEvent(None, keycode, pressed)
        _cg.CGEventPost(_kCGHIDEventTap, ev)
        _cf.CFRelease(ev)

    def get_keycode(key_name):
        kc = _MAC_KEY_MAP.get(key_name)
        if kc is not None:
            return kc
        ch = key_name.lower()
        kc = _MAC_CHAR_MAP.get(ch)
        return kc


# ========================== Windows / Win32 ================================
elif SYSTEM == "Windows":
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1

    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000

    KEYEVENTF_KEYUP = 0x0002

    WHEEL_DELTA = 120

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("iu", INPUT_UNION)]

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    # Windows virtual key codes
    _WIN_KEY_MAP = {
        "Backspace": 0x08, "Enter": 0x0D, "Space": 0x20, "Tab": 0x09,
        "Escape": 0x1B, "Delete": 0x2E, "Home": 0x24, "End": 0x23,
        "Up": 0x26, "Down": 0x28, "Left": 0x25, "Right": 0x27,
        "Shift": 0x10, "Ctrl": 0x11, "Alt": 0x12, "Super": 0x5B,
        "CapsLock": 0x14,
        "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
        "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
        "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    }

    _WIN_BUTTON_MAP = {
        1: (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        2: (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
        3: (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    }

    KEY_MAP = {}  # Not used on Windows — we use _WIN_KEY_MAP directly

    def _send_input(inp):
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    def init():
        w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return w, h

    def get_pointer():
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def move_pointer(x, y):
        user32.SetCursorPos(x, y)

    def mouse_button(button, pressed):
        flags = _WIN_BUTTON_MAP.get(button, _WIN_BUTTON_MAP[1])
        flag = flags[0] if pressed else flags[1]
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.iu.mi.dwFlags = flag
        _send_input(inp)

    def scroll_event(direction):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.iu.mi.dwFlags = MOUSEEVENTF_WHEEL
        inp.iu.mi.mouseData = WHEEL_DELTA if direction == "up" else ctypes.c_ulong(-WHEEL_DELTA & 0xFFFFFFFF).value
        _send_input(inp)

    def key_event(keycode, pressed):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.iu.ki.wVk = keycode
        inp.iu.ki.dwFlags = 0 if pressed else KEYEVENTF_KEYUP
        _send_input(inp)

    def get_keycode(key_name):
        vk = _WIN_KEY_MAP.get(key_name)
        if vk is not None:
            return vk
        # For single characters, use VkKeyScan
        if len(key_name) == 1:
            result = user32.VkKeyScanW(ord(key_name))
            if result != -1:
                return result & 0xFF  # low byte is the VK code
        return None


else:
    print(f"ERROR: Unsupported platform: {SYSTEM}", file=sys.stderr)
    sys.exit(1)


# ===========================================================================
# Common / cross-platform logic
# ===========================================================================

SHIFTED_CHARS = '~!@#$%^&*()_+{}|:"<>?'


def needs_shift(char):
    return char.isupper() or char in SHIFTED_CHARS


def _get_shift_keycode():
    if SYSTEM == "Linux":
        return get_keycode("Shift_L")
    elif SYSTEM == "Darwin":
        return _MAC_KEY_MAP["Shift"]
    elif SYSTEM == "Windows":
        return _WIN_KEY_MAP["Shift"]


def _resolve_char_keycode(char):
    """Resolve a printable character to a keycode (platform-specific)."""
    if SYSTEM == "Linux":
        lookup = char.lower() if char.isupper() else char
        ks = x11.XStringToKeysym(lookup.encode())
        if ks == 0:
            ks = x11.XStringToKeysym(char.encode())
        if ks == 0:
            return None
        kc = x11.XKeysymToKeycode(display, ks)
        return kc if kc else None
    elif SYSTEM == "Darwin":
        base = _MAC_SHIFTED.get(char, char).lower()
        return _MAC_CHAR_MAP.get(base)
    elif SYSTEM == "Windows":
        result = user32.VkKeyScanW(ord(char))
        if result == -1:
            return None
        return result & 0xFF


# ---------------------------------------------------------------------------
# High-level actions (used by the command loop)
# ---------------------------------------------------------------------------

screen_width = 0
screen_height = 0


def move_relative(dx, dy):
    cx, cy = get_pointer()
    nx = max(0, min(screen_width - 1, cx + dx))
    ny = max(0, min(screen_height - 1, cy + dy))
    move_pointer(nx, ny)


def click(button=1):
    mouse_button(button, True)
    mouse_button(button, False)


def button_down(button=1):
    mouse_button(button, True)


def button_up(button=1):
    mouse_button(button, False)


def key_press(key):
    # Named key?
    if SYSTEM == "Linux":
        keysym_name = KEY_MAP.get(key)
        if keysym_name:
            kc = get_keycode(keysym_name)
            if kc:
                key_event(kc, True)
                key_event(kc, False)
            return
    else:
        kmap = _MAC_KEY_MAP if SYSTEM == "Darwin" else _WIN_KEY_MAP
        kc = kmap.get(key)
        if kc is not None:
            key_event(kc, True)
            key_event(kc, False)
            return

    # Character
    shift = needs_shift(key)
    kc = _resolve_char_keycode(key)
    if kc is None:
        print(f"ERROR: Unknown key '{key}'", file=sys.stderr)
        return

    shift_kc = _get_shift_keycode()
    if shift and shift_kc is not None:
        key_event(shift_kc, True)
    key_event(kc, True)
    key_event(kc, False)
    if shift and shift_kc is not None:
        key_event(shift_kc, False)


def modifier_down(key):
    if SYSTEM == "Linux":
        keysym_name = KEY_MAP.get(key)
        if not keysym_name:
            return
        kc = get_keycode(keysym_name)
    else:
        kmap = _MAC_KEY_MAP if SYSTEM == "Darwin" else _WIN_KEY_MAP
        kc = kmap.get(key)
    if kc is not None:
        key_event(kc, True)


def modifier_up(key):
    if SYSTEM == "Linux":
        keysym_name = KEY_MAP.get(key)
        if not keysym_name:
            return
        kc = get_keycode(keysym_name)
    else:
        kmap = _MAC_KEY_MAP if SYSTEM == "Darwin" else _WIN_KEY_MAP
        kc = kmap.get(key)
    if kc is not None:
        key_event(kc, False)


# ===========================================================================
# Main
# ===========================================================================

screen_width, screen_height = init()
print(json.dumps({"type": "screen", "width": screen_width, "height": screen_height}), flush=True)

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        cmd = json.loads(line)
        action = cmd.get("action")
        if action == "move":
            move_relative(cmd["dx"], cmd["dy"])
        elif action == "click":
            click(cmd.get("button", 1))
        elif action == "scroll":
            scroll_event(cmd.get("direction", "down"))
        elif action == "down":
            button_down(cmd.get("button", 1))
        elif action == "up":
            button_up(cmd.get("button", 1))
        elif action == "key":
            key_press(cmd["key"])
        elif action == "modifier_down":
            modifier_down(cmd["key"])
        elif action == "modifier_up":
            modifier_up(cmd["key"])
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
