from google.oauth2 import service_account
from pathlib import Path
import configparser as cp
import speedtest
import psutil
import mimetypes
import random
import asyncio
import shutil
from modules import gentoken
from os import listdir,path,makedirs,system

system("clear")

# Read configuration from file
cfg = cp.ConfigParser()
cfg.read('config.conf')

# Loading of variables
USE_SERVICE_ACCOUNT = cfg['GOOGLE'].getboolean("USE_SERVICE_ACCOUNTS")
GD_PARENT_FOLDER_ID = cfg['GOOGLE']['GDRIVE_FOLDER_ID']
TEAM_DRIVE_ID = cfg['GOOGLE']['TEAM_DRIVE_ID']
ACCOUNTS_FOLDER = cfg['GOOGLE']['ACCOUNTS_FOLDER']
GO_API = cfg['GOFILE']['GO_API']
GO_FOLDER_ID = cfg['GOFILE']['GO_FOLDER_ID']
USE_TEAM_DRIVE = cfg['GOOGLE'].getboolean("USE_TEAM_DRIVE")
BOT_TOKEN = cfg['TG']['BOT_TOKEN']
BASE_URL = cfg['INDEX']['BASE_URL']
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = path.join(BASE_DIR, 'downloads')
API_ID = cfg['TG']['API_ID']
API_HASH = cfg['TG']['API_HASH']
CREDS = gentoken.genTokenJson()


BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = path.join(BASE_DIR, 'downloads')
SESSIONS_DIR = "sessions"


if not path.exists(SESSIONS_DIR):
    makedirs(SESSIONS_DIR)
try:
    shutil.rmtree(DOWNLOAD_DIR)
    makedirs(DOWNLOAD_DIR)
except:
    makedirs(DOWNLOAD_DIR)

# Get mime of a file
def get_mime_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type

# Progress Animation
def getLoadingAnimation(progress):
    loadinganimation = "▱▱▱▱▱▱▱▱▱▱"
    for i in range(int(progress // 10)):
        loadinganimation = loadinganimation.replace("▱", "▰", 1)
    return loadinganimation 

# Calculate download speed in MB/s by default
def calculate_download_speed(downloaded_bytes, elapsed_time):    
    speed = int(downloaded_bytes) / float(elapsed_time)
    if speed < 1024:
        return f'{speed:.1f}', 'B/s'
    elif speed < 1024 * 1024:
        return f'{(speed / 1024):.1f}','KB/s'
    else:
        return f'{speed /(1024 * 1024):.1f}','MB/s' 
 
#Sorts File Size units
def get_file_size(bytes):
    bytes = int(bytes)
    if bytes < 1024:
        return bytes,"B"
    elif bytes >= 1024 and bytes < 1024*1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes >= 1024*1024 and bytes < 1024*1024*1024:
        return f"{bytes/(1024*1024):.1f} MB"
    else:
        return f"{bytes/(1024*1024*1024):.1f} GB"

#Sorts Time Unit
def get_time(time):
    time = int(time)
    if time < 60 :
        return f"{time:.1f}","s"
    elif time >=60 and time <3600 :
        return f"{time/60:.1f}","min"
    elif time >=3600 and time <3600*24:
        return f"{time/3600:.1f}","hr"
    else:
        return f"{time/(3600*24):.1f}","days"

# Function to get system usage
def get_system_usage():
    # Get CPU usage percentage
    cpu_usage = psutil.cpu_percent(interval=0)
    
    # Get RAM usage information
    memory_info = psutil.virtual_memory()
    ram_usage = memory_info.percent
    
    # Get disk usage information
    disk_usage = psutil.disk_usage(DOWNLOAD_DIR)
    disk_usage_percent = disk_usage.percent
    disk_used = disk_usage.used
    disk_total = disk_usage.total
    disk_available = disk_usage.free

    # Format the results
    results = {
        "cpu_usage_percent": cpu_usage,
        "ram_usage_percent": ram_usage,
        "disk_usage_percent": disk_usage_percent,
        "disk_used_space": get_file_size(disk_used),
        "disk_total_space": get_file_size(disk_total),
        "disk_available_space": get_file_size(disk_available)
    }
    
    return results  

# Perform SpeedTest
async def perform_speedtest():
    st = speedtest.Speedtest()
    st.get_servers()
    st.get_best_server()
    download_speed = st.download()
    await asyncio.sleep(1)  # Simulate async delay
    upload_speed = st.upload()
    await asyncio.sleep(1)  # Simulate async delay
    ping = st.results.ping
    return {
        'download_speed': download_speed,
        'upload_speed': upload_speed,
        'ping': ping
    }

# Load a random Service account Every time
def get_random_service_account():
    account_files = listdir(ACCOUNTS_FOLDER)
    random_account_file = random.choice(account_files)
    credentials_path = path.join(ACCOUNTS_FOLDER, random_account_file)
    CREDS = service_account.Credentials.from_service_account_file(credentials_path)
    # print(f"Using service account: {random_account_file}")  
    return CREDS