import os
import subprocess
import sys
import logging
from fuzzywuzzy import process
from livekit.agents import function_tool
import asyncio
try:
    if not sys.platform.startswith('linux'):
        import pygetwindow as gw
    else:
        gw = None
except ImportError:
    gw = None

sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def focus_window(title_keyword: str) -> bool:
    """Cross-platform window focusing"""
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
        return False
    elif gw:
        await asyncio.sleep(1.5)
        title_keyword = title_keyword.lower().strip()

        for window in gw.getAllWindows():
            if title_keyword in window.title.lower():
                if window.isMinimized:
                    window.restore()
                window.activate()
                logger.info(f"🪟 Window focused: {window.title}")
                return True
    
    logger.warning(f"⚠ Could not focus window: {title_keyword}")
    return False

async def index_files(base_dirs):
    """Index files from specified directories"""
    file_index = []
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            logger.warning(f"⚠ Directory does not exist: {base_dir}")
            continue
        
        try:
            for root, _, files in os.walk(base_dir):
                for f in files:
                    file_path = os.path.join(root, f)
                    # Skip hidden files and system files
                    if not f.startswith('.') and os.access(file_path, os.R_OK):
                        file_index.append({
                            "name": f,
                            "path": file_path,
                            "type": "file"
                        })
        except PermissionError:
            logger.warning(f"⚠ Permission denied accessing: {base_dir}")
        except Exception as e:
            logger.warning(f"⚠ Error indexing {base_dir}: {e}")
    
    logger.info(f"✅ Indexed {len(file_index)} files from {base_dirs}")
    return file_index

async def search_file(query, index):
    """Search for files using fuzzy matching"""
    choices = [item["name"] for item in index]
    if not choices:
        logger.warning("⚠ No files available for matching")
        return None

    best_match, score = process.extractOne(query, choices)
    logger.info(f"🔍 Matched '{query}' to '{best_match}' (Score: {score})")
    if score > 70:
        for item in index:
            if item["name"] == best_match:
                return item
    return None

async def open_file(item):
    """Open file using cross-platform method"""
    try:
        logger.info(f"📂 Opening file: {item['path']}")
        
        if sys.platform.startswith('linux'):
            subprocess.call(['xdg-open', item["path"]])
        elif sys.platform == 'darwin':
            subprocess.call(['open', item["path"]])
        else:  # Windows
            os.startfile(item["path"])
        
        # Try to focus window after opening
        await focus_window(item["name"])
        return f"✅ File opened: {item['name']}"
    except Exception as e:
        logger.error(f"❌ File open error: {e}")
        return f"❌ Failed to open file: {e}"

async def handle_command(command, index):
    """Handle file opening command"""
    item = await search_file(command, index)
    if item:
        return await open_file(item)
    else:
        logger.warning("❌ File not found")
        return "❌ File not found"

@function_tool
async def Play_file(name: str) -> str:
    """Play/open files with cross-platform directory support"""
    # Use appropriate directories based on platform
    if sys.platform.startswith('linux'):
        folders_to_index = [
            os.path.expanduser("~/"),  # Home directory
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Music"),
            os.path.expanduser("~/Videos"),
            os.path.expanduser("~/Pictures"),
            "/usr/share",  # System files
            "/opt"  # Optional software
        ]
    else:
        folders_to_index = ["D:/", "C:/Users"]
    
    # Filter out non-existent directories
    folders_to_index = [d for d in folders_to_index if os.path.exists(d)]
    
    if not folders_to_index:
        return "❌ No accessible directories found for file search"
    
    index = await index_files(folders_to_index)
    command = name.strip()
    return await handle_command(command, index)
