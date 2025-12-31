# copyright 2023 © Xron Trix | https://github.com/Xrontrix10


import os
import shutil
import logging
import pathlib
from asyncio import sleep
from time import time
from colab_leecher import OWNER, DUMP_ID, colab_bot
from natsort import natsorted
from datetime import datetime
from os import makedirs, path as ospath
from colab_leecher.uploader.telegram import upload_file
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from colab_leecher.utility.variables import (
    BOT,
    MSG,
    BotTimes,
    Messages,
    Paths,
    Transfer,
)
from colab_leecher.utility.converters import (
    archive,
    extract,
    videoConverter,
    sizeChecker,
)
from colab_leecher.utility.helper import (
    fileType,
    getSize,
    getTime,
    keyboard,
    shortFileName,
    sizeUnit,
    sysINFO,
    load_upload_log,
    save_to_upload_log,
    is_already_uploaded,
    check_disk_space,
    format_elapsed_time,
)


async def Leech(folder_path: str, remove: bool):
    global BOT, BotTimes, Messages, Paths, Transfer
    files = [str(p) for p in pathlib.Path(folder_path).glob("**/*") if p.is_file()]
    for f in natsorted(files):
        file_path = ospath.join(folder_path, f)

        # Converting Video Files
        if BOT.Options.convert_video and fileType(file_path) == "video":
            file_path = await videoConverter(file_path)

    Transfer.total_down_size = getSize(folder_path)

    files = [str(p) for p in pathlib.Path(folder_path).glob("**/*") if p.is_file()]
    for f in natsorted(files):
        file_path = ospath.join(folder_path, f)

        leech = await sizeChecker(file_path, remove)

        if leech:  # File was splitted
            if ospath.exists(file_path) and remove:
                os.remove(file_path)  # Delete original Big Zip file

            dir_list = natsorted(os.listdir(Paths.temp_zpath))

            count = 1

            for dir_path in dir_list:
                short_path = ospath.join(Paths.temp_zpath, dir_path)
                file_name = ospath.basename(short_path)
                new_path = shortFileName(short_path)
                os.rename(short_path, new_path)
                BotTimes.current_time = time()
                Messages.status_head = f"<b>📤 UPLOADING SPLIT » {count} OF {len(dir_list)} Files</b>\n\n<code>{file_name}</code>\n"
                try:
                    MSG.status_msg = await MSG.status_msg.edit_text(
                        text=Messages.task_msg
                        + Messages.status_head
                        + "\n⏳ __Starting.....__"
                        + sysINFO(),
                        reply_markup=keyboard(),
                    )
                except Exception as d:
                    logging.info(d)
                await upload_file(new_path, file_name)
                Transfer.up_bytes.append(os.stat(new_path).st_size)

                count += 1

            shutil.rmtree(Paths.temp_zpath)

        else:
            if not ospath.exists(Paths.temp_files_dir): # Create Directory
                makedirs(Paths.temp_files_dir)

            if not remove:  # Copy To Temp Dir for Renaming Purposes
                file_path = shutil.copy(file_path, Paths.temp_files_dir)
            file_name = ospath.basename(file_path)
            # Trimming filename upto 50 chars
            new_path = shortFileName(file_path)
            os.rename(file_path, new_path)
            BotTimes.current_time = time()
            Messages.status_head = (
                f"<b>📤 UPLOADING » </b>\n\n<code>{file_name}</code>\n"
            )
            try:
                MSG.status_msg = await MSG.status_msg.edit_text(
                    text=Messages.task_msg
                    + Messages.status_head
                    + "\n⏳ __Starting.....__"
                    + sysINFO(),
                    reply_markup=keyboard(),
                )
            except Exception as d:
                logging.error(f"Error updating status bar: {d}")
            file_size = os.stat(new_path).st_size
            await upload_file(new_path, file_name)
            Transfer.up_bytes.append(file_size)

            if remove:
                if ospath.exists(new_path):
                    os.remove(new_path)
            else:
                for file in os.listdir(Paths.temp_files_dir):
                    os.remove(ospath.join(Paths.temp_files_dir, file))

    if remove and ospath.exists(folder_path):
        shutil.rmtree(folder_path)
    if ospath.exists(Paths.thumbnail_ytdl):
        shutil.rmtree(Paths.thumbnail_ytdl)
    if ospath.exists(Paths.temp_files_dir):
        shutil.rmtree(Paths.temp_files_dir)


async def Zip_Handler(down_path: str, is_split: bool, remove: bool):
    global BOT, Messages, MSG, Transfer

    Messages.status_head = (
        f"<b>🔐 ZIPPING » </b>\n\n<code>{Messages.download_name}</code>\n"
    )

    try:
        MSG.status_msg = await MSG.status_msg.edit_text(
            text=Messages.task_msg + Messages.status_head + sysINFO(),
            reply_markup=keyboard(),
        )
    except Exception as e2:
        logging.error(f"Problem in ZipLeech !{e2}")

    logging.info("\nNow ZIPPING the folder...")
    BotTimes.current_time = time()
    if not ospath.exists(Paths.temp_zpath):
        makedirs(Paths.temp_zpath)
    await archive(down_path, is_split, remove)

    await sleep(2)  # Time for renmaing newly created archives

    Transfer.total_down_size = getSize(Paths.temp_zpath)

    if remove and ospath.exists(down_path):
        shutil.rmtree(down_path)


async def IndividualZipLeech(folder_path: str, remove: bool):
    """
    Process each file in folder_path individually:
    1. Zip the file
    2. Split if > 1.8GB
    3. Upload split parts
    4. Delete zip and parts before moving to next file
    5. Save to upload log for resume capability
    """
    global BOT, BotTimes, Messages, Paths, Transfer

    # Check disk space before starting
    disk_ok, free_gb = check_disk_space(5.0)
    if not disk_ok:
        logging.warning(f"Low disk space warning: {free_gb}GB free")
        try:
            await MSG.status_msg.edit_text(
                text=f"⚠️ <b>LOW DISK SPACE WARNING</b>\n\nOnly {free_gb}GB free. Recommend > 5GB.\n\nContinuing anyway...",
                reply_markup=keyboard(),
            )
        except:
            pass
    
    # Start timer for summary
    start_time = time()
    total_size_uploaded = 0

    # Load already-uploaded files for resume capability (log stored in source folder)
    uploaded_files = load_upload_log(folder_path)
    
    # Exclude log files from processing
    files = [str(p) for p in pathlib.Path(folder_path).glob("**/*") 
             if p.is_file() and not p.name.startswith('.upload_log')]
    folder_name = ospath.basename(folder_path)
    total_files = len(files)
    skipped_count = 0
    uploaded_parts_list = []  # Track uploaded parts for index

    # Send folder header message to dump channel
    folder_size = getSize(folder_path)
    header_msg = (
        f"\n\n📂 <b>FOLDER: {folder_name}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 Files: {total_files}\n"
        f"💾 Size: {sizeUnit(folder_size)}\n"
        f"📍 Path: <code>{folder_path}</code>\n"
    )
    try:
        await colab_bot.send_message(DUMP_ID, header_msg)
        logging.info(f"Sent folder header for: {folder_name}")
    except Exception as e:
        logging.error(f"Error sending folder header: {e}")

    for idx, f in enumerate(natsorted(files), 1):
        file_path = f
        file_name = ospath.basename(file_path)

        # Skip already uploaded files (resume capability)
        if is_already_uploaded(file_path, uploaded_files):
            logging.info(f"SKIPPING (already uploaded): {file_name}")
            skipped_count += 1
            continue

        logging.info(f"Processing file {idx}/{total_files}: {file_name}")

        # Update status
        Messages.status_head = f"<b>📦 PROCESSING » </b>\n\n<code>{file_name}</code>\n<i>File {idx} of {total_files}</i>\n"
        try:
            MSG.status_msg = await MSG.status_msg.edit_text(
                text=Messages.task_msg + Messages.status_head + "\n⏳ __Starting...__" + sysINFO(),
                reply_markup=keyboard(),
            )
        except Exception as e:
            logging.error(f"Error updating status: {e}")

        # Create temp directory for zipping
        if not ospath.exists(Paths.temp_zpath):
            makedirs(Paths.temp_zpath)

        # Zip this individual file
        Messages.download_name = file_name
        BotTimes.current_time = time()
        await archive(file_path, True, False)  # is_split=True, remove=False (we handle removal later)

        await sleep(1)

        # Get all created zip parts
        zip_files = natsorted(os.listdir(Paths.temp_zpath))
        Transfer.total_down_size = getSize(Paths.temp_zpath)

        # Upload each part
        for part_idx, zip_part in enumerate(zip_files, 1):
            part_path = ospath.join(Paths.temp_zpath, zip_part)
            part_name = zip_part

            BotTimes.current_time = time()
            Messages.status_head = f"<b>📤 UPLOADING » {part_idx} OF {len(zip_files)}</b>\n\n<code>{part_name}</code>\n"
            try:
                MSG.status_msg = await MSG.status_msg.edit_text(
                    text=Messages.task_msg + Messages.status_head + "\n⏳ __Starting...__" + sysINFO(),
                    reply_markup=keyboard(),
                )
            except Exception as e:
                logging.error(f"Error updating status: {e}")

            await upload_file(part_path, part_name)
            part_size = os.stat(part_path).st_size
            Transfer.up_bytes.append(part_size)
            Transfer.sent_file_names.append(part_name)
            total_size_uploaded += part_size
            uploaded_parts_list.append(part_name)  # Track for index

            # Delete part after upload
            os.remove(part_path)
            logging.info(f"Deleted uploaded part: {part_name}")

        # Clear temp zip directory
        if ospath.exists(Paths.temp_zpath):
            shutil.rmtree(Paths.temp_zpath)

        # Save to upload log for resume capability (log stored in source folder)
        save_to_upload_log(folder_path, file_path)

        # Remove original file if requested
        if remove and ospath.exists(file_path):
            os.remove(file_path)
            logging.info(f"Deleted original file: {file_name}")

    # Calculate elapsed time
    end_time = time()
    elapsed_seconds = end_time - start_time
    elapsed_str = format_elapsed_time(elapsed_seconds)
    
    # Summary
    uploaded_count = total_files - skipped_count
    summary_msg = (
        f"\n\n<b>📊 SUMMARY</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📁 Folder: <code>{folder_name}</code>\n"
        f"📦 Total Files: {total_files}\n"
        f"✅ Uploaded: {uploaded_count}\n"
        f"⏭️ Skipped: {skipped_count}\n"
        f"💾 Total Size: {sizeUnit(total_size_uploaded)}\n"
        f"⏱️ Time: {elapsed_str}\n"
    )
    
    try:
        await MSG.status_msg.edit_text(
            text=Messages.task_msg + summary_msg + sysINFO(),
            reply_markup=keyboard(),
        )
    except Exception as e:
        logging.error(f"Error showing summary: {e}")
    
    logging.info(f"Completed: {uploaded_count} uploaded, {skipped_count} skipped, {elapsed_str}")

    # Send index message to dump channel
    if uploaded_parts_list:
        index_lines = [f"{i}. {name}" for i, name in enumerate(uploaded_parts_list, 1)]
        # Split into chunks of 50 if too many files
        for chunk_start in range(0, len(index_lines), 50):
            chunk = index_lines[chunk_start:chunk_start + 50]
            chunk_num = (chunk_start // 50) + 1
            total_chunks = (len(index_lines) + 49) // 50
            
            index_msg = (
                f"\n\n📋 <b>INDEX - {folder_name}</b>"
                + (f" (Part {chunk_num}/{total_chunks})" if total_chunks > 1 else "") + "\n"
                f"━━━━━━━━━━━━━━━\n"
                + "\n".join(chunk) + "\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✅ Total: {len(uploaded_parts_list)} parts uploaded\n"
            )
            try:
                await colab_bot.send_message(DUMP_ID, index_msg)
                logging.info(f"Sent index message for: {folder_name}")
            except Exception as e:
                logging.error(f"Error sending index: {e}")

    # Cleanup folder if empty and remove requested
    if remove and ospath.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            logging.error(f"Could not remove folder: {e}")



async def Unzip_Handler(down_path: str, remove: bool):
    global MSG, Messages

    Messages.status_head = (
        f"\n<b>📂 EXTRACTING » </b>\n\n<code>{Messages.download_name}</code>\n"
    )

    MSG.status_msg = await MSG.status_msg.edit_text(
        text=Messages.task_msg
        + Messages.status_head
        + "\n⏳ __Starting.....__"
        + sysINFO(),
        reply_markup=keyboard(),
    )
    filenames = [str(p) for p in pathlib.Path(down_path).glob("**/*") if p.is_file()]
    for f in natsorted(filenames):
        short_path = ospath.join(down_path, f)
        if not ospath.exists(Paths.temp_unzip_path):
            makedirs(Paths.temp_unzip_path)
        filename = ospath.basename(f).lower()
        _, ext = ospath.splitext(filename)
        try:
            if ospath.exists(short_path):
                if ext in [".7z", ".gz", ".zip", ".rar", ".001", ".tar", ".z01"]:
                    await extract(short_path, remove)
                else:
                    shutil.copy(short_path, Paths.temp_unzip_path)
        except Exception as e5:
            logging.error(f"UZLeech Launcher Exception: {e5}")

    if remove:
        shutil.rmtree(down_path)


async def cancelTask(Reason: str):
    text = f"#TASK_STOPPED\n\n**╭🔗 Source » **__[Here]({Messages.src_link})__\n**├🦄 Mode » **__{BOT.Mode.mode.capitalize()}__\n**├🤔 Reason » **__{Reason}__\n**╰🍃 Spent Time » **__{getTime((datetime.now() - BotTimes.start_time).seconds)}__"
    if BOT.State.task_going:
        try:
            BOT.TASK.cancel()  # type: ignore
            shutil.rmtree(Paths.WORK_PATH)
        except Exception as e:
            logging.error(f"Error Deleting Task Folder: {e}")
        else:
            logging.info(f"On-Going Task Cancelled !")
        finally:
            BOT.State.task_going = False
            await MSG.status_msg.delete()
            await colab_bot.send_message(
                chat_id=OWNER,
                text=text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(  # Opens a web URL
                                "Channel 📣",
                                url="https://t.me/Colab_Leecher",
                            ),
                            InlineKeyboardButton(  # Opens a web URL
                                "Group 💬",
                                url="https://t.me/Colab_Leecher_Discuss",
                            ),
                        ],
                    ]
                ),
            )


async def SendLogs(is_leech: bool):
    global Transfer, Messages
    final_text = f"<b>☘️ File Count:</b>  <code>{len(Transfer.sent_file)}</code>\n\n<b>📜 Logs:</b>\n"
    l_ink = "⌬─────[「 Colab Usage 」](https://colab.research.google.com/drive/12hdEqaidRZ8krqj7rpnyDzg1dkKmvdvp)─────⌬"

    if is_leech:
        file_count = (
            f"├<b>☘️ File Count » </b><code>{len(Transfer.sent_file)} Files</code>\n"
        )
    else:
        file_count = ""

    size = (
        sizeUnit(sum(Transfer.up_bytes))
        if is_leech
        else sizeUnit(Transfer.total_down_size)
    )

    last_text = (
        f"\n\n<b>#{(BOT.Mode.mode).upper()}_COMPLETE 🔥</b>\n\n"
        + f"╭<b>📛 Name » </b><code>{Messages.download_name}</code>\n"
        + f"├<b>📦 Size » </b><code>{size}</code>\n"
        + file_count
        + f"╰<b>🍃 Saved Time »</b> <code>{getTime((datetime.now() - BotTimes.start_time).seconds)}</code>"
    )

    if BOT.State.task_going:
        await MSG.sent_msg.reply_text(
            text=f"**SOURCE »** __[Here]({Messages.src_link})__" + last_text
        )
        await MSG.status_msg.edit_text(
            text=Messages.task_msg + l_ink + last_text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Git Repo 🪲",
                            url="https://github.com/ajithvnr2001/tele-leech-new",
                        ),
                    ],
                    [
                        InlineKeyboardButton(  # Opens a web URL
                            "Channel 📣",
                            url="https://t.me/Colab_Leecher",
                        ),
                        InlineKeyboardButton(  # Opens a web URL
                            "Group 💬",
                            url="https://t.me/Colab_Leecher_Discuss",
                        ),
                    ],
                ]
            ),
        )

        if is_leech:
            try:
                final_texts = []
                for i in range(len(Transfer.sent_file)):
                    file_link = (
                        f"https://t.me/c/{Messages.link_p}/{Transfer.sent_file[i].id}"
                    )
                    fileName = Transfer.sent_file_names[i]
                    fileText = (
                        f"\n({str(i+1).zfill(2)}) <a href={file_link}>{fileName}</a>"
                    )
                    if len(final_text + fileText) >= 4096:
                        final_texts.append(final_text)
                        final_text = fileText
                    else:
                        final_text += fileText
                final_texts.append(final_text)

                for fn_txt in final_texts:
                    MSG.status_msg = await MSG.status_msg.reply_text(text=fn_txt)
            except Exception as e:
                Err = f"<b>Error Sending logs » </b><i>{e}</i>"
                Err += f"\n\n<i>⚠️ If You are Unknown with this **ERROR**, Then Forward This Message in [Colab Leecher Discussion](https://t.me/Colab_Leecher_Discuss) Where [Xron Trix](https://t.me/XronTrix) may fix it</i>"
                await MSG.status_msg.reply_text(text=Err)

    BOT.State.started = False
    BOT.State.task_going = False
