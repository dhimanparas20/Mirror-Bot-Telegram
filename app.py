# from pyrogram.types import User,Chat,Message,InlineKeyboardMarkup
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from os import path,remove,listdir
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from modules.utils import *
from pyrogram import Client
from pyrogram import enums
import logging
import shutil
import asyncio
import aria2p
import random
import time
import requests
import shutil

# Logging level Settings
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Create aria2 client object
client =  aria2p.Client(host="http://localhost",port=6800,secret="")
aria2 = aria2p.API(client=client)
aria2.purge()

app = Client(
                "bot",
                api_id=API_ID, 
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                workdir=SESSIONS_DIR 
            )

#Set Download Options for aria2
options = {
    "dir": DOWNLOAD_DIR,
}

# Handler for Aria
class DownloadHandler():

    def start_download(self,url:str)-> str:
        try:
            if url.startswith("magnet:"):
                download = aria2.add_magnet(url,options=options)
                download.update
            else:
                download = aria2.add_uris([url], options=options) 
            return download
        except:
            return "Invalid URI"

    def get_all_downloads(self) -> list[object]:
        downloads = aria2.get_downloads()
        return downloads

    def get_gid(self,download:object)->str:
        return download.gid

    def get_download(self,gid:str) -> object: 
        download = aria2.get_download(gid=gid)
        return download
   
    def stop_download(self,download:object)->None:
        return aria2.remove(downloads=[download],force=False,files=True,clean=True)

    def purge(self)->bool:
        try:
            aria2.purge()
            return True
        except:
            return False

    def any_active_download(self)->bool:
        self.downloads = self.get_all_downloads()
        for download in self.downloads:
            if download.is_active:
                return True
        return False    
                
    def is_active(self,download:object)->bool:
        for child in download.followed_by:
            if child.is_active and not child.is_removed:
                return True
   
        return download.is_active
    
    def update_status(self,download:object):
        download.update()

    def get_respose_message(self,download:object,userid:int)->str:
            try: 
                download = download.live        
                message = ""
                stats = get_system_usage()
                if download.status == "error":
                    message = f"Download failed: {self.download.error_message}"
                    return message
                else:
                    if download.is_metadata:
                        message = "Downloading Metadata Wait..\n"
                    else:
                        message += (
                                    f"🆔 **Id:** [{download.gid}](tg://user?id={userid})\n"
                                    f"📁 **Name:** {download.name}\n"
                                    f"📥 **Downloaded:** {download.completed_length_string(human_readable=True)}/{download.total_length_string(human_readable=True)}\n"
                                    f"📈 **Progress:** {download.progress_string(digits=2)}\n"
                                    f"⚡ **Speed:** {download.download_speed_string(human_readable=True)}\n"
                                    f"⌛**ETA:** {download.eta_string(precision=2)}\n"
                                    # f"🌍 **Status:** {download.status}\n"
                                    f"💿 **Space Left**: {stats['disk_available_space']}/{stats['disk_total_space']}\n"
                                )
                        if download.is_torrent:
                            message += f"🌱 seeds: {download.num_seeders} 🍐peers: {download.connections}\n"  

                        message += f"{getLoadingAnimation(download.progress)}\n" 
                    return message
            except:
                return ("Download stopped")

# Handler for TG to uplaod and download stuff
class MyTgHandler():
    def __init__(self, url,userid,tgclient:object,chat_id,message_id):
        self.userid = userid
        self.client = tgclient
        self.chat_id = chat_id
        self.message_id = message_id
        self.file_name = None
        self.size = None
        self.file_path =None
        self.is_canceled = False

        self.creds = CREDS
        self.file_metadata = {}
        if USE_SERVICE_ACCOUNT:
            self.creds = get_random_service_account()
            self.file_metadata['driveId'] = TEAM_DRIVE_ID
        self.service = build('drive', 'v3', credentials=self.creds)    

    # Method to handle Download tasks 
    async def download_file(self,url,compress_file:bool):
        downobj = DownloadHandler()
        downobj.purge()
        download = downobj.start_download(url=url) 
        logging.info(f"Download Started for : {download.name}")
        if download == "Invalid URI":
            logging.error(f"Invalid URI: {url}")
            self.is_canceled = True
            await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Invalid URI")
            return
        oldmsg1,oldmsg2 = "",""
        now_time = time.time()
        while downobj.is_active(download) and not download.is_removed:       
            if download.is_active:
                respmsg =  downobj.get_respose_message(download,userid=self.userid)
                if respmsg == "Download stopped":
                    self.is_canceled = True
                    await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Mirror Cancelled by User")
                    return
                if oldmsg1 != respmsg:  # TG dont allow to edit if old and new message are same
                    if time.time()-now_time >=5: 
                        await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text=respmsg)
                        now_time = time.time()
                        oldmsg1=respmsg   
            for child in download.followed_by:
                if child.is_active:
                    respmsg =  downobj.get_respose_message(child,userid=self.userid)
                    if respmsg == "Download stopped":
                        self.is_canceled = True
                        await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Mirror Cancelled by User")
                        return
                    if oldmsg2 != respmsg:
                        if time.time()-now_time >=5: 
                            await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text=respmsg)
                            now_time = time.time()
                            oldmsg2=respmsg

        file_name = download.name
        size = download.total_length_string(human_readable=True)
        
        await asyncio.sleep(0.5)
        if  download.is_metadata:
            try:
                file_name =  child.name
            except:
                logging.info(f"Download Cancelled by User") 
                self.is_canceled = True
                await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Same Download is alredy processing.")
                return

            size = child.total_length_string(human_readable=True)
        base_path = path.join(DOWNLOAD_DIR, file_name)

        logging.info(f"Download Complete: {file_name}")
        logging.info(f"Download Size: {size}")

        # handle Cancelled Processes
        try:
            if child.is_removed:
                self.is_canceled = True
                try:
                    remove(base_path+".aria2")
                except:
                    pass   
                logging.info(f"Mirror Cancelled or Invalid URI") 
                await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Mirror Cancelled or Invalid URI")
                return
        except:
            if download.is_removed:
                self.is_canceled = True
                try:
                    remove(base_path+".aria2")
                except:
                    pass  
                logging.info(f"Mirror Cancelled or Invalid URI") 
                await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Mirror Cancelled or Invalid URI")
                return

        await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text=f"Downloaded: **{file_name}**\nSize: **{size}**")

        await asyncio.sleep(0.5)

        async def compress(base_path, file_name):
            if path.isdir(base_path):
                logging.info(f"Compressing: {file_name}") 
                await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Compressing, Please Wait.")
                await asyncio.sleep(0.5)
                zip_name = path.join(DOWNLOAD_DIR, file_name)
                # Create a zip file from the directory
                print(f"Compressing: {zip_name}")
                
                # Use asyncio.to_thread to run the blocking function in a separate thread
                await asyncio.to_thread(shutil.make_archive, zip_name, 'zip', base_path)
                
                # Optionally, remove the original directory after zipping
                shutil.rmtree(base_path)
                file_name = f"{file_name}.zip"
                logging.info(f"Compressed Name : {file_name}") 
                return file_name

        if compress_file:
            file_name = await compress(base_path,file_name)


        self.file_path = f"{DOWNLOAD_DIR}/{file_name}"
        self.file_name =file_name  
        self.size = size
        logging.info(f"Method download_file() completed and Exits. ") 
        return   self.file_path,self.file_name

    # Creates a directory in GD
    async def create_directory(self, directory_name, parent_id):
        file_metadata = {
            "name": directory_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id is not None:
            file_metadata["parents"] = [parent_id]
        file = self.service.files().create(supportsAllDrives=USE_SERVICE_ACCOUNT,supportsTeamDrives=USE_TEAM_DRIVE, body=file_metadata).execute()
        file_id = file.get("id")
        logging.info(f"Directory Created in GD with id: {file_id}")
        return file_id

    # Uploades the content of Directory in Gdrive  
    async def upload_dir(self, input_directory, parent_id):
        list_dirs = listdir(input_directory)
        if len(list_dirs) == 0:
            return parent_id
        new_id = None
        logging.info(f"Recursively Uploading Directory content to GD")
        for item in list_dirs:
            current_file_name = path.join(input_directory, item)
            if self.is_canceled:
                return None
            if path.isdir(current_file_name):
                current_dir_id = await self.create_directory(item, parent_id)
                new_id = await self.upload_dir(current_file_name, current_dir_id)
            else:
                mime_type = get_mime_type(current_file_name)
                file_name = current_file_name.split("/")[-1]
                # current_file_name will have the full path
                await self.upload_file(current_file_name, file_name, parent_id)
                new_id = parent_id
        return new_id
   
    # Entrypoint to uploading of files
    async def upload(self,file_path,file_name):
        if not self.is_canceled:
            logging.info(f"Starting Upload Process for: {file_name}")
            print("Uploading: ",self.file_name)
            await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Starting Upload Process..")
            await asyncio.sleep(0.5)

            url = f"{BASE_URL}{self.file_name.replace(' ','%20')}"
            link = None
            file_size= get_file_size(path.getsize(self.file_path))
            if path.isdir(file_path):
                    logging.info(f"Directory Detected")
                    dir_id = await self.create_directory(file_name, parent_id=GD_PARENT_FOLDER_ID)
                    result = await self.upload_dir(file_path, dir_id)
                    link = f"https://drive.google.com/folderview?id={dir_id}"
                    print(f"file uploaded to: {link}")
                    url += "/"
                    logging.info(f"Removing {self.file_path}")
                    shutil.rmtree(self.file_path) 
            else:
                logging.info(f"File Detected")
                await self.upload_file(file_path,file_name) 
                logging.info(f"Removing {self.file_path}")
                remove(path=self.file_path)
            print("Upload Complete for: ",self.file_name)
            message=(
                    f"Name: {self.file_name}\n"
                    f"Size: {self.size}\n"
                    )

            if link:
                message += f"\n[Drive Link]({link})" 
                
            Button_data=[
                        [  # First row
                            InlineKeyboardButton(  # Generates a callback query when pressed
                                "Download",
                                url=url
                            ),
                            InlineKeyboardButton(  # Opens a web URL
                                "All Files",
                                url=BASE_URL
                            ),
                        ]
                    ] 

            await self.client.delete_messages(chat_id=self.chat_id,message_ids=self.message_id)
            await asyncio.sleep(0.5)
            await app.send_message(self.userid, message,parse_mode=enums.ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(Button_data))
            
            # await self.client.edit_message_text(chat_id=self.chat_id,message_id=self.message_id,text=message,parse_mode=enums.ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(Button_data))
            print("Full upload complete")
            logging.info(f"Exiting Upload method")
            return
        
        logging.info(f"Mirror Cancelled by User")
        await self.client.edit_message_text(chat_id=self.chat_id,message_id=self.message_id,text="Mirror Cancelled by the USER !",parse_mode=enums.ParseMode.MARKDOWN)

    #Now Upload the file to gd
    async def upload_file(self,file_path,file_name,parent_folder_id=GD_PARENT_FOLDER_ID):
        if not self.is_canceled:
            mimetype = get_mime_type(file_path=file_path)
            logging.info(f"Detected mimetype: {mimetype}")
            file_metadata = {
                'name': file_name,
                'parents': [parent_folder_id],   #Folder_id
                "mimeType": mimetype
            } 
            media = MediaFileUpload(file_path, resumable=True, chunksize=1024 * 1024)
            request = self.service.files().create(body=file_metadata, media_body=media,supportsAllDrives=USE_SERVICE_ACCOUNT,supportsTeamDrives=USE_TEAM_DRIVE)
            media.stream()
            response = None 
            start_time = time.time()
            now_time = time.time()

            logging.info(f"Starting File Upload for: {file_name}")
            while response is None:
                # os.system("clear")
                status, response = request.next_chunk()
                if status:
                    # system("clear")
                    progress_percent = int(status.progress() * 100)
                    _file_uploaded= get_file_size(status.resumable_progress)
                    total_file_size= get_file_size(status.total_size)
                    
                    elapsed_time = time.time() - start_time
                    upload_speed,upunit = calculate_download_speed(downloaded_bytes=status.resumable_progress,elapsed_time=elapsed_time)
                    remaining_bytes = status.total_size - status.resumable_progress
                    eta = remaining_bytes / (status.resumable_progress/elapsed_time)
                    eta,etaunit = get_time(time=eta)
                                            
                    # stats = get_system_usage()
                    message = (
                            f"📁 **Name:** {file_name}\n"
                            f"📥 **Uploaded:** {_file_uploaded}/{total_file_size}\n"
                            f"📈 **Progress:** {progress_percent}%\n"
                            f"⚡ **Speed:** {upload_speed} {upunit}\n"
                            f"⌛**ETA:** {eta} {etaunit}\n"
                            f"🌍 **Status:** uploading\n"
                            # f"🧠 **CPU Usage**: {stats['cpu_usage_percent']}% ** 🔲 RAM Usage:** {stats['ram_usage_percent']}%\n"
                            f"{getLoadingAnimation(progress_percent)}\n"
                        )
                # asyncio.sleep(1)   
                if time.time()-now_time >=5:    
                    try:
                        await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text=message)
                        now_time = time.time()
                        # await asyncio.sleep(5)
                    except:
                        pass  
            return
        return                       
 
    #Returns a random available Gofiles server
    async def get_gofile_server(self):
        response = requests.get('https://api.gofile.io/servers')
        try:
            data = response.json()
        except ValueError:
            print("Failed to parse JSON from the servers response.")
            print("Response content:", response.text)
            return None
        
        if data['status'] == "ok":
            servers = data['data']['servers']
            serverno = random.randint(0, len(servers))     
            if serverno == len(servers):
                serverno -= 1
            logging.info(f"Go server: {servers[serverno]['name']}")    
            return servers[serverno]['name']
        else:
            logging.info(f"Failed to get Go Server")
            print("Failed to get servers:", data)
            return None

    # generates temperary gofile server  
    async def gofile_upload(self,file_path,file_name):
        if not self.is_canceled:
            logging.info(f"Starting Go Upload")
            go_server = await self.get_gofile_server()
            if go_server is None:
                print("No server available to upload the file.")
                await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="No server Available.\nPlease try again after some time")
                return
            print(f"Uploading to server {go_server}")
            url = f'https://{go_server}.gofile.io/contents/uploadfile'
            headers = {
                'Authorization': f'Bearer {GO_API}'
            }
            file = {
                'file': (file_path, open(file_path, 'rb')),
                'folderId': (GO_FOLDER_ID)
            }
            try:
                await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Uploading to GoFiles.\nPlease wait")
                start_time = time.time()
                response = requests.post(url,headers=headers,files=file)
                try:
                    await asyncio.sleep(0.5) 
                    data = response.json()
                except ValueError:
                    print("Failed to parse JSON from the upload response.")
                    print("Response content:", response.text)
                    return

                # print(data)
                time_taken = time.time()-start_time
                if data['status']=="ok":
                    # print(data)
                    await asyncio.sleep(0.5) 
                    fixed_name = data['data']['fileName'].replace(" ","%20")
                    down_url = f"https://{go_server}.gofile.io/download/web/{data['data']['fileId']}/{fixed_name}"
                    
                    file_size= get_file_size(path.getsize(self.file_path))
                    upspeed = float(file_size.split()[0])/time_taken
                    message = (
                            f"📁 **Name:** {file_name}\n"
                            f"📤 **Size:** {file_size}\n"
                            f"⚡ **Speed:** {upspeed:.2f} MB/s\n"
                            f"⌛**Time Taken:** {time_taken:.0f} s\n"
                            f"\nIf Download Button isn't Working, Click on **'Go Files'** Button & Download from there."
                            ) 
                    Button_data = [
                                    [  # First row
                                        InlineKeyboardButton(  # Generates a callback query when pressed
                                            "Download",
                                            url=down_url
                                        ),
                                        InlineKeyboardButton(  # Opens a web URL
                                            "Go Files",
                                            url=f"{data['data']['downloadPage']}"
                                        ),
                                    ],
                                    [  # 2nd Row
                                        InlineKeyboardButton(  # Opens a web URL
                                            "Index Site",
                                            url="https://luffy.mst-uploads.workers.dev/0:/"
                                        ),
                                    ]
                                ] 
                    try:
                        remove(file_path)
                        print(f"File {file_path} has been uploaded and deleted from the server.")
                        await self.client.edit_message_text(chat_id=self.chat_id,message_id=self.message_id,text=message,parse_mode=enums.ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(Button_data))

                    except Exception as e:
                        logging.info(f"GoFile Exception: {e}")
                        print(f"Exception: {e}")  
                        await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Server Error.\nPlease try again after some time")

                else:
                    await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Server Error.\nPlease try again after some time")

            except Exception as e:
                logging.info(f"GoFile Exception: {e}")
                print("Exception: ",e)
                await self.client.edit_message_text(chat_id=self.chat_id, message_id=self.message_id, text="Server Error.\nPlease try again after some time")

        return        

system_stats = get_system_usage()
print("Listening to messages on @mstapibot")  
print("===========SYSTEM STATUS============")
print(f"CPU Usage: {system_stats['cpu_usage_percent']}%")
print(f"RAM Usage: {system_stats['ram_usage_percent']}%")
print(f"Disk Usage: {system_stats['disk_usage_percent']}%")
print(f"Space Free: {system_stats['disk_available_space']}/{system_stats['disk_total_space']}")
print(f"Space Used: {system_stats['disk_used_space']}/{system_stats['disk_total_space']}")
print("======================================")

logging.info('Bot Started')
@app.on_message()
async def handle(client,message):
    mid,uid,uname,cid = message.id,message.from_user.id,message.from_user.username,message.chat.id
    # me = await app.get_me()
    
    #Breakdown the message into parts
    parts = message.text.split()
    list_len = len(parts)
    try:
        username = uname
    except:
        username = None   
    logging.info(f"=====================================")
    logging.info(f'Received Command: {parts[0]} by @{username}')
    logging.info(f"=====================================")

    
    if parts[0] == "/start" and list_len == 1:
        dataret = await message.reply_text("👋**__Welcome to Bot__** ", quote=True,parse_mode=enums.ParseMode.MARKDOWN)
        logging.info(f"User:{uid} -  Query:start  Completed")

    elif parts[0] == "/mirror" and list_len == 2:
        
        url = parts[1]
        sentdata = await message.reply_text("Starting... Please Wait", quote=True)
        await asyncio.sleep(0.5) 

        # try:
        logging.info(f"Mirror Started by: {uid} in chat {cid}")
        myobj = MyTgHandler(url=url,userid=uid,tgclient=client,chat_id=cid,message_id=sentdata.id)
        task1 = asyncio.create_task(myobj.download_file(compress_file=False,url=url))
        file_path,file_name  = await task1
        task2 = asyncio.create_task(myobj.upload(file_path,file_name))
        await task2
        logging.info(f"User:{uid} -  Query:mirror  Completed")
        return
        
        # except Exception as e:
        #     print(f"Exception: {e}")
        #     await client.edit_message_text(chat_id=cid, message_id=sentdata.id, text=f"Exception: {e}")
        #     return

    elif parts[0] == "/zipmirror" and list_len == 2:
        
        url = parts[1]
        sentdata = await message.reply_text("Starting... Please Wait", quote=True)
        await asyncio.sleep(0.5) 

        # try:
        logging.info(f"Zip-Mirror Started by: {uid} in chat {cid}")
        myobj = MyTgHandler(url=url,userid=uid,tgclient=client,chat_id=cid,message_id=sentdata.id)
        task1 = asyncio.create_task(myobj.download_file(compress_file=True,url=url))
        file_path,file_name  = await task1
        task2 = asyncio.create_task(myobj.upload(file_path,file_name))
        await task2
        logging.info(f"User:{uid} -  Query:zipmirror  Completed")
        return    

    elif parts[0] == "/link" and list_len == 2:
        url = parts[1]
        sentdata = await message.reply_text("Starting... Please Wait", quote=True)
        await asyncio.sleep(0.5) 

        # Schedule the coroutine to be run in the event loop
        try:
            logging.info(f"Link Mirror Started by: {uid} in chat {cid}")
            myobj = MyTgHandler(url=url,userid=uid,tgclient=client,chat_id=cid,message_id=sentdata.id)
            task1 = asyncio.create_task(myobj.download_file(compress_file=True,url=url))
            file_path,file_name  = await task1
            task2 = asyncio.create_task(myobj.gofile_upload(file_path, file_name))
            await task2
            logging.info(f"User:{uid} -  Query:link  Completed")
            return
        
        except Exception as e:
            logging.info(f"link Exception: {e}")
            print(f"Exception: {e}")
            await client.edit_message_text(chat_id=cid, message_id=sentdata.id, text=f"Exception: {e}")
            return

    elif parts[0] == "/cancel" and list_len == 2:
        gid = parts[1]
        sentdata = await message.reply_text("Stopping... Please Wait", quote=True)
        await asyncio.sleep(0.5) 
        object = DownloadHandler()
        try:
            logging.info(f"Cancel Called by: {uid} in chat {cid} for {gid}")
            download = object.get_download(gid=gid)
            if not download.is_complete:
                result = object.stop_download(download=download)
                if result[0]:
                    await client.delete_messages(chat_id=cid,message_ids=sentdata.id)
                    logging.info(f"User:{uid} -  Query:cancel  Completed")
                    return
            else:
                logging.info(f"Cant Cancel Uploading task ID: {gid}")
                await message.reply_text("For Now, Uploading Tasks Cant Be Cancelled :-( ", quote=True)
                return
        except Exception as e:
            await client.edit_message_text(chat_id=cid, message_id=sentdata.id, text="Invalid ID")
            logging.info(f"Invalid Cancel ID: {gid}.")
            logging.info(f"Exception: {e}")
            return

    elif parts[0] == "/stats" and list_len == 1:
        logging.info("Serving Stats")
        stats = get_system_usage()
        msg = (
            f"**CPU Usage:** {stats['cpu_usage_percent']}%\n"
            f"**RAM Usage:** {stats['ram_usage_percent']}%\n"
            f"**Disk Usage:** {stats['disk_usage_percent']}%\n"
            f"**Disk Used:** {stats['disk_used_space']}/{stats['disk_total_space']}\n"
            f"**Disk Free:** {stats['disk_available_space']}/{stats['disk_total_space']}\n"
        )
        await message.reply_text(msg, quote=True,parse_mode=enums.ParseMode.MARKDOWN)
        logging.info(f"User:{uid} -  Query:stats  Completed")
        return

    elif parts[0] == "/speedtest" and list_len == 1:
        sentdata = await message.reply_text("Running the Horses. Please Wait", quote=True,parse_mode=enums.ParseMode.MARKDOWN)
        start_time = time.time()
        speedtest = perform_speedtest()
        stop_time = time.time()-start_time
        if speedtest:
            msg = (
                f"**📥 Download Speed:** {get_file_size(speedtest['download_speed']/8)}/s \n"
                f"**📤 Upload Speed:** {get_file_size(speedtest['upload_speed']/8)}/s\n"
                f"**🏓 Ping:** {speedtest['ping']} ms\n"
                f"**⌛ Time Taken:** {stop_time:.0f}s"
            )
            await client.edit_message_text(chat_id=cid, message_id=sentdata.id, text=msg)
            logging.info(f"User:{uid} -  Query:speedtest  Completed")
            return
        else:    
            await client.edit_message_text(chat_id=cid, message_id=sentdata.id, text="Unable to Fetch Speed :-( ")
            logging.info(f"Unable to fetch Speed")
            return
        
    elif parts[0] == "/ping" or parts[0].lower()=="ping":
        await message.reply_text(f"[Pong!](tg://user?id={uid}) 🏓", quote=True,parse_mode=enums.ParseMode.MARKDOWN)
        logging.info(f"User:{uid} -  Query:ping  Completed")
        return

    elif parts[0] == "/allfiles" or parts[0]=="/index":
        msg=(f"Index Link For All Files.")
        Button_data=[
                    [  # First row
                        InlineKeyboardButton(  # Opens a web URL
                            "HERE",
                            url=BASE_URL
                        ),
                    ]
                ] 
        # await app.send_message("{uid}", message,parse_mode=enums.ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(Button_data))
        await message.reply_text(msg, quote=False,parse_mode=enums.ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(Button_data))
        logging.info(f"User:{uid} -  Query:allfiles  Completed")
        return
            
    elif parts[0] == "/help":
        msg = (f"\nWelcome to the bot."
            f"\nGoto [Repo](https://github.com/dhimanparas20?tab=repositories) for more details"
            f"\nThe bot is used to mirror files to Google Drive or provide a Direct Download Link.")
        await message.reply_text(msg, quote=True,parse_mode=enums.ParseMode.MARKDOWN)
        logging.info(f"User:{uid} -  Query:help  Completed")
        return

    else:
        await message.reply_text("No Valid Command\ntry /help for Help", quote=True,parse_mode=enums.ParseMode.MARKDOWN)
        logging.info(f"User:{uid} -  Query:NoCommand  Completed")
        return

if __name__ == "__main__":
    app.run()
