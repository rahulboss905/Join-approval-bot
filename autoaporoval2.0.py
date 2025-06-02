import json
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatJoinRequest, Message

# --- CONFIGURATION ---
API_ID = 23888050  # Your API ID
API_HASH = "23888050"
BOT_TOKEN = "7672237545:AAFa1b7kyYv5tXEiR-mVwU8OWb7wp3F7lec"
OWNER_ID = 7456681709  # Your Telegram User ID

DATA_FILE = "group_welcomes.json"
USERS_FILE = "users.json"
SUDO_FILE = "sudo.json"

bot = Client("join_approval_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- JSON Helpers ---
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

def load_welcomes():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_welcomes(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_sudo(user_id):
    sudo_list = load_json(SUDO_FILE)
    return user_id == OWNER_ID or user_id in sudo_list

# --- Start command ---
@bot.on_message(filters.command("start") & filters.private)
async def start(bot, message: Message):
    users = load_json(USERS_FILE)
    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_json(USERS_FILE, users)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Updates", url="https://t.me/yourchannel")],
        [InlineKeyboardButton("👥 Support Group", url="https://t.me/your_support_group")],
        [InlineKeyboardButton("➕ Add Me to Group", url=f"https://t.me/{bot.me.username}?startgroup=true")]
    ])

    await message.reply(
        "🤖 Welcome! Add me as admin in your group to enable join approval.\n"
        "Use /help for commands.",
        reply_markup=keyboard
    )

# --- Help command ---
@bot.on_message(filters.command("help"))
async def help_cmd(bot, message: Message):
    await message.reply(
        "**Join Approval Bot Commands:**\n\n"
        "/setwelcome (reply to text) - Set welcome message (admin/sudo only)\n"
        "/getwelcome - Show current welcome message\n"
        "/broadcast (reply to message) - Send message to all users (sudo only)\n"
        "/addsudo (reply to user) - Add sudo user (owner only)\n"
        "/delsudo (reply to user) - Remove sudo user (owner only)\n"
        "/sudolist - List sudo users (owner only)\n"
    )

# --- Join request handler ---
@bot.on_chat_join_request()
async def handle_join_request(bot, join_req: ChatJoinRequest):
    user = join_req.from_user
    chat = join_req.chat

    try:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ I'm not a robot", callback_data=f"verify_{user.id}_{chat.id}")]]
        )
        await bot.send_message(
            user.id,
            f"Hi {user.first_name}! To join **{chat.title}**, please verify you are human.\n"
            "Click the button below:",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Failed to DM user {user.id}: {e}")
        # Optionally notify group or ignore

# --- Verification callback ---
@bot.on_callback_query(filters.regex(r"verify_(\d+)_(\-?\d+)"))
async def verify_user(bot, query: CallbackQuery):
    user_id, chat_id = map(int, query.data.split("_")[1:])
    if query.from_user.id != user_id:
        return await query.answer("This button is not for you!", show_alert=True)

    try:
        await bot.approve_chat_join_request(chat_id, user_id)
        welcomes = load_welcomes()
        welcome_msg = welcomes.get(str(chat_id), "🎉 Welcome to the group!")
        await query.message.edit_text("✅ You are verified! Join request approved.")
        await bot.send_message(user_id, welcome_msg)
    except Exception as e:
        print(f"Error approving user: {e}")
        await query.message.edit_text("❌ Failed to approve join request.")

# --- Set welcome message ---
@bot.on_message(filters.command("setwelcome") & filters.group)
async def set_welcome(bot, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("Reply to a **text message** to set as welcome.")

    # Check if sudo or admin
    if not is_sudo(user_id):
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status not in ["administrator", "creator"]:
                return await message.reply("You must be group admin or sudo to use this.")
        except Exception as e:
            print(f"Failed to get chat member: {e}")
            return await message.reply("Could not verify permissions.")

    welcomes = load_welcomes()
    welcomes[str(chat_id)] = message.reply_to_message.text
    save_welcomes(welcomes)
    await message.reply("✅ Welcome message saved!")

# --- Get welcome message ---
@bot.on_message(filters.command("getwelcome") & filters.group)
async def get_welcome(bot, message: Message):
    welcomes = load_welcomes()
    welcome_msg = welcomes.get(str(message.chat.id))
    if welcome_msg:
        await message.reply(f"Current welcome message:\n\n{welcome_msg}")
    else:
        await message.reply("No welcome message set for this group.")

# --- Broadcast command ---
@bot.on_message(filters.command("broadcast"))
async def broadcast(bot, message: Message):
    if not is_sudo(message.from_user.id):
        return await message.reply("You are not authorized to broadcast.")

    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("Reply to a message with text to broadcast.")

    users = load_json(USERS_FILE)
    sent = 0
    failed = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, message.reply_to_message.text)
            sent += 1
        except Exception:
            failed += 1

    await message.reply(f"Broadcast completed!\nSent: {sent}\nFailed: {failed}")

# --- Add sudo ---
@bot.on_message(filters.command("addsudo") & filters.user(OWNER_ID))
async def addsudo(bot, message: Message):
    if not message.reply_to_message:
        return await message.reply("Reply to the user to add as sudo.")

    user_id = message.reply_to_message.from_user.id
    sudo_list = load_json(SUDO_FILE)
    if user_id in sudo_list:
        return await message.reply("User is already sudo.")

    sudo_list.append(user_id)
    save_json(SUDO_FILE, sudo_list)
    await message.reply(f"User {user_id} added to sudo list.")

# --- Remove sudo ---
@bot.on_message(filters.command("delsudo") & filters.user(OWNER_ID))
async def delsudo(bot, message: Message):
    if not message.reply_to_message:
        return await message.reply("Reply to the sudo user to remove.")

    user_id = message.reply_to_message.from_user.id
    sudo_list = load_json(SUDO_FILE)
    if user_id not in sudo_list:
        return await message.reply("User is not in sudo list.")

    sudo_list.remove(user_id)
    save_json(SUDO_FILE, sudo_list)
    await message.reply(f"User {user_id} removed from sudo list.")

# --- List sudo users ---
@bot.on_message(filters.command("sudolist") & filters.user(OWNER_ID))
async def sudolist(bot, message: Message):
    sudo_list = load_json(SUDO_FILE)
    if not sudo_list:
        return await message.reply("No sudo users.")
    text = "**Sudo Users:**\n" + "\n".join(f"- `{uid}`" for uid in sudo_list)
    await message.reply(text)

print("Bot is running...")
bot.run()
