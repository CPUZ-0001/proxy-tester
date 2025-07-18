import logging
import uuid
import os
from pymongo import MongoClient
from telegram.error import BadRequest
from telegram import ReplyKeyboardRemove
from telegram.error import Forbidden
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    Message,   # ✅ Add this
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

load_dotenv()

# ========== ENV CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
DUMP_CHANNEL_ID = int(os.getenv("DUMP_CHANNEL_ID"))
PUBLIC_CHANNEL_ID = int(os.getenv("PUBLIC_CHANNEL_ID"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "Movie"
COLLECTION = "movies"
ALL_USERS_COLLECTION = "users"

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO)

# ========== MONGO SETUP ==========
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
movie_collection = db[COLLECTION]
all_users_collection = db[ALL_USERS_COLLECTION]

# ========== IN-MEMORY CACHE ==========
pending_posts = {}  # user_id -> {file_id, file_type, poster}
posters = {}        # user_id -> {caption, photo_id}

# ========== START COMMAND ==========
BOT_VERSION = "1.0"  # Add this near the top with your config

async def is_user_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=PUBLIC_CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Forbidden:
        return False  # Bot not admin in channel
    except:
        return False

# ========== UTILS ==========
def generate_code():
    while True:
        code = uuid.uuid4().hex[:8].upper()
        if not movie_collection.find_one({"code": code}):
            return code

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # ✅ Save user if new
    if not all_users_collection.find_one({"user_id": user_id}):
        all_users_collection.insert_one({"user_id": user_id})

    # Check for deep link code
    args = context.args
    if args:
        code = args[0]

        # 🔐 Check if user has joined the channel
        if not await is_user_joined(context.bot, user_id):
            await update.message.reply_text(
                f"🔒 **Please join [MovieHub™]({CHANNEL_LINK}) to access this content.**",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            return

        movie = movie_collection.find_one({"code": code})
        if movie:
            file_type = movie["file_type"]
            file_id = movie["file_id"]
            if file_type == "document":
                await update.message.reply_document(file_id)
            else:
                await update.message.reply_video(file_id)
        else:
            await update.message.reply_text("⚠️ This link is invalid or expired.")
        return

    # Admin welcome
    if user_id in ADMIN_IDS:
        await update.message.reply_text(
            "🎬 Send a movie poster first (with optional caption), then the movie file."
        )
        return

    # User welcome
    await update.message.reply_text(
        f"**🎬 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 𝐌𝐨𝐯𝐢𝐞𝐇𝐮𝐛™ – 𝐘𝐨𝐮𝐫 𝐔𝐥𝐭𝐢𝐦𝐚𝐭𝐞 𝐌𝐨𝐯𝐢𝐞 𝐃𝐞𝐬𝐭𝐢𝐧𝐚𝐭𝐢𝐨𝐧!**\n"
        f"**🤖 𝐕𝐞𝐫𝐬𝐢𝐨𝐧: {BOT_VERSION}**\n\n"
        f"**🎞️ 𝐒𝐭𝐚𝐲 𝐭𝐮𝐧𝐞𝐝 𝐟𝐨𝐫 𝐭𝐡𝐞 𝐥𝐚𝐭𝐞𝐬𝐭 𝐝𝐫𝐨𝐩𝐬 𝐨𝐧 𝐨𝐮𝐫 [𝐜𝐡𝐚𝐧𝐧𝐞𝐥]({CHANNEL_LINK})!**",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


# ========== POSTER HANDLER ==========
async def handle_poster_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:

        return

    photo = update.message.photo[-1]
    caption = update.message.caption or ""  # Accept empty caption

    posters[user_id] = {
        "caption": caption,
        "photo_id": photo.file_id
    }

    await update.message.reply_text("✅ Poster saved. Now send the movie file (ZIP/video/document).")

# ========== MOVIE UPLOAD ==========
async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("🚫 You are not allowed to upload.")
        return

    file = update.message.video or update.message.document
    if not file:
        await update.message.reply_text("❗ Please send a valid video or document file.")
        return

    poster = posters.get(user.id)
    if not poster:
        await update.message.reply_text("❗ Please send the poster image first.")
        return

    pending_posts[user.id] = {
        "file_id": file.file_id,
        "file_type": "document" if update.message.document else "video",
        "poster": poster
    }

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("✅ Confirm Upload"), KeyboardButton("❌ Cancel Upload")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text("✅ File received. Choose an option:", reply_markup=keyboard)

# ========== HANDLE REPLY CHOICE ==========
async def handle_reply_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in ADMIN_IDS:

        await update.message.reply_text("🚫 Not authorized.")
        return

    if text == "✅ Confirm Upload":
        pending = pending_posts.get(user_id)
        if not pending:
            await update.message.reply_text("⚠️ No pending post to confirm.")
            return

        code = generate_code()

        # Send file to dump channel with file info
        dump_caption = (
            "🎬 Uploaded by Admin\n\n"
            f"Code: `{code}`\n"
            f"File ID: `{pending['file_id']}`\n"
            f"Type: `{pending['file_type']}`"
        )
        await context.bot.send_document(
            chat_id=DUMP_CHANNEL_ID,
            document=pending["file_id"],
            caption=dump_caption,
            parse_mode="Markdown"
        )

        # Save file details to MongoDB
        movie_collection.insert_one({
            "code": code,
            "file_id": pending["file_id"],
            "file_type": pending["file_type"]
        })

        # Generate deep link and publish to public channel
        bot_username = (await context.bot.get_me()).username
        deep_link = f"https://t.me/{bot_username}?start={code}"
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download Movie", url=deep_link)]
        ])

        base_caption = pending["poster"]["caption"]
        final_caption = (base_caption + "\n\n👇 Click below to download") if base_caption else "👇 Click below to download"

        await context.bot.send_photo(
            chat_id=PUBLIC_CHANNEL_ID,
            photo=pending["poster"]["photo_id"],
            caption=final_caption,
            reply_markup=button
        )

        # Notify and clean up
        await update.message.reply_text("✅ Uploaded successfully.", reply_markup=ReplyKeyboardRemove())
        posters.pop(user_id, None)
        pending_posts.pop(user_id, None)

    elif text == "❌ Cancel Upload":
        if pending_posts.pop(user_id, None):
            await update.message.reply_text("❌ Upload cancelled.", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("⚠️ No pending upload found.", reply_markup=ReplyKeyboardRemove())


# Broadcast command handler
async def broadcast_message(self, message: Message, user_id: int):
    """Send a message to a single user"""
    try:
        caption = message.caption if message.caption else None
        reply_markup = message.reply_markup if message.reply_markup else None

        if message.text:
            await self.app.send_message(
                chat_id=user_id,
                text=message.text,
                entities=message.entities,
                reply_markup=reply_markup,
                disable_notification=True
            )
        elif message.photo:
            await self.app.send_photo(
                chat_id=user_id,
                photo=message.photo.file_id,
                caption=caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup,
                disable_notification=True
            )
        elif message.video:
            await self.app.send_video(
                chat_id=user_id,
                video=message.video.file_id,
                caption=caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup,
                disable_notification=True
            )
        elif message.audio:
            await self.app.send_audio(
                chat_id=user_id,
                audio=message.audio.file_id,
                caption=caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup,
                disable_notification=True
            )
        elif message.document:
            await self.app.send_document(
                chat_id=user_id,
                document=message.document.file_id,
                caption=caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup,
                disable_notification=True
            )
        elif message.animation:
            await self.app.send_animation(
                chat_id=user_id,
                animation=message.animation.file_id,
                caption=caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup,
                disable_notification=True
            )
        elif message.sticker:
            await self.app.send_sticker(
                chat_id=user_id,
                sticker=message.sticker.file_id,
                disable_notification=True
            )
        elif message.voice:
            await self.app.send_voice(
                chat_id=user_id,
                voice=message.voice.file_id,
                caption=caption,
                caption_entities=message.caption_entities,
                reply_markup=reply_markup,
                disable_notification=True
            )
        elif message.video_note:
            await self.app.send_video_note(
                chat_id=user_id,
                video_note=message.video_note.file_id,
                disable_notification=True
            )

        return True, ""

    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await self.broadcast_message(message, user_id)
    
    except InputUserDeactivated:
        return False, "deactivated"
    except UserIsBlocked:
        return False, "blocked"
    except PeerIdInvalid:
        return False, "invalid_id"
    except Exception as e:
        return False, f"other:{str(e)}"

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    if user_id not in ADMIN_IDS:

        await message.reply_text("⛔️ You are not authorized to use this command!")
        return

    # Get the message to broadcast
    if message.reply_to_message:
        broadcast_content = message.reply_to_message
    elif context.args:
        broadcast_content = " ".join(context.args)
    else:
        await message.reply_text("❗️ Please reply to a message or type a message to broadcast.")
        return

    status_msg = await message.reply_text("🚀 Starting broadcast...")

    total_users = all_users_collection.count_documents({})
    done = success = failed = blocked = deleted = invalid = 0
    failed_users = []

    users_list = list(all_users_collection.find({}, {'user_id': 1}))

    for user in users_list:
        done += 1
        try:
            if isinstance(broadcast_content, str):
                await context.bot.send_message(chat_id=user['user_id'], text=broadcast_content)
            else:
                # **Forward the original message** with "forwarded from" header
                await context.bot.forward_message(
                    chat_id=user['user_id'],
                    from_chat_id=broadcast_content.chat.id,
                    message_id=broadcast_content.message_id
                )
            success += 1
        except TelegramError as e:
            failed += 1
            failed_users.append((user['user_id'], str(e)))
            if "blocked" in str(e):
                blocked += 1
            elif "deactivated" in str(e):
                deleted += 1
            elif "invalid" in str(e):
                invalid += 1

        if done % 20 == 0:
            try:
                await status_msg.edit_text(
                    f"🚀 Broadcast in Progress...\n\n"
                    f"👥 Total Users: {total_users}\n"
                    f"✅ Completed: {done} / {total_users}\n"
                    f"✨ Success: {success}\n"
                    f"⚠️ Failed: {failed}\n\n"
                    f"🚫 Blocked: {blocked}\n"
                    f"❗️ Deleted: {deleted}\n"
                    f"📛 Invalid: {invalid}"
                )
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ Broadcast Completed!\n"
        f"👥 Total Users: {total_users}\n"
        f"✨ Success: {success}\n"
        f"⚠️ Failed: {failed}\n"
        f"🚫 Blocked: {blocked}\n"
        f"❗️ Deleted: {deleted}\n"
        f"📛 Invalid: {invalid}"
    )

    if failed_users:
        clean_msg = await message.reply_text("🧹 Cleaning database... Removing invalid users.")
        invalid_user_ids = [uid for uid, _ in failed_users]
        result = all_users_collection.delete_many({"user_id": {"$in": invalid_user_ids}})
        await clean_msg.edit_text(f"🧹 Database cleaned! Removed {result.deleted_count} invalid users.")
# ========== BOT SETUP ==========
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_poster_photo))
app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO, handle_upload))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(✅ Confirm Upload|❌ Cancel Upload)$"), handle_reply_choice))


if __name__ == "__main__":
    print("✅ Movie bot is running with optional caption support!")
    app.run_polling()
