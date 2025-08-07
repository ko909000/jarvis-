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

# Only import pygetwindow on Windows
try:
    if not sys.platform.startswith('linux'):
        import pygetwindow as gw
    else:
        gw = None
except ImportError:
    gw = None

# Setup encoding and logger
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App command map - Updated for Linux compatibility
APP_MAPPINGS = {
    "notepad": "gedit" if sys.platform.startswith('linux') else "notepad",
    "calculator": "gnome-calculator" if sys.platform.startswith('linux') else "calc",
    "chrome": "google-chrome" if sys.platform.startswith('linux') else "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "firefox": "firefox",
    "vlc": "vlc" if sys.platform.startswith('linux') else "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "command prompt": "gnome-terminal" if sys.platform.startswith('linux') else "cmd",
    "terminal": "gnome-terminal",
    "file manager": "nautilus" if sys.platform.startswith('linux') else "explorer",
    "control panel": "gnome-control-center" if sys.platform.startswith('linux') else "control",
    "settings": "gnome-control-center" if sys.platform.startswith('linux') else "start ms-settings:",
    "paint": "gimp" if sys.platform.startswith('linux') else "mspaint",
    "vs code": "code",
    "code": "code",
    "text editor": "gedit" if sys.platform.startswith('linux') else "notepad",
    "music player": "rhythmbox" if sys.platform.startswith('linux') else "wmplayer",
    "video player": "vlc"
}

# -------------------------
# Cross-platform focus utility
# -------------------------
async def focus_window(title_keyword: str) -> bool:
    """Focus window using cross-platform methods"""
    if sys.platform.startswith('linux'):
        # Linux window focusing using wmctrl if available
        try:
            # Try to use wmctrl for window focusing
            result = subprocess.run(['which', 'wmctrl'], capture_output=True, text=True)
            if result.returncode == 0:
                # Get list of windows
                windows_result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
                if windows_result.returncode == 0:
                    for line in windows_result.stdout.split('\n'):
                        if title_keyword.lower() in line.lower():
                            # Extract window ID (first column)
                            window_id = line.split()[0]
                            # Focus the window
                            subprocess.run(['wmctrl', '-i', '-a', window_id], capture_output=True)
                            logger.info(f"🪟 Linux window focused: {title_keyword}")
                            return True
            else:
                # Install wmctrl if not available
                logger.info("Installing wmctrl for window management...")
                subprocess.run(['sudo', 'apt', 'install', '-y', 'wmctrl'], capture_output=True)
        except Exception as e:
            logger.warning(f"⚠ Linux window focusing failed: {e}")
    
    elif gw:  # Windows with pygetwindow
        await asyncio.sleep(1.5)
        title_keyword = title_keyword.lower().strip()

        for window in gw.getAllWindows():
            if title_keyword in window.title.lower():
                if window.isMinimized:
                    window.restore()
                window.activate()
                logger.info(f"🪟 Windows window focused: {window.title}")
                return True
    
    logger.warning(f"⚠ Could not focus window: {title_keyword}")
    return False

# Index files/folders
async def index_items(base_dirs):
    item_index = []
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            logger.warning(f"⚠ Directory does not exist: {base_dir}")
            continue
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

# File/folder actions - Cross-platform
async def open_folder(path):
    try:
        if sys.platform.startswith('linux'):
            subprocess.call(['xdg-open', path])
        elif sys.platform == 'darwin':
            subprocess.call(['open', path])
        else:  # Windows
            os.startfile(path)
        await focus_window(os.path.basename(path))
        logger.info(f"✅ Folder opened: {path}")
    except Exception as e:
        logger.error(f"❌ Folder open error: {e}")

async def play_file(path):
    try:
        if sys.platform.startswith('linux'):
            subprocess.call(['xdg-open', path])
        elif sys.platform == 'darwin':
            subprocess.call(['open', path])
        else:  # Windows
            os.startfile(path)
        await focus_window(os.path.basename(path))
        logger.info(f"✅ File opened: {path}")
    except Exception as e:
        logger.error(f"❌ File open error: {e}")

async def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ Folder created: {path}"
    except Exception as e:
        return f"❌ Folder creation error: {e}"

async def rename_item(old_path, new_path):
    try:
        os.rename(old_path, new_path)
        return f"✅ Renamed to {new_path}"
    except Exception as e:
        return f"❌ Rename failed: {e}"

async def delete_item(path):
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        return f"🗑️ Deleted: {path}"
    except Exception as e:
        return f"❌ Delete failed: {e}"

# Cross-platform app control
@function_tool
async def open(app_title: str) -> str:
    """Open applications with cross-platform compatibility"""
    app_title = app_title.lower().strip()
    app_command = APP_MAPPINGS.get(app_title, app_title)
    
    try:
        if sys.platform.startswith('linux'):
            # Linux application launching
            # Check if app exists in PATH first
            which_result = subprocess.run(['which', app_command], capture_output=True, text=True)
            if which_result.returncode != 0:
                # Try some common alternatives
                alternatives = {
                    'google-chrome': ['chromium-browser', 'chromium', 'firefox'],
                    'gedit': ['nano', 'vim', 'mousepad'],
                    'gnome-calculator': ['galculator', 'kcalc', 'xcalc'],
                    'gnome-terminal': ['xterm', 'konsole', 'lxterminal'],
                    'nautilus': ['thunar', 'dolphin', 'pcmanfm'],
                    'gnome-control-center': ['systemsettings5', 'xfce4-settings-manager']
                }
                
                if app_command in alternatives:
                    for alt in alternatives[app_command]:
                        alt_result = subprocess.run(['which', alt], capture_output=True, text=True)
                        if alt_result.returncode == 0:
                            app_command = alt
                            break
                    else:
                        return f"❌ Application not found: {app_title}. Please install it first."
                else:
                    return f"❌ Application not found: {app_title}. Please install it first."
            
            # Launch the application
            process = subprocess.Popen([app_command], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL,
                                     preexec_fn=os.setsid)
            
            # Give the app time to start
            await asyncio.sleep(2)
            
            # Try to focus the window
            focused = await focus_window(app_title)
            
            if focused:
                return f"🚀 App launched and focused: {app_title}"
            else:
                return f"🚀 App launched: {app_title} (could not focus window)"
                
        else:
            # Windows application launching (original code)
            await asyncio.create_subprocess_shell(f'start "" "{app_command}"', shell=True)
            focused = await focus_window(app_title)
            if focused:
                return f"🚀 App launched and focused: {app_title}"
            else:
                return f"🚀 App launched: {app_title} (could not focus window)"
                
    except Exception as e:
        logger.error(f"❌ App launch error: {e}")
        return f"❌ Failed to launch {app_title}: {e}"

@function_tool
async def close(window_title: str) -> str:
    """Close windows with cross-platform compatibility"""
    if sys.platform.startswith('linux'):
        # Linux window closing using wmctrl or pkill
        try:
            # Try wmctrl first
            result = subprocess.run(['which', 'wmctrl'], capture_output=True, text=True)
            if result.returncode == 0:
                # Get list of windows and close matching ones
                windows_result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
                if windows_result.returncode == 0:
                    closed_any = False
                    for line in windows_result.stdout.split('\n'):
                        if window_title.lower() in line.lower():
                            # Extract window ID (first column)
                            window_id = line.split()[0]
                            # Close the window
                            subprocess.run(['wmctrl', '-i', '-c', window_id], capture_output=True)
                            closed_any = True
                    
                    if closed_any:
                        return f"✅ Closed windows containing: {window_title}"
                    else:
                        # Try pkill as fallback
                        subprocess.run(['pkill', '-f', window_title], capture_output=True)
                        return f"✅ Attempted to close process: {window_title}"
            else:
                # Use pkill if wmctrl not available
                subprocess.run(['pkill', '-f', window_title], capture_output=True)
                return f"✅ Attempted to close process: {window_title}"
                
        except Exception as e:
            logger.error(f"❌ Linux window close error: {e}")
            return f"❌ Failed to close {window_title}: {e}"
    
    elif win32gui:  # Windows
        def enumHandler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                if window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

        win32gui.EnumWindows(enumHandler, None)
        return f"✅ Closed windows containing: {window_title}"
    else:
        return "❌ Window closing not supported on this platform"

# Jarvis command logic - Updated for Linux
@function_tool
async def folder_file(command: str) -> str:
    """Handle folder and file operations with Linux compatibility"""
    # Use more appropriate directories for Linux
    if sys.platform.startswith('linux'):
        folders_to_index = [
            os.path.expanduser("~/"),  # Home directory
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            "/usr/share/applications"  # For .desktop files
        ]
    else:
        folders_to_index = ["D:/"]
    
    # Filter out non-existent directories
    folders_to_index = [d for d in folders_to_index if os.path.exists(d)]
    
    if not folders_to_index:
        return "❌ No accessible directories found for indexing"
    
    index = await index_items(folders_to_index)
    command_lower = command.lower()

    if "create folder" in command_lower:
        folder_name = command.replace("create folder", "").strip()
        if sys.platform.startswith('linux'):
            path = os.path.join(os.path.expanduser("~/"), folder_name)
        else:
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
        return "❌ Invalid rename command format"

    if "delete" in command_lower:
        item = await search_item(command, index, "folder") or await search_item(command, index, "file")
        if item:
            return await delete_item(item["path"])
        return "❌ Item not found for deletion"

    if "folder" in command_lower or "open folder" in command_lower:
        item = await search_item(command, index, "folder")
        if item:
            await open_folder(item["path"])
            return f"✅ Folder opened: {item['name']}"
        return "❌ Folder not found"

    item = await search_item(command, index, "file")
    if item:
        await play_file(item["path"])
        return f"✅ File opened: {item['name']}"

    return "⚠ No matching items found"
