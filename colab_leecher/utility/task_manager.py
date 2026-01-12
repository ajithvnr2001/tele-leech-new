# copyright 2024 © Xron Trix | https://github.com/Xrontrix10


import pytz
import shutil
import logging
from time import time
from datetime import datetime
from asyncio import sleep
from os import makedirs, path as ospath, system
from colab_leecher import OWNER, colab_bot, DUMP_ID
from colab_leecher.downlader.manager import calDownSize, get_d_name, downloadManager
from colab_leecher.downlader.ytdl import expand_playlist_urls
from colab_leecher.utility.helper import (
    getSize,
    applyCustomName,
    keyboard,
    sysINFO,
    is_google_drive,
    is_telegram,
    is_ytdl_link,
    is_mega,
    is_terabox,
    is_torrent,
)
from colab_leecher.utility.handler import (
    Leech,
    Unzip_Handler,
    Zip_Handler,
    IndividualZipLeech,
    SendLogs,
    cancelTask,
    SubLeech,
)
from colab_leecher.utility.variables import (
    BOT,
    MSG,
    BotTimes,
    Messages,
    Paths,
    Aria2c,
    Transfer,
    TaskError,
)


async def task_starter(message, text):
    global BOT
    await message.delete()
    BOT.State.started = True
    if BOT.State.task_going == False:
        src_request_msg = await message.reply_text(text)
        return src_request_msg
    else:
        msg = await message.reply_text(
            "I am already working ! Please wait until I finish !!"
        )
        await sleep(15)
        await msg.delete()
        return None


async def taskScheduler():
    global BOT, MSG, BotTimes, Messages, Paths, Transfer, TaskError
    src_text = []
    is_dualzip, is_unzip, is_zip, is_dir, is_subex = (
        BOT.Mode.type == "undzip",
        BOT.Mode.type == "unzip",
        BOT.Mode.type == "zip",
        BOT.Mode.mode == "dir-leech",
        BOT.Mode.mode == "subex",
    )
    
    # Auto-detect if it's a directory mode for subex
    if is_subex and any(x in str(BOT.SOURCE[0]) for x in ["/content/", "/home"]):
        is_dir = True
    
    # Expand playlist URLs for ytdl_hard mode (sequential processing)
    if BOT.Mode.ytdl_hard and not is_dir:
        expanded_sources = []
        for link in BOT.SOURCE:
            if is_ytdl_link(link):
                expanded = expand_playlist_urls(link)
                expanded_sources.extend(expanded)
            else:
                expanded_sources.append(link)
        if len(expanded_sources) > len(BOT.SOURCE):
            logging.info(f"Expanded {len(BOT.SOURCE)} links to {len(expanded_sources)} videos for sequential processing")
        BOT.SOURCE = expanded_sources
    
    # Reset Texts
    Messages.download_name = ""
    Messages.task_msg = f"<b>🦞 TASK MODE » </b>"
    
    # Set mode-specific task description
    if is_subex:
        mode_desc = "Subtitle Extraction"
    elif BOT.Mode.ytdl_hard:
        mode_desc = "YTDL Hardcode Subtitles"
    else:
        mode_desc = f"{BOT.Mode.type.capitalize()} {BOT.Mode.mode.capitalize()} as {BOT.Setting.stream_upload}"
    
    Messages.dump_task = (
        Messages.task_msg
        + f"<i>{mode_desc}</i>\n\n<b>🖇️ SOURCES » </b>"
    )
    Transfer.sent_file = []
    Transfer.sent_file_names = []
    Transfer.down_bytes = [0, 0]
    Transfer.up_bytes = [0, 0]
    Messages.download_name = ""
    Messages.task_msg = ""
    
    # Set mode-specific status header
    if is_subex:
        Messages.status_head = f"<b>💎 SUBTITLE EXTRACTION » </b>\n"
    elif BOT.Mode.ytdl_hard:
        Messages.status_head = f"<b>🔥 YTDL HARDCODE » </b>\n"
    else:
        Messages.status_head = f"<b>📥 DOWNLOADING » </b>\n"
    
    # Reset Paths.down_path to default (prevents state persistence from previous dir-leech tasks)
    Paths.down_path = f"{Paths.WORK_PATH}/Downloads"

    if is_dir:
        if not ospath.exists(BOT.SOURCE[0]):
            TaskError.state = True
            TaskError.text = "Task Failed. Because: Provided Directory Path Not Exists"
            logging.error(TaskError.text)
            return
        if not ospath.exists(Paths.temp_dirleech_path):
            makedirs(Paths.temp_dirleech_path)
        Messages.dump_task += f"\n\n📂 <code>{BOT.SOURCE[0]}</code>"
        Transfer.total_down_size = getSize(BOT.SOURCE[0])
        Messages.download_name = ospath.basename(BOT.SOURCE[0])
    else:
        for link in BOT.SOURCE:
            if is_telegram(link):
                ida = "💬"
            elif is_google_drive(link):
                ida = "♻️"
            elif is_torrent(link):
                ida = "🧲"
                Messages.caution_msg = "\n\n⚠️<i><b> Torrents Are Strictly Prohibited in Google Colab</b>, Try to avoid Magnets !</i>"
            elif is_ytdl_link(link):
                ida = "🏮"
            elif is_terabox(link):
                ida = "🍑"
            elif is_mega(link):
                ida = "💾"
            else:
                ida = "🔗"
            code_link = f"\n\n{ida} <code>{link}</code>"
            if len(Messages.dump_task + code_link) >= 4096:
                src_text.append(Messages.dump_task)
                Messages.dump_task = code_link
            else:
                Messages.dump_task += code_link

    # Get the current date and time in the specified time zone
    cdt = datetime.now(pytz.timezone("Asia/Kolkata"))
    dt = cdt.strftime(" %d-%m-%Y")
    Messages.dump_task += f"\n\n<b>📆 Task Date » </b><i>{dt}</i>"

    src_text.append(Messages.dump_task)

    if ospath.exists(Paths.WORK_PATH):
        shutil.rmtree(Paths.WORK_PATH)
    
    makedirs(Paths.WORK_PATH)
    
    # Only create down_path if it's inside WORK_PATH (not for dir-leech where it's the Drive folder)
    if not is_dir:
        makedirs(Paths.down_path)
    
    Messages.link_p = str(DUMP_ID)[4:]

    try:
        system(f"aria2c -d {Paths.WORK_PATH} -o Hero.jpg {Aria2c.pic_dwn_url}")
    except Exception:
        Paths.HERO_IMAGE = Paths.DEFAULT_HERO

    MSG.sent_msg = await colab_bot.send_message(chat_id=DUMP_ID, text=src_text[0])

    if len(src_text) > 1:
        for lin in range(1, len(src_text)):
            MSG.sent_msg = await MSG.sent_msg.reply_text(text=src_text[lin], quote=True)

    Messages.src_link = f"https://t.me/c/{Messages.link_p}/{MSG.sent_msg.id}"
    
    # Set task message based on mode
    if is_subex:
        Messages.task_msg += f"__[Subtitle Extraction]({Messages.src_link})__\n\n"
    else:
        Messages.task_msg += f"__[{BOT.Mode.type.capitalize()} {BOT.Mode.mode.capitalize()} as {BOT.Setting.stream_upload}]({Messages.src_link})__\n\n"

    await MSG.status_msg.delete()
    img = Paths.THMB_PATH if ospath.exists(Paths.THMB_PATH) else Paths.HERO_IMAGE
    
    # Set initial status text based on mode
    if is_subex and is_dir:
        initial_status = f"\n💎 __Processing directory...__"
    elif is_subex:
        initial_status = f"\n💎 __Starting download for extraction...__"
    else:
        initial_status = f"\n📝 __Starting DOWNLOAD...__"
    
    MSG.status_msg = await colab_bot.send_photo(  # type: ignore
        chat_id=OWNER,
        photo=img,
        caption=Messages.task_msg
        + Messages.status_head
        + initial_status
        + sysINFO(),
        reply_markup=keyboard(),
    )

    await calDownSize(BOT.SOURCE)

    if not is_dir:
        await get_d_name(BOT.SOURCE[0])
    else:
        Messages.download_name = ospath.basename(BOT.SOURCE[0])

    if is_zip:
        Paths.down_path = ospath.join(Paths.down_path, Messages.download_name)
        if not ospath.exists(Paths.down_path):
            makedirs(Paths.down_path)

    BotTimes.current_time = time()

    if BOT.Mode.mode == "subex":
        await Do_Leech(BOT.SOURCE, is_dir, BOT.Mode.ytdl, False, False, False)
    elif BOT.Mode.mode != "mirror":
        await Do_Leech(BOT.SOURCE, is_dir, BOT.Mode.ytdl, is_zip, is_unzip, is_dualzip)
    else:
        await Do_Mirror(BOT.SOURCE, BOT.Mode.ytdl, is_zip, is_unzip, is_dualzip)


async def Do_Leech(source, is_dir, is_ytdl, is_zip, is_unzip, is_dualzip):
    if is_dir:
        for folder_idx, s in enumerate(source, 1):
            if not ospath.exists(s):
                logging.error("Provided directory does not exist !")
                await cancelTask("Provided directory does not exist !")
                return
            
            logging.info(f"Processing folder {folder_idx}/{len(source)}: {s}")
            Messages.download_name = ospath.basename(s)
            Paths.down_path = s
            
            if is_zip:
                # Individual file zipping for sequential processing
                # Pass remove=False to KEEP original Drive files, only delete Colab temp files
                await IndividualZipLeech(Paths.down_path, False)
            elif is_unzip:
                await Unzip_Handler(Paths.down_path, False)
                await Leech(Paths.temp_unzip_path, True)
            elif is_dualzip:
                await Unzip_Handler(Paths.down_path, False)
                await Zip_Handler(Paths.temp_unzip_path, True, True)
                await Leech(Paths.temp_zpath, True)
            else:
                if ospath.isdir(s):
                    if BOT.Mode.mode == "subex":
                        await SubLeech(Paths.down_path, False)
                    else:
                        await Leech(Paths.down_path, False)
                else:
                    Transfer.total_down_size = ospath.getsize(s)
                    makedirs(Paths.temp_dirleech_path)
                    shutil.copy(s, Paths.temp_dirleech_path)
                    Messages.download_name = ospath.basename(s)
                    if BOT.Mode.mode == "subex":
                        await SubLeech(Paths.temp_dirleech_path, True)
                    else:
                        await Leech(Paths.temp_dirleech_path, True)
            
            # Cleanup BOT_WORK between folders to free space
            if ospath.exists(Paths.temp_zpath):
                shutil.rmtree(Paths.temp_zpath)
            if ospath.exists(Paths.temp_unzip_path):
                shutil.rmtree(Paths.temp_unzip_path)
            if ospath.exists(Paths.temp_dirleech_path):
                shutil.rmtree(Paths.temp_dirleech_path)
            
            logging.info(f"Completed folder {folder_idx}/{len(source)}: {ospath.basename(s)}")
    else:
        # SEQUENTIAL PROCESSING: Download -> Upload -> Cleanup for each link
        total_links = len(source)
        for link_idx, link in enumerate(source, 1):
            logging.info(f"[Sequential] Processing link {link_idx}/{total_links}: {link[:50]}...")
            
            # Reset download path for this link
            Paths.down_path = f"{Paths.WORK_PATH}/Downloads"
            if ospath.exists(Paths.down_path):
                shutil.rmtree(Paths.down_path)
            makedirs(Paths.down_path)
            
            # Get download name for this specific link
            await get_d_name(link)
            
            # If zip mode, create subfolder for this link
            if is_zip:
                Paths.down_path = ospath.join(Paths.down_path, Messages.download_name)
                if not ospath.exists(Paths.down_path):
                    makedirs(Paths.down_path)
            
            # Download this single link
            await downloadManager([link], is_ytdl, link_idx)
            
            Transfer.total_down_size = getSize(Paths.down_path)
            
            # Renaming Files With Custom Name
            applyCustomName()
            
            # Process and Upload this link
            if is_zip:
                await Zip_Handler(Paths.down_path, True, True)
                await Leech(Paths.temp_zpath, True)
            elif is_unzip:
                await Unzip_Handler(Paths.down_path, True)
                await Leech(Paths.temp_unzip_path, True)
            elif is_dualzip:
                await Unzip_Handler(Paths.down_path, True)
                await Zip_Handler(Paths.temp_unzip_path, True, True)
                await Leech(Paths.temp_zpath, True)
            elif BOT.Mode.mode == "subex":
                await SubLeech(Paths.down_path, True)
            else:
                await Leech(Paths.down_path, True)
            
            # Cleanup after this link before next iteration
            logging.info(f"[Sequential] Cleanup after link {link_idx}/{total_links}")
            if ospath.exists(Paths.down_path):
                shutil.rmtree(Paths.down_path)
            if ospath.exists(Paths.temp_zpath):
                shutil.rmtree(Paths.temp_zpath)
            if ospath.exists(Paths.temp_unzip_path):
                shutil.rmtree(Paths.temp_unzip_path)
            if ospath.exists(Paths.temp_files_dir):
                shutil.rmtree(Paths.temp_files_dir)
            
            logging.info(f"[Sequential] Completed link {link_idx}/{total_links}")

    await SendLogs(True)


async def Do_Mirror(source, is_ytdl, is_zip, is_unzip, is_dualzip):
    if not ospath.exists(Paths.MOUNTED_DRIVE):
        await cancelTask(
            "Google Drive is NOT MOUNTED ! Stop the Bot and Run the Google Drive Cell to Mount, then Try again !"
        )
        return

    if not ospath.exists(Paths.mirror_dir):
        makedirs(Paths.mirror_dir)

    # SEQUENTIAL PROCESSING: Download -> Mirror -> Cleanup for each link
    total_links = len(source)
    for link_idx, link in enumerate(source, 1):
        logging.info(f"[Sequential Mirror] Processing link {link_idx}/{total_links}: {link[:50]}...")
        
        # Reset download path for this link
        Paths.down_path = f"{Paths.WORK_PATH}/Downloads"
        if ospath.exists(Paths.down_path):
            shutil.rmtree(Paths.down_path)
        makedirs(Paths.down_path)
        
        # Get download name for this specific link
        await get_d_name(link)
        
        # Download this single link
        await downloadManager([link], is_ytdl, link_idx)

        Transfer.total_down_size = getSize(Paths.down_path)

        applyCustomName()

        cdt = datetime.now()
        cdt_ = cdt.strftime(f"Link{str(link_idx).zfill(2)}_%Y-%m-%d_%H-%M-%S")
        mirror_dir_ = ospath.join(Paths.mirror_dir, cdt_)

        if is_zip:
            await Zip_Handler(Paths.down_path, True, True)
            shutil.copytree(Paths.temp_zpath, mirror_dir_)
        elif is_unzip:
            await Unzip_Handler(Paths.down_path, True)
            shutil.copytree(Paths.temp_unzip_path, mirror_dir_)
        elif is_dualzip:
            await Unzip_Handler(Paths.down_path, True)
            await Zip_Handler(Paths.temp_unzip_path, True, True)
            shutil.copytree(Paths.temp_zpath, mirror_dir_)
        else:
            shutil.copytree(Paths.down_path, mirror_dir_)
        
        # Cleanup after this link before next iteration
        logging.info(f"[Sequential Mirror] Cleanup after link {link_idx}/{total_links}")
        if ospath.exists(Paths.down_path):
            shutil.rmtree(Paths.down_path)
        if ospath.exists(Paths.temp_zpath):
            shutil.rmtree(Paths.temp_zpath)
        if ospath.exists(Paths.temp_unzip_path):
            shutil.rmtree(Paths.temp_unzip_path)
        
        logging.info(f"[Sequential Mirror] Completed link {link_idx}/{total_links}")

    await SendLogs(False)
