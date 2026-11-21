"""Read-only capture of a known console window; no keyboard, mouse or window changes."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import datetime as dt
import hashlib
import json
from pathlib import Path
from PIL import Image

p = argparse.ArgumentParser()
p.add_argument('mode', choices=['verify', 'trace'])
a = p.parse_args()
out = Path(__file__).resolve().parent / 'validation/round8'
identity = json.loads((out / a.mode / 'window-identity.json').read_text(encoding='utf-8-sig'))
command = json.loads((out / a.mode / 'command.json').read_text(encoding='utf-8-sig'))
handle = identity['MainWindowHandle']
handle = handle['value'] if isinstance(handle, dict) else handle
user = c.WinDLL('user32', use_last_error=True)
gdi = c.WinDLL('gdi32', use_last_error=True)
user.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
user.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
user.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
user.GetWindowDC.argtypes = [w.HWND]
user.GetWindowDC.restype = w.HDC
user.PrintWindow.argtypes = [w.HWND, w.HDC, w.UINT]
user.ReleaseDC.argtypes = [w.HWND, w.HDC]
gdi.CreateCompatibleDC.argtypes = [w.HDC]
gdi.CreateCompatibleDC.restype = w.HDC
gdi.CreateCompatibleBitmap.argtypes = [w.HDC, c.c_int, c.c_int]
gdi.CreateCompatibleBitmap.restype = w.HBITMAP
gdi.SelectObject.argtypes = [w.HDC, w.HANDLE]
gdi.SelectObject.restype = w.HANDLE
gdi.DeleteObject.argtypes = [w.HANDLE]
gdi.DeleteDC.argtypes = [w.HDC]
gdi.GetDIBits.argtypes = [w.HDC, w.HBITMAP, w.UINT, w.UINT, c.c_void_p, c.c_void_p, w.UINT]
pid = w.DWORD()
user.GetWindowThreadProcessId(handle, c.byref(pid))
title = c.create_unicode_buffer(1024)
user.GetWindowTextW(handle, title, 1024)
assert pid.value == identity['Id'] == command['processId']
assert title.value == identity['MainWindowTitle'] == f'ROCm C# - {a.mode} - actual PowerShell execution'
rect = w.RECT()
assert user.GetWindowRect(handle, c.byref(rect))
width, height = rect.right - rect.left, rect.bottom - rect.top


class Header(c.Structure):
    _fields_ = [('size', w.DWORD), ('width', w.LONG), ('height', w.LONG), ('planes', w.WORD),
                ('bits', w.WORD), ('compression', w.DWORD), ('imageSize', w.DWORD), ('x', w.LONG),
                ('y', w.LONG), ('colors', w.DWORD), ('important', w.DWORD)]


screen = user.GetWindowDC(handle)
memory = gdi.CreateCompatibleDC(screen)
bitmap = gdi.CreateCompatibleBitmap(screen, width, height)
old = gdi.SelectObject(memory, bitmap)
try:
    assert user.PrintWindow(handle, memory, 2), 'PrintWindow failed'
    header = Header(c.sizeof(Header), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
    pixels = c.create_string_buffer(width * height * 4)
    assert gdi.GetDIBits(memory, bitmap, 0, height, pixels, c.byref(header), 0) == height
    image = Image.frombytes('RGB', (width, height), pixels.raw, 'raw', 'BGRX')
    name = ('01' if a.mode == 'verify' else '02') + f'-powershell-{a.mode}-frame.png'
    target = out / 'screenshots' / name
    assert not target.exists(), 'Capture must not overwrite earlier bytes'
    image.save(target)
finally:
    gdi.SelectObject(memory, old)
    gdi.DeleteObject(bitmap)
    gdi.DeleteDC(memory)
    user.ReleaseDC(handle, screen)
metadata = {'capturedAt': dt.datetime.now().astimezone().isoformat(), 'file': target.relative_to(out).as_posix(),
    'api': 'Win32 PrintWindow (flags=2), read-only full window bitmap', 'windowTitle': title.value,
    'processId': pid.value, 'windowHandle': handle, 'width': width, 'height': height, 'format': 'PNG',
    'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size,
    'edited': False, 'terminalInputAutomated': False, 'source': f'{a.mode}/command.json',
    'scope': 'Actual PowerShell/ConsoleHost window including native title bar; no log replay, HTML render, UI reconstruction, crop or annotation.'}
(out / 'screenshots' / (a.mode + '-capture.json')).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(metadata, ensure_ascii=False))
