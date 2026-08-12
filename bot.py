import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread
from pymongo import MongoClient
import urllib.parse

# Flask app for Fake Port (Render 24/7 uptime ke liye)
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running smoothly with MongoDB!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

TOKEN = "8726582370:AAEvxgHrJg0m1ohYUyIyvpuzzcEm15zsks0"
bot = telebot.TeleBot(TOKEN)

# Main Super Admin ID
SUPER_ADMIN_ID = 7691071175
FORCE_CHANNEL_ID = -1003923376846  
GC_INVITE_LINK = "https://t.me/+SPLleac6nY01ZTdh"

# Password mein @ ya koi bhi special character ho toh yeh safely handle kar lega
db_user = urllib.parse.quote_plus("Cricket_231")
db_pass = urllib.parse.quote_plus("Rohit1616@") # Yahan apna asli password daal dena (@ ke sath bhi chalega)

MONGO_URI = f"mongodb+srv://{db_user}:{db_pass}@cluster0.zolmdho.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URI)
db = client["telegram_teddy_bot"]

# Collections (MongoDB ki tables)
users_col = db["users"]
admins_col = db["admins"]
stats_col = db["bot_stats"]
promo_col = db["promo_codes"]
used_promos_col = db["used_promos"]

# Initial setup
if stats_col.count_documents({"key": "total_joins"}) == 0:
    stats_col.insert_one({"key": "total_joins", "value": 0})

if admins_col.count_documents({"user_id": SUPER_ADMIN_ID}) == 0:
    admins_col.insert_one({"user_id": SUPER_ADMIN_ID})

user_state = {}
last_bot_msg_id = {}


def is_admin(user_id):
  if user_id == SUPER_ADMIN_ID:
    return True
  return admins_col.find_one({"user_id": user_id}) is not None


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
          [{"text": "JOIN STARS GC", "url": GC_INVITE_LINK}],
          [{"text": "CHECK JOIN", "callback_data": "check_join"}]
      ]
  }


def get_main_menu():
  return {
      "inline_keyboard": [
          [{"text": "MY REFERRAL & CLAIM", "callback_data": "get_link"}],
          [{"text": "LEADERBOARD & MY STATUS", "callback_data": "leaderboard"}],
          [{"text": "PROMO CODE", "callback_data": "promo_code"}],
          [{"text": "STARS GC", "url": GC_INVITE_LINK}],
          [
              {"text": "SUPPORT", "url": "https://t.me/selvam"},
              {"text": "DEV", "url": "https://t.me/evadespam"}
          ]
      ]
  }


def get_back_markup():
  return {
      "inline_keyboard": [
          [{"text": "BACK TO MENU", "callback_data": "back_to_main"}]
      ]
  }


def get_referral_claim_markup():
  return {
      "inline_keyboard": [
          [{"text": "CLAIM REWARD NOW", "callback_data": "claim"}],
          [{"text": "BACK TO MENU", "callback_data": "back_to_main"}]
      ]
  }


def edit_msg(call, text, reply_markup):
  try:
    markup_obj = types.InlineKeyboardMarkup.de_json(reply_markup)
    if call.message.content_type == 'photo':
      bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=text, parse_mode="HTML", reply_markup=markup_obj)
    else:
      bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, parse_mode="HTML", reply_markup=markup_obj)
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

    user = users_col.find_one({"user_id": user_id})
    if user and user.get("is_banned", 0) == 1:
      bot.send_message(message.chat.id, "ACCESS DENIED: YOU HAVE BEEN RESTRICTED FROM USING THIS SERVICE.", parse_mode="HTML")
      return

    if not user:
      referred_by = None
      if len(args) > 1 and args[0].startswith("/start ref_"):
        try:
          potential_referrer = int(args[1].replace("ref_", ""))
          if potential_referrer != user_id and check_subscription(user_id):
            ref_check = users_col.find_one({"user_id": potential_referrer})
            if ref_check and ref_check.get("is_banned", 0) == 0:
              referred_by = potential_referrer
              users_col.update_one({"user_id": referred_by}, {"$inc": {"ref_count": 1}})
              stats_col.update_one({"key": "total_joins"}, {"$inc": {"value": 1}})

              ref_data = users_col.find_one({"user_id": referred_by})
              if ref_data and ref_data.get("ref_count", 0) == 15:
                bot.send_message(referred_by, "CONGRATULATIONS!\n\nYOU HAVE SUCCESSFULLY REACHED 15 REFERRALS! PLEASE CLAIM YOUR FREE TEDDY BEAR FROM THE ADMIN: @SELVAM", parse_mode="HTML")
              else:
                bot.send_message(referred_by, "NEW REFERRAL!\n\nA NEW USER JUST JOINED USING YOUR EXCLUSIVE LINK. YOUR REFERRAL COUNT HAS BEEN UPDATED.", parse_mode="HTML")
        except ValueError:
          pass

      users_col.insert_one({
          "user_id": user_id,
          "referred_by": referred_by,
          "ref_count": 0,
          "reward_claimed": 0,
          "submitted_id": None,
          "is_banned": 0
      })

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
    markup_obj = types.InlineKeyboardMarkup.de_json(markup_json)
    try:
      msg = bot.send_photo(message.chat.id, photo=PHOTO_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup_obj)
      last_bot_msg_id[user_id] = msg.message_id
    except Exception:
      msg = bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup_obj)
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
    admins_col.update_one({"user_id": new_admin_id}, {"$set": {"user_id": new_admin_id}}, upsert=True)
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
    admins_col.delete_one({"user_id": rem_id})
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
    users_col.update_one({"user_id": target_user_id}, {"$inc": {"ref_count": amount}})
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
  code = args[1].upper()
  try:
    amount = int(args[2])
  except ValueError:
    bot.send_message(message.chat.id, "ERROR: THE AMOUNT MUST BE A VALID NUMBER.", parse_mode="HTML")
    return

  promo_col.update_one({"code": code}, {"$set": {"amount": amount}}, upsert=True)
  bot.send_message(message.chat.id, f"PROMO CODE CREATED!\n\nCODE: <code>{code}</code>\nVALUE: <code>{amount}</code> POINTS", parse_mode="HTML")


@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
  try:
    if not is_admin(message.from_user.id):
      return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
      bot.send_message(message.chat.id, "ERROR: PLEASE PROVIDE THE MESSAGE CONTENT YOU WISH TO BROADCAST.", parse_mode="HTML")
      return

    all_users = users_col.find({"is_banned": 0})
    success = 0
    for u in all_users:
      try:
        bot.send_message(u["user_id"], f"IMPORTANT ANNOUNCEMENT:\n\n{text.upper()}", parse_mode="HTML")
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

    user = users_col.find_one({"user_id": user_id})
    if user and user.get("is_banned", 0) == 1:
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
      
      top_users = list(users_col.find().sort("ref_count", -1).limit(5))
      user_stat = users_col.find_one({"user_id": user_id})

      lb_text = "TOP 5 REFERRERS LEADERBOARD:\n\n"
      for idx, u in enumerate(top_users, 1):
        lb_text += f"{idx}. USER ID: <code>{u.get('user_id')}</code> — {u.get('ref_count', 0)} REFERRALS\n"
        
      lb_text += "\n--------------------\n\n"
      lb_text += "YOUR CURRENT STATUS:\n\n"

      if user_stat:
        ref_count = user_stat.get("ref_count", 0)
        reward_claimed = user_stat.get("reward_claimed", 0)
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
      user = users_col.find_one({"user_id": user_id})
      
      if not user:
        bot.answer_callback_query(call.id, "PLEASE USE /START FIRST.", show_alert=True)
        return

      ref_count = user.get("ref_count", 0)
      reward_claimed = user.get("reward_claimed", 0)

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
      
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"submitted_id": text, "reward_claimed": 1}, "$inc": {"ref_count": -15}}
    )
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

    all_admins = admins_col.find()
    for adm in all_admins:
      try:
        bot.send_message(adm["user_id"], admin_msg, parse_mode="HTML")
      except Exception:
        pass

  elif state == "waiting_for_promo":
    code_text = text.upper()
    promo = promo_col.find_one({"code": code_text})
    
    if promo:
      amount = promo["amount"]
      already_used = used_promos_col.find_one({"user_id": user_id, "code": code_text})
      
      if already_used:
        update_vd = "NOTICE: YOU HAVE ALREADY UTILIZED THIS PROMO CODE."
        update_bot_message(message.chat.id, user_id, update_vd, get_back_markup())
      else:
        used_promos_col.insert_one({"user_id": user_id, "code": code_text})
        users_col.update_one({"user_id": user_id}, {"$inc": {"ref_count": amount}})
        
        msg_text = f"SUCCESS!\n\nPROMO CODE APPLIED SUCCESSFULLY. YOU HAVE BEEN REWARDED WITH {amount} REFERRAL POINTS."
        update_bot_message(message.chat.id, user_id, msg_text, get_back_markup())
    else:
      update_bot_message(message.chat.id, user_id, "INVALID CODE: THE PROMO CODE YOU ENTERED DOES NOT EXIST OR HAS EXPIRED.", get_back_markup())
      
    user_state.pop(user_id, None)


if __name__ == "__main__":
  keep_alive()
  print("Bot is successfully running on Render...")
  bot.polling(none_stop=True)