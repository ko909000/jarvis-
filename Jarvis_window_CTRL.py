import os
import subprocess
import logging
import sys
import asyncio
from fuzzywuzzy import process

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func): 
        return func

try:
    import win32gui
    import win32con
except ImportError:
    win32gui = None
    win32con = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Setup encoding and logger
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App command map - Cross-platform
if os.name == 'nt':  # Windows
    APP_MAPPINGS = {
        "notepad": "notepad",
        "calculator": "calc",
        "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "vlc": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
        "command prompt": "cmd",
        "control panel": "control",
        "settings": "start ms-settings:",
        "paint": "mspaint",
        "vs code": "C:\\Users\\gaura\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
        "postman": "C:\\Users\\gaura\\AppData\\Local\\Postman\\Postman.exe"
    }
else:  # Linux/Unix
    APP_MAPPINGS = {
        "notepad": "gedit",
        "text editor": "gedit",
        "calculator": "gnome-calculator",
        "chrome": "google-chrome",
        "firefox": "firefox",
        "vlc": "vlc",
        "terminal": "gnome-terminal",
        "file manager": "nautilus",
        "vs code": "code",
        "vscode": "code",
        "libreoffice": "libreoffice",
        "writer": "libreoffice --writer",
        "calc": "libreoffice --calc",
        "impress": "libreoffice --impress"
    }

# -------------------------
# Global focus utility
# -------------------------
async def focus_window(title_keyword: str) -> bool:
    if not gw:
        logger.warning("⚠ pygetwindow")
        return False

    await asyncio.sleep(1.5)  # Give time for window to appear
    title_keyword = title_keyword.lower().strip()

    for window in gw.getAllWindows():
        if title_keyword in window.title.lower():
            if window.isMinimized:
                window.restore()
            window.activate()
            return True
    return False

# Index files/folders
async def index_items(base_dirs):
    item_index = []
    for base_dir in base_dirs:
        for root, dirs, files in os.walk(base_dir):
            for d in dirs:
                item_index.append({"name": d, "path": os.path.join(root, d), "type": "folder"})
            for f in files:
                item_index.append({"name": f, "path": os.path.join(root, f), "type": "file"})
    logger.info(f"✅ Indexed {len(item_index)} items.")
    return item_index

async def search_item(query, index, item_type):
    filtered = [item for item in index if item["type"] == item_type]
    choices = [item["name"] for item in filtered]
    if not choices:
        return None
    best_match, score = process.extractOne(query, choices)
    logger.info(f"🔍 Matched '{query}' to '{best_match}' with score {score}")
    if score > 70:
        for item in filtered:
            if item["name"] == best_match:
                return item
    return None

# File/folder actions
async def open_folder(path):
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', path])
        else:  # Linux
            subprocess.call(['xdg-open', path])
        await focus_window(os.path.basename(path))
        logger.info(f"✅ Folder opened: {path}")
    except Exception as e:
        logger.error(f"❌ फ़ाइल open करने में error आया। {e}")
        raise

async def play_file(path):
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', path])
        else:  # Linux
            subprocess.call(['xdg-open', path])
        await focus_window(os.path.basename(path))
        logger.info(f"✅ File opened: {path}")
    except Exception as e:
        logger.error(f"❌ फ़ाइल open करने में error आया।: {e}")
        raise

async def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ Folder create हो गया।: {path}"
    except Exception as e:
        return f"❌ फ़ाइल create करने में error आया।: {e}"

async def rename_item(old_path, new_path):
    try:
        os.rename(old_path, new_path)
        return f"✅ नाम बदलकर {new_path} कर दिया गया।"
    except Exception as e:
        return f"❌ नाम बदलना fail हो गया: {e}"

async def delete_item(path):
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        return f"🗑️ Deleted: {path}"
    except Exception as e:
        return f"❌ Delete नहीं हुआ।: {e}"

# App control
@function_tool
async def open(app_title: str) -> str:
    app_title = app_title.lower().strip()
    app_command = APP_MAPPINGS.get(app_title, app_title)
    
    try:
        if os.name == 'nt':  # Windows
            await asyncio.create_subprocess_shell(f'start "" "{app_command}"', shell=True)
        else:  # Linux/Unix
            # Use nohup to prevent the process from being killed when terminal closes
            await asyncio.create_subprocess_shell(f'nohup {app_command} > /dev/null 2>&1 &', shell=True)
        
        # Give the app time to start
        await asyncio.sleep(2)
        
        focused = await focus_window(app_title)
        if focused:
            return f"🚀 App launch हुआ और focus में है: {app_title}."
        else:
            logger.info(f"App {app_title} launched but couldn't focus window")
            return f"🚀 {app_title} Launch किया गया, लेकिन window पर focus नहीं हो पाया।"
    except Exception as e:
        logger.error(f"Error launching {app_title}: {e}")
        return f"❌ {app_title} Launch नहीं हो पाया।: {e}"

@function_tool
async def close(window_title: str) -> str:
    if not win32gui:
        return "❌ win32gui"

    def enumHandler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    win32gui.EnumWindows(enumHandler, None)
    return f"❌ Window बंद हो गई है।: {window_title}"

# Jarvis command logic
@function_tool
async def folder_file(command: str) -> str:
    # Cross-platform folder indexing
    if os.name == 'nt':  # Windows
        folders_to_index = ["D:/", "C:/Users"]
    else:  # Linux/Unix
        home_dir = os.path.expanduser("~")
        folders_to_index = [home_dir, "/usr/share/applications", "/home"]
    
    index = await index_items(folders_to_index)
    command_lower = command.lower()

    if "create folder" in command_lower:
        folder_name = command.replace("create folder", "").strip()
        path = os.path.join("D:/", folder_name)
        return await create_folder(path)

    if "rename" in command_lower:
        parts = command_lower.replace("rename", "").strip().split("to")
        if len(parts) == 2:
            old_name = parts[0].strip()
            new_name = parts[1].strip()
            item = await search_item(old_name, index, "folder")
            if item:
                new_path = os.path.join(os.path.dirname(item["path"]), new_name)
                return await rename_item(item["path"], new_path)
        return "❌ rename command valid नहीं है।"

    if "delete" in command_lower:
        item = await search_item(command, index, "folder") or await search_item(command, index, "file")
        if item:
            return await delete_item(item["path"])
        return "❌ Delete करने के लिए item नहीं मिला।"

    if "folder" in command_lower or "open folder" in command_lower:
        item = await search_item(command, index, "folder")
        if item:
            await open_folder(item["path"])
            return f"✅ Folder opened: {item['name']}"
        return "❌ Folder नहीं मिला।."

    item = await search_item(command, index, "file")
    if item:
        await play_file(item["path"])
        return f"✅ File opened: {item['name']}"

    return "⚠ कुछ भी match नहीं हुआ।"
