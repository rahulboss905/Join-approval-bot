import json
import os
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# === CONFIGURATION ===
API_ID = 23888050  # Replace with your API ID
API_HASH = "80679c77353535f9e13f10710a7feec9"
BOT_TOKEN = "7573448964:AAEiXXq6HoNzVLkC1XbdwVlyetABavGpBDM"
OWNER_ID = 7456681709  # Your Telegram user ID

DATA_FILE = "group_welcomes.json"
USERS_FILE = "users.json"
SUDO_FILE = "sudo.json"

bot = Client("join_approval_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === JSON HANDLERS ===
def load_json(file):
    return json.load(open(file)) if os.path.exists(file) else []

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def load_welcomes():
    return json.load(open(DATA_FILE)) if os.path.exists(DATA_FILE) else {}

def save_welcomes(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_sudo(user_id):
    return user_id == OWNER_ID or user_id in load_json(SUDO_FILE)

# === /START ===
@bot.on_message(filters.command("start") & filters.private)
async def start(bot, message: Message):
    users = load_json(USERS_FILE)
    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_json(USERS_FILE, users)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Join Updates Channel", url="https://t.me/ca_foundation_notess_network")],
        [InlineKeyboardButton("👥 Join Support Group", url="https://t.me/CAFNDLLcBATCH1JUNE2024STUDENTS")],
        [InlineKeyboardButton("➕ Add Me to Group", url=f"https://t.me/{bot.me.username}?startgroup=true")]
    ])

    await message.reply(
        "🤖 I'm a Global Join Approval Bot!\n\n"
        "➕ Add me to any group as admin to enable join request verification.\n"
        "👮 I will automatically verify users with a button.\n\n"
        "Use /help to see full commands.",
        reply_markup=keyboard
    )

# === /HELP ===
@bot.on_message(filters.command("help"))
async def help_cmd(bot, message: Message):
    help_text = (
        "🤖 **Join Approval Bot Help**\n\n"
        "**Commands:**\n"
        "`/start` - Bot info and links\n"
        "`/help` - Show this help\n"
        "`/setwelcome` - Set group welcome message (reply to a message)\n"
        "`/broadcast` - Send message to all users (sudo only)\n"
        "`/addsudo` - Add a sudo user (owner only)\n"
        "`/delsudo` - Remove a sudo user (owner only)\n"
        "`/sudolist` - View all sudo users\n\n"
        "**How It Works:**\n"
        "- User sends join request\n"
        "- Bot sends DM asking to verify\n"
        "- If verified, join is auto-approved!"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{bot.me.username}?startgroup=true")],
        [InlineKeyboardButton("📣 Updates", url="https://t.me/ca_foundation_notess_network")],
        [InlineKeyboardButton("👥 Support", url="https://t.me/CAFNDLLcBATCH1JUNE2024STUDENTS")]
    ])

    await message.reply(help_text, reply_markup=keyboard)

# === JOIN REQUEST HANDLER ===
@bot.on_chat_join_request()
async def on_join_request(bot, join_req: ChatJoinRequest):
    user = join_req.from_user
    chat = join_req.chat

    try:
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I'm not a robot", callback_data=f"verify_{user.id}_{chat.id}")]
        ])
        await bot.send_message(
            user.id,
            f"👋 Hi {user.first_name}!\nTo join **{chat.title}**, please verify you're human.\n\nClick below:",
            reply_markup=button
        )
    except Exception as e:
        print(f"[!] Cannot DM user {user.id}: {e}")

# === VERIFY CALLBACK ===
@bot.on_callback_query(filters.regex(r"verify_(\d+)_(\-?\d+)"))
async def on_verify(bot, query: CallbackQuery):
    user_id, chat_id = map(int, query.data.split("_")[1:])

    if query.from_user.id != user_id:
        return await query.answer("❌ This button is not for you!", show_alert=True)

    try:
        await bot.approve_chat_join_request(chat_id, user_id)

        welcomes = load_welcomes()
        welcome_msg = welcomes.get(str(chat_id), "🎉 You've been approved! Welcome!")

        await query.message.edit_text("✅ You are verified! Join request approved.")
        await bot.send_message(user_id, welcome_msg)

    except Exception as e:
        print(f"[!] Error approving user: {e}")
        await query.message.edit_text("❌ Something went wrong during approval.")

# === /SETWELCOME (Admins or Sudo Only) ===
@bot.on_message(filters.command("setwelcome") & filters.group)
async def set_welcome(bot, message: Message):
    user_id = message.from_user.id

    try:
        # Allow sudo OR group admins
        if not is_sudo(user_id):
            member = await bot.get_chat_member(message.chat.id, user_id)
            if member.status not in ("administrator", "creator"):
                return await message.reply("❌ Only group admins or sudo users can use this.")

        if not message.reply_to_message or not message.reply_to_message.text:
            return await message.reply("❗Reply to a message you want to set as welcome.")

        welcomes = load_welcomes()
        welcomes[str(message.chat.id)] = message.reply_to_message.text
        save_welcomes(welcomes)

        await message.reply("✅ Welcome message set for this group!")

    except Exception as e:
        print(f"[!] /setwelcome error: {e}")
        await message.reply("⚠️ Something went wrong.")

# === /BROADCAST ===
@bot.on_message(filters.command("broadcast"))
async def broadcast(bot, message: Message):
    if not is_sudo(message.from_user.id):
        return await message.reply("❌ You're not authorized to use this command.")

    if not message.reply_to_message:
        return await message.reply("❗Reply to a message to broadcast it.")

    text = message.reply_to_message.text
    sent, failed = 0, 0
    users = load_json(USERS_FILE)

    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except:
            failed += 1

    await message.reply(f"📣 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}")

# === /ADDSUDO ===
@bot.on_message(filters.command("addsudo") & filters.user(OWNER_ID))
async def add_sudo(bot, message: Message):
    if not message.reply_to_message:
        return await message.reply("❗Reply to the user you want to make sudo.")

    user_id = message.reply_to_message.from_user.id
    sudo = load_json(SUDO_FILE)

    if user_id in sudo:
        return await message.reply("⚠️ User is already sudo.")

    sudo.append(user_id)
    save_json(SUDO_FILE, sudo)
    await message.reply(f"✅ Added `{user_id}` to sudo list.")

# === /DELSUDO ===
@bot.on_message(filters.command("delsudo") & filters.user(OWNER_ID))
async def del_sudo(bot, message: Message):
    if not message.reply_to_message:
        return await message.reply("❗Reply to the sudo user you want to remove.")

    user_id = message.reply_to_message.from_user.id
    sudo = load_json(SUDO_FILE)

    if user_id not in sudo:
        return await message.reply("⚠️ User is not in sudo list.")

    sudo.remove(user_id)
    save_json(SUDO_FILE, sudo)
    await message.reply(f"✅ Removed `{user_id}` from sudo list.")

# === /SUDOLIST ===
@bot.on_message(filters.command("sudolist") & filters.user(OWNER_ID))
async def sudo_list(bot, message: Message):
    sudo = load_json(SUDO_FILE)
    if not sudo:
        return await message.reply("📭 No sudo users yet.")
    
    text = "**🧑‍💻 Sudo Users:**\n" + "\n".join([f"`{uid}`" for uid in sudo])
    await message.reply(text)

# === START BOT ===
print("🤖 Global Join Approval Bot Running...")
bot.run()
