import sqlite3
import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# Flask app for Fake Port (24/7 uptime ke liye)
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running smoothly!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

TOKEN = "8726582370:AAFuaYEwsdUEdflaHxzd-XUCT2O6_Xo8fy8"
bot = telebot.TeleBot(TOKEN)

# Main Super Admin ID
SUPER_ADMIN_ID = 7691071175
FORCE_CHANNEL_ID = -1003923376846  
GC_INVITE_LINK = "https://t.me/+SPLleac6nY01ZTdh"

conn = sqlite3.connect("referra_l_bot.db", check_same_thread=False)
cursor = conn.cursor()

# Database Tables
cursor.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, referred_by INTEGER, ref_count INTEGER DEFAULT 0, reward_claimed INTEGER DEFAULT 0, submitted_id TEXT, is_banned INTEGER DEFAULT 0, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS bot_stats (key TEXT PRIMARY KEY, value INTEGER)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS promo_codes (code TEXT PRIMARY KEY, amount INTEGER)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS used_promos (user_id INTEGER, code TEXT, UNIQUE(user_id, code))""")
cursor.execute("""INSERT OR IGNORE INTO bot_stats (key, value) VALUES ('total_joins', 0)""")
cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUPER_ADMIN_ID,))
conn.commit()

user_state = {}
last_bot_msg_id = {}


def is_admin(user_id):
  if user_id == SUPER_ADMIN_ID:
    return True
  local_cursor = conn.cursor()
  local_cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
  return local_cursor.fetchone() is not None


def check_subscription(user_id):
  try:
    member = bot.get_chat_member(FORCE_CHANNEL_ID, user_id)
    if member.status in ["member", "administrator", "creator"]:
      return True
  except Exception:
    pass
  return False


def get_join_markup():
  return {
      "inline_keyboard": [
          [{"text": "JOIN STARS GC", "url": GC_INVITE_LINK, "style": "success"}],
          [{"text": "CHECK JOIN", "callback_data": "check_join", "style": "primary"}]
      ]
  }


def get_main_menu():
  return {
      "inline_keyboard": [
          [{"text": "MY REFERRAL & CLAIM", "callback_data": "get_link", "style": "primary"}],
          [{"text": "LEADERBOARD & MY STATUS", "callback_data": "leaderboard", "style": "success"}],
          [{"text": "PROMO CODE", "callback_data": "promo_code", "style": "primary"}],
          [{"text": "STARS GC", "url": GC_INVITE_LINK, "style": "success"}],
          [
              {"text": "SUPPORT", "url": "https://t.me/selvam", "style": "primary"},
              {"text": "DEV", "url": "https://t.me/evadespam", "style": "primary"}
          ]
      ]
  }


def get_back_markup():
  return {
      "inline_keyboard": [
          [{"text": "BACK TO MENU", "callback_data": "back_to_main", "style": "danger"}]
      ]
  }


def get_referral_claim_markup():
  return {
      "inline_keyboard": [
          [{"text": "CLAIM REWARD NOW", "callback_data": "claim", "style": "success"}],
          [{"text": "BACK TO MENU", "callback_data": "back_to_main", "style": "danger"}]
      ]
  }


def edit_msg(call, text, reply_markup):
  try:
    if call.message.content_type == 'photo':
      bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=text, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup.de_json(reply_markup))
    else:
      bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup.de_json(reply_markup))
  except Exception:
    pass


def update_bot_message(chat_id, user_id, text, reply_markup):
  msg_id = last_bot_msg_id.get(user_id)
  if msg_id:
    markup_obj = types.InlineKeyboardMarkup.de_json(reply_markup)
    try:
      bot.edit_message_caption(chat_id=chat_id, message_id=msg_id, caption=text, parse_mode="HTML", reply_markup=markup_obj)
    except:
      try:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=markup_obj)
      except:
        pass


@bot.message_handler(commands=["start"])
def send_welcome(message):
  try:
    user_id = message.from_user.id

    if not check_subscription(user_id):
      if user_id in last_bot_msg_id:
        try:
          bot.delete_message(message.chat.id, last_bot_msg_id[user_id])
        except:
          pass
      
      msg_text = (
          "VERIFICATION REQUIRED\n\n"
          "TO UTILIZE THIS BOT, YOU MUST BE A MEMBER OF THE STARS GC. "
          "PLEASE JOIN OUR COMMUNITY USING THE BUTTON BELOW AND CLICK CHECK JOIN TO PROCEED."
      )
      
      msg = bot.send_message(
          message.chat.id,
          msg_text,
          parse_mode="HTML",
          reply_markup=types.InlineKeyboardMarkup.de_json(get_join_markup()),
      )
      last_bot_msg_id[user_id] = msg.message_id
      return

    process_valid_start(message)

  except Exception as e:
    print(f"Error in send_welcome: {e}")


def process_valid_start(message):
  try:
    user_id = message.from_user.id
    args = message.text.split() if message.text else []

    local_cursor = conn.cursor()

    local_cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    ban_status = local_cursor.fetchone()
    if ban_status and ban_status[0] == 1:
      bot.send_message(message.chat.id, "ACCESS DENIED: YOU HAVE BEEN RESTRICTED FROM USING THIS SERVICE.", parse_mode="HTML")
      return

    local_cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = local_cursor.fetchone()

    if not user:
      referred_by = None
      if len(args) > 1 and args[0].startswith("/start ref_"):
        try:
          potential_referrer = int(args[1].replace("ref_", ""))
          if potential_referrer != user_id and check_subscription(user_id):
            local_cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (potential_referrer,),)
            ref_check = local_cursor.fetchone()
            if ref_check and ref_check[0] == 0:
              referred_by = potential_referrer
              local_cursor.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (referred_by,),)
              local_cursor.execute("UPDATE bot_stats SET value = value + 1 WHERE key = 'total_joins'")
              conn.commit()

              local_cursor.execute("SELECT ref_count FROM users WHERE user_id = ?", (referred_by,))
              ref_data = local_cursor.fetchone()
              
              if ref_data and ref_data[0] == 15:
                bot.send_message(referred_by, "CONGRATULATIONS!\n\nYOU HAVE SUCCESSFULLY REACHED 15 REFERRALS! PLEASE CLAIM YOUR FREE TEDDY BEAR FROM THE ADMIN: @SELVAM", parse_mode="HTML")
              else:
                bot.send_message(referred_by, "NEW REFERRAL!\n\nA NEW USER JUST JOINED USING YOUR EXCLUSIVE LINK. YOUR REFERRAL COUNT HAS BEEN UPDATED.", parse_mode="HTML")
        except ValueError:
          pass

      local_cursor.execute("INSERT INTO users (user_id, referred_by, ref_count) VALUES (?, ?, 0)", (user_id, referred_by),)
      conn.commit()

    if user_id in last_bot_msg_id:
      try:
        bot.delete_message(message.chat.id, last_bot_msg_id[user_id])
      except:
        pass

    welcome_text = (
        "WELCOME TO THE EXCLUSIVE TEDDY GIVEAWAY!\n\n"
        "WE ARE THRILLED TO REWARD OUR TOP SUPPORTERS WITH A FREE PREMIUM TEDDY BEAR. "
        "SIMPLY INVITE 15 FRIENDS USING YOUR UNIQUE LINK TO UNLOCK YOUR EXCLUSIVE REWARD.\n\n"
        "SELECT AN OPTION FROM THE MENU BELOW TO GET STARTED:"
    )

    PHOTO_URL = "YOUR_IMAGE_URL_HERE"

    markup_json = get_main_menu()
    try:
      msg = bot.send_photo(message.chat.id, photo=PHOTO_URL, caption=welcome_text, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup.de_json(markup_json))
      last_bot_msg_id[user_id] = msg.message_id
    except Exception:
      msg = bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup.de_json(markup_json))
      last_bot_msg_id[user_id] = msg.message_id

  except Exception as e:
    print(f"Error in process_valid_start: {e}")


@bot.message_handler(commands=["addadmin"])
def add_admin(message):
  if message.from_user.id != SUPER_ADMIN_ID:
    return
  args = message.text.split()
  if len(args) != 2:
    bot.send_message(message.chat.id, "USAGE: /addadmin <user_id>", parse_mode="HTML")
    return
  try:
    new_admin_id = int(args[1])
    local_cursor = conn.cursor()
    local_cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin_id,))
    conn.commit()
    bot.send_message(message.chat.id, f"SUCCESSFULLY ADDED {new_admin_id} AS ADMIN.", parse_mode="HTML")
  except ValueError:
    bot.send_message(message.chat.id, "INVALID USER ID.", parse_mode="HTML")


@bot.message_handler(commands=["removeadmin"])
def remove_admin(message):
  if message.from_user.id != SUPER_ADMIN_ID:
    return
  args = message.text.split()
  if len(args) != 2:
    bot.send_message(message.chat.id, "USAGE: /removeadmin <user_id>", parse_mode="HTML")
    return
  try:
    rem_id = int(args[1])
    if rem_id == SUPER_ADMIN_ID:
      bot.send_message(message.chat.id, "YOU CANNOT REMOVE THE SUPER ADMIN.", parse_mode="HTML")
      return
    local_cursor = conn.cursor()
    local_cursor.execute("DELETE FROM admins WHERE user_id = ?", (rem_id,))
    conn.commit()
    bot.send_message(message.chat.id, f"ADMIN {rem_id} REMOVED SUCCESSFULLY.", parse_mode="HTML")
  except ValueError:
    bot.send_message(message.chat.id, "INVALID USER ID.", parse_mode="HTML")


@bot.message_handler(commands=["refund"])
def refund_user(message):
  if not is_admin(message.from_user.id):
    return
  args = message.text.split()
  if len(args) != 3:
    bot.send_message(message.chat.id, "USAGE: /refund <user_id> <amount>", parse_mode="HTML")
    return
  try:
    target_user_id = int(args[1])
    amount = int(args[2])
    local_cursor = conn.cursor()
    local_cursor.execute("UPDATE users SET ref_count = ref_count + ? WHERE user_id = ?", (amount, target_user_id))
    conn.commit()
    bot.send_message(message.chat.id, f"SUCCESSFULLY REFUNDED {amount} POINTS TO USER {target_user_id}.", parse_mode="HTML")
    try:
      bot.send_message(target_user_id, f"YOUR ACCOUNT HAS BEEN REFUNDED WITH {amount} REFERRAL POINTS BY ADMIN.", parse_mode="HTML")
    except:
      pass
  except ValueError:
    bot.send_message(message.chat.id, "INVALID FORMAT OR USER ID.", parse_mode="HTML")


@bot.message_handler(commands=["promo"])
def create_promo(message):
  if not is_admin(message.from_user.id):
    return
  args = message.text.split()
  if len(args) != 3:
    bot.send_message(message.chat.id, "INVALID FORMAT\nUSAGE: /PROMO <CODE> <AMOUNT>", parse_mode="HTML")
    return
  code = args[1]
  try:
    amount = int(args[2])
  except ValueError:
    bot.send_message(message.chat.id, "ERROR: THE AMOUNT MUST BE A VALID NUMBER.", parse_mode="HTML")
    return

  local_cursor = conn.cursor()
  local_cursor.execute("INSERT OR REPLACE INTO promo_codes (code, amount) VALUES (?, ?)", (code, amount))
  conn.commit()
  bot.send_message(message.chat.id, f"PROMO CODE CREATED!\n\nCODE: <code>{code.upper()}</code>\nVALUE: <code>{amount}</code> POINTS", parse_mode="HTML")


@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
  try:
    if not is_admin(message.from_user.id):
      return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
      bot.send_message(message.chat.id, "ERROR: PLEASE PROVIDE THE MESSAGE CONTENT YOU WISH TO BROADCAST.", parse_mode="HTML")
      return

    local_cursor = conn.cursor()
    local_cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    all_users = local_cursor.fetchall()
    success = 0
    for (u_id,) in all_users:
      try:
        bot.send_message(u_id, f"IMPORTANT ANNOUNCEMENT:\n\n{text.upper()}", parse_mode="HTML")
        success += 1
      except Exception:
        pass
    bot.send_message(message.chat.id, f"BROADCAST SUCCESSFUL!\nMESSAGE SUCCESSFULLY DELIVERED TO {success} ACTIVE USERS.", parse_mode="HTML")
  except Exception as e:
    print(f"Error in broadcast: {e}")


@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
  try:
    user_id = call.from_user.id

    if call.data == "check_join":
      if check_subscription(user_id):
        bot.answer_callback_query(call.id, "VERIFICATION SUCCESSFUL!")
        call.message.text = "/start"
        process_valid_start(call.message)
      else:
        bot.answer_callback_query(call.id, "YOU HAVE NOT JOINED THE GROUP YET! PLEASE JOIN FIRST.", show_alert=True)
      return

    if not check_subscription(user_id):
      bot.answer_callback_query(call.id, "PLEASE JOIN THE STARS GC FIRST TO ACCESS THE BOT MENU!", show_alert=True)
      return

    local_cursor = conn.cursor()
    local_cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    ban_status = local_cursor.fetchone()
    if ban_status and ban_status[0] == 1:
      bot.answer_callback_query(call.id, "YOU ARE CURRENTLY BANNED FROM THIS SERVICE.", show_alert=True)
      return
      
    if call.data == "back_to_main":
      bot.answer_callback_query(call.id)
      user_state.pop(user_id, None)
      
      welcome_text = (
          "WELCOME TO THE EXCLUSIVE TEDDY GIVEAWAY!\n\n"
          "WE ARE THRILLED TO REWARD OUR TOP SUPPORTERS WITH A FREE PREMIUM TEDDY BEAR. "
          "SIMPLY INVITE 15 FRIENDS USING YOUR UNIQUE LINK TO UNLOCK YOUR EXCLUSIVE REWARD.\n\n"
          "SELECT AN OPTION FROM THE MENU BELOW TO GET STARTED:"
      )
      edit_msg(call, welcome_text, get_main_menu())

    elif call.data == "get_link":
      ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"
      bot.answer_callback_query(call.id)
      
      text = (
          "YOUR EXCLUSIVE REFERRAL LINK:\n"
          f"<code>{ref_link}</code>\n\n"
          "SHARE THIS LINK WITH YOUR NETWORK TO EARN POINTS!\n\n"
          "(IF YOU HAVE COMPLETED 15 REFERRALS, CLICK THE CLAIM BUTTON BELOW)"
      )
      edit_msg(call, text, get_referral_claim_markup())

    elif call.data == "leaderboard":
      bot.answer_callback_query(call.id)
      
      local_cursor.execute("SELECT user_id, ref_count FROM users ORDER BY ref_count DESC LIMIT 5")
      top_users = local_cursor.fetchall()
      
      local_cursor.execute("SELECT ref_count, reward_claimed FROM users WHERE user_id = ?", (user_id,),)
      user_stat = local_cursor.fetchone()

      lb_text = "TOP 5 REFERRERS LEADERBOARD:\n\n"
      for idx, (u_id, r_count) in enumerate(top_users, 1):
        lb_text += f"{idx}. USER ID: <code>{u_id}</code> — {r_count} REFERRALS\n"
        
      lb_text += "\n--------------------\n\n"
      lb_text += "YOUR CURRENT STATUS:\n\n"

      if user_stat:
        ref_count, reward_claimed = user_stat
        needed = max(0, 15 - ref_count)
        lb_text += f"TOTAL REFERRALS: <code>{ref_count} / 15</code>\n"

        if ref_count >= 15:
          if reward_claimed == 0:
            lb_text += "\nTARGET ACHIEVED! YOU ARE ELIGIBLE FOR THE REWARD."
          else:
            lb_text += "\nSTATUS: YOU HAVE ALREADY SUBMITTED YOUR DETAILS FOR VERIFICATION."
        else:
          lb_text += f"\nPROGRESS: YOU ONLY NEED {needed} MORE REFERRALS TO UNLOCK YOUR REWARD!"
      else:
        lb_text += "PLEASE USE THE /START COMMAND TO INITIALIZE YOUR PROFILE."

      edit_msg(call, lb_text, get_back_markup())
      
    elif call.data == "promo_code":
      bot.answer_callback_query(call.id)
      user_state[user_id] = "waiting_for_promo"
      edit_msg(call, "REDEEM PROMO CODE\n\nPLEASE ENTER YOUR EXCLUSIVE PROMO CODE BELOW IN THE CHAT:", get_back_markup())

    elif call.data == "claim":
      local_cursor.execute("SELECT ref_count, reward_claimed FROM users WHERE user_id = ?", (user_id,),)
      user = local_cursor.fetchone()
      
      if not user:
        bot.answer_callback_query(call.id, "PLEASE USE /START FIRST.", show_alert=True)
        return

      ref_count, reward_claimed = user

      if ref_count < 15:
        bot.answer_callback_query(call.id, f"YOU CURRENTLY HAVE {ref_count} REFERRALS. 15 ARE REQUIRED TO CLAIM.", show_alert=True)
        return

      if reward_claimed == 1:
        bot.answer_callback_query(call.id, "YOU HAVE ALREADY SUBMITTED YOUR USER ID FOR REVIEW!", show_alert=True)
        return

      bot.answer_callback_query(call.id)
      user_state[user_id] = "waiting_for_user_id"
      edit_msg(call, "CONGRATULATIONS! YOU COMPLETED 15 REFERRALS.\n\nPLEASE TYPE AND SEND YOUR USER ID IN THE CHAT BELOW TO CLAIM YOUR REWARD:", get_back_markup())
      
  except Exception as e:
    print(f"Error in handle_buttons: {e}")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_user_messages(message):
  user_id = message.from_user.id
  state = user_state.get(user_id)
  
  if not state:
      return
  
  try:
    bot.delete_message(message.chat.id, message.message_id)
  except Exception:
    pass
    
  if not message.text:
    return
    
  text = message.text.strip()
  
  if state == "waiting_for_user_id":
    if not check_subscription(user_id):
      return
      
    local_cursor = conn.cursor()
    local_cursor.execute("UPDATE users SET submitted_id = ?, reward_claimed = 1, ref_count = ref_count - 15 WHERE user_id = ?", (text, user_id))
    conn.commit()
    user_state.pop(user_id, None)

    success_msg = "SUBMISSION SUCCESSFUL!\n\nYOUR USER ID HAS BEEN RECORDED AND POINTS HAVE BEEN REDEEMED. OUR ADMINISTRATION TEAM WILL CONTACT YOU SHORTLY."
    update_bot_message(message.chat.id, user_id, success_msg, get_back_markup())

    username = f"@{message.from_user.username}" if message.from_user.username else "No Username"
    admin_msg = (
        "NEW REWARD CLAIMED!\n\n"
        f"TELEGRAM USER ID: <code>{user_id}</code>\n"
        f"USERNAME: {username}\n\n"
        f"SUBMITTED DETAIL:\n<code>{text}</code>"
    )

    local_cursor.execute("SELECT user_id FROM admins")
    all_admins = local_cursor.fetchall()
    for (adm_id,) in all_admins:
      try:
        bot.send_message(adm_id, admin_msg, parse_mode="HTML")
      except Exception:
        pass

  elif state == "waiting_for_promo":
    local_cursor = conn.cursor()
    local_cursor.execute("SELECT amount FROM promo_codes WHERE code = ?", (text,))
    promo = local_cursor.fetchone()
    
    if promo:
      amount = promo[0]
      try:
        local_cursor.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (user_id, text))
        local_cursor.execute("UPDATE users SET ref_count = ref_count + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        
        msg_text = f"SUCCESS!\n\nPROMO CODE APPLIED SUCCESSFULLY. YOU HAVE BEEN REWARDED WITH {amount} REFERRAL POINTS."
        update_bot_message(message.chat.id, user_id, msg_text, get_back_markup())
      except sqlite3.IntegrityError:
        update_vd = "NOTICE: YOU HAVE ALREADY UTILIZED THIS PROMO CODE."
        update_bot_message(message.chat.id, user_id, update_vd, get_back_markup())
    else:
      update_bot_message(message.chat.id, user_id, "INVALID CODE: THE PROMO CODE YOU ENTERED DOES NOT EXIST OR HAS EXPIRED.", get_back_markup())
      
    user_state.pop(user_id, None)


if __name__ == "__main__":
  keep_alive()
  print("Bot is successfully running with button colors retained and emojis removed...")
  bot.polling(none_stop=True)
