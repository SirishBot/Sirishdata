import json
import os
from csv import DictWriter
from datetime import datetime, timedelta
from re import findall, search
from pymongo import MongoClient   # pip install pymongo[srv]
from telebot import TeleBot, util, types   # pip install pyTelegramBotAPI

CONFIG_FILE = 'config.json'
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

bot_api_token = config['bot_api_token']
mongo_host_url = config['mongo_host_url']

bot = TeleBot(bot_api_token, parse_mode='html', threaded=False, disable_web_page_preview=True)
botusername = bot.get_me().username
botid = bot.get_me().id

mongo_client = MongoClient(mongo_host_url)
db = mongo_client[botusername]
coll = db['Users']
coll2 = db['States']
coll3 = db['Leaderboard']

coll2.create_index("createdAt", expireAfterSeconds=86400*3)
coll3.create_index("expireAt", expireAfterSeconds=0)

bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())

quiz_status = True
quiz_list = [
    {"question": "What is the main utility of the FXST Token?", "answer": "Staking", "options": ["Staking", "Trading", "Lending", "Governance"]},
    {"question": "Which blockchain is FXST Token built on?", "answer": "Binance Smart Chain", "options": ["Ethereum", "Binance Smart Chain", "Solana", "Polkadot"]},
    {"question": "Which platform will FXST Token be listed on first?", "answer": "LA Token", "options": ["Coinbase", "Bitmart", "MEXC", "LA Token"]},
    {"question": "Which use case of FXST Token involves a marketplace for digital collectibles?", "answer": "NFT marketplace", "options": ["Forex trading", "NFT marketplace", "Indices and commodity trading", "Crypto staking"]},
    {"question": "Which feature is not associated with FXST Token?", "answer": "Lending", "options": ["Governance", "Lending", "Trading", "Rewards"]},
    {"question": "What does <b>HODL</b> mean in crypto?", "answer": "Hold On for Dear Life", "options": ["Hold On for Dear Life", "High Order Digital Ledger", "Hold On Digital Liquidity", "Heavy Order Demand List"]},
    {"question": "Who created Ethereum?", "answer": "Vitalik Buterin", "options": ["Satoshi Nakamoto", "Vitalik Buterin", "Charles Hoskinson", "Gavin Wood"]},
    {"question": "Which country first adopted Bitcoin as legal tender?", "answer": "El Salvador", "options": ["United States", "Switzerland", "El Salvador", "Japan"]},
    {"question": "Which term describes a rapid price increase in a cryptocurrency?", "answer": "Pump", "options": ["Pump", "Dump", "Burn", "Slash"]},
    {"question": "Which of the following is a popular hardware wallet?", "answer": "Ledger", "options": ["MetaMask", "Coinbase", "Ledger", "Binance"]}
]

@bot.message_handler(func=lambda message: message.text in ['/cancle'], chat_types=['private'])
def cancel(message: types.Message):
    coll2.delete_one({"_id": message.from_user.id})
    start(message)

@bot.message_handler(commands=['cleardata'], chat_types=['private'])
def cleardata(message: types.Message):
    coll.delete_many({})
    coll2.delete_many({})
    coll3.delete_many({})
    bot.send_message(message.from_user.id, "Data cleared successfully!")

@bot.message_handler(commands=['start'], chat_types=['private'])
def start(message: types.Message):
    user = coll.find_one({"_id": message.from_user.id}, {"_id": 1})
    if not user:
        ref_parent = util.extract_arguments(message.text)
        if ref_parent and ref_parent.isdigit() and coll.find_one({"_id": int(ref_parent)}):
            coll.insert_one({"_id": message.from_user.id, "username": message.from_user.username, "firstname": message.from_user.first_name, "refcount": 0, "refparent": int(ref_parent)})
        else:
            coll.insert_one({"_id": message.from_user.id, "username": message.from_user.username, "firstname": message.from_user.first_name, "refcount": 0})
    mention = util.user_link(message.from_user)
    bot.send_message(message.from_user.id, f'Hey <b>{mention}</b> 👋😉 \n\n🎉 Welcome to the <b>FXST Token Quiz Airdrop</b>! 🏆\n\nBefore we start the quiz, we need a few details from you to ensure we can send you your rewards if you win. 🏅')
    bot.send_message(message.from_user.id, '<b>Please Submit Your Email Address</b> 📧:')
    coll2.replace_one({"_id": message.from_user.id}, {"_id": message.from_user.id, "state": "email", "createdAt": datetime.utcnow()}, upsert=True)

def get_email(message: types.Message):
    if message.entities and len(message.entities) == 1 and message.entities[0].offset == 0 and message.entities[0].length == len(message.text) and message.entities[0].type == "email":
        coll.update_one({"_id": message.from_user.id}, {"$set": {"email": message.text}})
        bot.send_message(message.from_user.id, 'Okay. Now submit your <b>BNB BEP20 wallet address</b>👇🏻:')
        coll2.replace_one({"_id": message.from_user.id}, {"_id": message.from_user.id, "state": "wallet", "createdAt": datetime.utcnow()}, upsert=True)
    else:
        bot.send_message(message.from_user.id, 'Invalid email address. Try again:')

def get_wallet(message: types.Message):
    if search(r"^0x[a-fA-F0-9]{40}$", message.text):
        coll.update_one({"_id": message.from_user.id}, {"$set": {"wallet": message.text}})
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("I have joined", callback_data="telegram"))
        bot.send_message(message.from_user.id, 'Okay. Now join our <b>Telegram Group</b>📲:\nhttps://t.me/+uFPk-Z12V3UyZDY1', reply_markup=keyboard)
        coll2.delete_one({"_id": message.from_user.id})
    else:
        bot.send_message(message.from_user.id, 'Invalid wallet address. Try again:')

@bot.callback_query_handler(lambda call: call.data == "telegram")
def telegram(call: types.CallbackQuery):
    try:
        if bot.get_chat_member(-1001791622607, call.from_user.id).status not in ('member','administrator','creator'):
            bot.answer_callback_query(call.id, "Please complete the tasks before clicking this button!", show_alert=True)
            return
    except:
        pass
    bot.edit_message_reply_markup(call.from_user.id, call.message.message_id)
    bot.send_message(call.from_user.id, 'Okay. Now follow our <b>Twitter page,Like ❤️ and Repost 📲 the pinned post and Tag 3 of your friends👥</b>:\nhttps://x.com/fxsttoken\n\nThen submit your Twitter username:\nExample: <code>@username</code>')
    coll2.replace_one({"_id": call.from_user.id}, {"_id": call.from_user.id, "state": "twitter", "createdAt": datetime.utcnow()}, upsert=True)

def get_twitter(message: types.Message):
    if search(r"^@[a-zA-Z0-9_]{1,15}$", message.text):
        coll.update_one({"_id": message.from_user.id}, {"$set": {"twitter": message.text}})
        bot.send_message(message.from_user.id, 'Okay. Now follow our <b>Instagram Page,Like ❤️ & Comment 💬 the pinned post</b>:\nhttps://www.instagram.com/fxsttoken\n\n<b>Then submit your Instagram username</b>:\nExample: <code>@username</code>')
        coll2.replace_one({"_id": message.from_user.id}, {"_id": message.from_user.id, "state": "instagram", "createdAt": datetime.utcnow()}, upsert=True)
    else:
        bot.send_message(message.from_user.id, 'Invalid Twitter username. Try again:')

def get_instagram(message: types.Message):
    if search(r"^@[a-zA-Z0-9._]{1,30}$", message.text):
        coll.update_one({"_id": message.from_user.id}, {"$set": {"instagram": message.text}})
        bot.send_message(message.from_user.id, 'Okay. Now follow our <b>Facebook page, Like ❤️ and Comment 💬 on the pinned post</b>:\nhttps://www.facebook.com/fxsttoken\n\n<b>Then submit your Facebook username</b>👇🏻:\nExample: <code>@username</code>')
        coll2.replace_one({"_id": message.from_user.id}, {"_id": message.from_user.id, "state": "facebook", "createdAt": datetime.utcnow()}, upsert=True)
    else:
        bot.send_message(message.from_user.id, 'Invalid Instagram username. Try again:')

def get_facebook(message: types.Message):
    if search(r"^@[a-zA-Z0-9.]{5,30}$", message.text):
        coll.update_one({"_id": message.from_user.id}, {"$set": {"facebook": message.text}})
        bot.send_message(message.from_user.id, '<b>Follow the FXST Token on CMC:</b> https://coinmarketcap.com/community/profile/fxst\n\n<b>Leave a comment on the FXST CMC Page 💬:</b> https://coinmarketcap.com/currencies/fxg\n\n<b>Then share your CMC username:</b>\nExample: <code>@username</code>')
        coll2.replace_one({"_id": message.from_user.id}, {"_id": message.from_user.id, "state": "cmc", "createdAt": datetime.utcnow()}, upsert=True)
    else:
        bot.send_message(message.from_user.id, 'Invalid Facebook username. Try again:')

def get_cmc(message: types.Message):
    if search(r"^@[a-zA-Z0-9_]{4,20}$", message.text):
        coll.update_one({"_id": message.from_user.id}, {"$set": {"cmc": message.text}})
        bot.send_message(message.from_user.id, 'Okay, Now <b>subscribe to our YouTube channel</b>:\nhttps://www.youtube.com/@FXstockToken\n\n<b>Then submit your YouTube username</b>:\nExample: <code>@username</code>')
        coll2.replace_one({"_id": message.from_user.id}, {"_id": message.from_user.id, "state": "youtube", "createdAt": datetime.utcnow()}, upsert=True)
    else:
        bot.send_message(message.from_user.id, 'Invalid CMC username. Try again:')

def get_youtube(message: types.Message):
    if search(r"^@[a-zA-Z0-9._-]{3,30}$", message.text):
        user = coll.find_one_and_update({"_id": message.from_user.id}, {"$set": {"youtube": message.text}}, {"youtube": 1, "refparent": 1})
        if "youtube" not in user:
            refparent = user.get("refparent", None)
            if refparent:
                coll.update_one({"_id": refparent}, {"$inc": {"refcount": 1}})
        coll2.delete_one({"_id": message.from_user.id})
        if quiz_status:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton('Start Quiz', callback_data="startquiz"))
            bot.send_message(message.from_user.id, '<b>Congratulations</b>, you have successfully completed the airdrop tasks and are now eligible for the quiz round.\n\n<b>Press the button below to start the quiz</b>👇🏻.', reply_markup=keyboard)
        else:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Account", callback_data=f"account"))
            keyboard.add(types.InlineKeyboardButton("Leaderboard", callback_data=f"leaderboard"))
            bot.send_message(message.from_user.id, '<b>Congratulations</b>, you have successfully completed the airdrop tasks.', reply_markup=keyboard)
    else:
        bot.send_message(message.from_user.id, 'Invalid YouTube username. Try again:')

@bot.callback_query_handler(lambda call: call.data == "startquiz")
def startquiz(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user = coll.find_one({"_id": call.from_user.id}, {"quiz_number": 1})
    quiz_number = user.get("quiz_number", 0)
    if quiz_number >= len(quiz_list):
        bot.send_message(call.from_user.id, "<b>You have already completed the quiz round☹️</b>.")
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Refresh", callback_data=f"account"))
        keyboard.add(types.InlineKeyboardButton("Leaderboard", callback_data=f"leaderboard"))
        user = coll.find_one({"_id": call.from_user.id})
        refcount = user['refcount']
        quiz_point = user['quiz_point']
        email = user['email']
        wallet = user['wallet']
        twitter = user['twitter']
        instagram = user['instagram']
        facebook = user['facebook']
        youtube = user['youtube']
        reflink = f"https://t.me/{botusername}?start={call.from_user.id}"
        bot.send_message(call.from_user.id, f'You have {refcount} referrals and have scored {quiz_point} points in the quiz round.\n\n<b>Your saved data:</b>\nEmail: {email}\nWallet: {wallet}\nTelegram: {call.from_user.username}\nTwitter: {twitter}\nInstagram: {instagram}\nFacebook: {facebook}\nYouTube: {youtube}\n\n<b>Your referral link:</b>\n<code>{reflink}</code>', reply_markup=keyboard)
    else:
        keyboard = types.InlineKeyboardMarkup()
        get_quiz = quiz_list[quiz_number]
        option_number = 0
        for option in get_quiz["options"]:
            keyboard.add(types.InlineKeyboardButton(option, callback_data=f"answer[{quiz_number}][{option_number}]"))
            option_number = option_number + 1
        bot.send_message(call.from_user.id, get_quiz["question"], reply_markup=keyboard)

@bot.callback_query_handler(lambda call: call.data.startswith("answer"))
def get_answer(call: types.CallbackQuery):
    matches = findall(r'\[(\d+)\]', call.data)
    call_quiz_number = int(matches[0])
    call_option_number = int(matches[1])
    user = coll.find_one({"_id": call.from_user.id}, {"quiz_number": 1})
    quiz_number = user.get("quiz_number", 0)
    if quiz_number == call_quiz_number:
        get_quiz = quiz_list[quiz_number]
        if get_quiz["options"][call_option_number] == get_quiz["answer"]:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("✅ Correct answer", callback_data=f"correctanswer"))
            bot.edit_message_reply_markup(call.from_user.id, call.message.message_id, reply_markup=keyboard)
            coll.update_one({"_id": call.from_user.id}, {"$inc": {"quiz_point": 1, "quiz_number": 1}})
        else:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("❌ Incorrect answer", callback_data=f"incorrectanswer"))
            bot.edit_message_reply_markup(call.from_user.id, call.message.message_id, reply_markup=keyboard)
            coll.update_one({"_id": call.from_user.id}, {"$inc": {"quiz_number": 1}})
        if quiz_number + 1 >= len(quiz_list):
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Refresh", callback_data=f"account"))
            keyboard.add(types.InlineKeyboardButton("Leaderboard", callback_data=f"leaderboard"))
            user = coll.find_one({"_id": call.from_user.id})
            refcount = user['refcount']
            quiz_point = user['quiz_point']
            email = user['email']
            wallet = user['wallet']
            twitter = user['twitter']
            instagram = user['instagram']
            facebook = user['facebook']
            youtube = user['youtube']
            reflink = f"https://t.me/{botusername}?start={call.from_user.id}"
            bot.send_message(call.from_user.id, f'You have {refcount} referrals and have scored {quiz_point} points in the quiz round.\n\n<b>Your saved data:</b>\nEmail: {email}\nWallet: {wallet}\nTelegram: {call.from_user.username}\nTwitter: {twitter}\nInstagram: {instagram}\nFacebook: {facebook}\nYouTube: {youtube}\n\n<b>Your referral link:</b>\n<code>{reflink}</code>', reply_markup=keyboard)
        else:
            user = coll.find_one({"_id": call.from_user.id}, {"quiz_number": 1})
            quiz_number = user.get("quiz_number", 0)
            keyboard = types.InlineKeyboardMarkup()
            get_quiz = quiz_list[quiz_number]
            option_number = 0
            for option in get_quiz["options"]:
                keyboard.add(types.InlineKeyboardButton(option, callback_data=f"answer[{quiz_number}][{option_number}]"))
                option_number = option_number + 1
            bot.send_message(call.from_user.id, get_quiz["question"], reply_markup=keyboard)
    else:
        bot.edit_message_text("You have already answered this quiz.\nSend /start to restart the bot.", call.from_user.id, call.message.message_id)

@bot.callback_query_handler(lambda call: call.data == "account")
def account(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Refresh", callback_data=f"account"))
    keyboard.add(types.InlineKeyboardButton("Leaderboard", callback_data=f"leaderboard"))
    user = coll.find_one({"_id": call.from_user.id})
    refcount = user['refcount']
    quiz_point = user['quiz_point']
    email = user['email']
    wallet = user['wallet']
    twitter = user['twitter']
    instagram = user['instagram']
    facebook = user['facebook']
    cmc = user['cmc']
    youtube = user['youtube']
    reflink = f"https://t.me/{botusername}?start={call.from_user.id}"
    bot.send_message(call.from_user.id, f'You have {refcount} referrals and have scored {quiz_point} points in the quiz round.\n\n<b>Your saved data:</b>\nEmail: {email}\nWallet: {wallet}\nTelegram: {call.from_user.username}\nTwitter: {twitter}\nInstagram: {instagram}\nFacebook: {facebook}\nCMC: {cmc}\nYouTube: {youtube}\n\n<b>Your referral link:</b>\n<code>{reflink}</code>', reply_markup=keyboard)

@bot.callback_query_handler(lambda call: call.data == "leaderboard")
def leaderboard(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Refresh", callback_data=f"leaderboard"))
    keyboard.add(types.InlineKeyboardButton("Account", callback_data=f"account"))
    def replace_placeholders(text, my_dict):
        for placeholder in findall(r'%top\d+(?:id|name|ref)%', text):
            key = placeholder[1:-1]
            if key in my_dict:
                text = text.replace(placeholder, str(my_dict[key]))
        return text
    find_top_users = coll3.find_one({"_id": 123})
    if find_top_users:
        top_users = find_top_users.get('top_users', {})
        expireAt = find_top_users['expireAt']
        time_difference = expireAt - datetime.utcnow()
        toph = int(time_difference.total_seconds() // 3600)
        topm = int((time_difference.total_seconds() % 3600) // 60)
    else:
        size = 100
        rate = 12
        find_top_users = coll.find({}, {"firstname": 1, "refcount": 1}).sort("refcount", -1).limit(size)
        top_users = {}
        for i, d in enumerate(find_top_users, 1):
            top_users[f'top{i}id'] = d['_id']
            top_users[f'top{i}name'] = d['firstname'][:20]
            top_users[f'top{i}ref'] = d['refcount']
        for i in range(int(len(top_users)/3) + 1, size + 1):
            top_users[f'top{i}id'] = "—"
            top_users[f'top{i}name'] = "—"
            top_users[f'top{i}ref'] = "—"
        expireAt = datetime.utcnow() + timedelta(hours=rate)
        coll3.insert_one({"_id": 123, "top_users": top_users, "expireAt": expireAt})
        toph = rate
        topm = 0
    message_text = '<b>Users with the most referrals:</b>\n\n1. %top1name% - %top1ref%\n2. %top2name% - %top2ref%\n3. %top3name% - %top3ref%\n4. %top4name% - %top4ref%\n5. %top5name% - %top5ref%\n6. %top6name% - %top6ref%\n7. %top7name% - %top7ref%\n8. %top8name% - %top8ref%\n9. %top9name% - %top9ref%\n10. %top10name% - %top10ref%\n11. %top11name% - %top11ref%\n12. %top12name% - %top12ref%\n13. %top13name% - %top13ref%\n14. %top14name% - %top14ref%\n15. %top15name% - %top15ref%\n16. %top16name% - %top16ref%\n17. %top17name% - %top17ref%\n18. %top18name% - %top18ref%\n19. %top19name% - %top19ref%\n20. %top20name% - %top20ref%\n21. %top21name% - %top21ref%\n22. %top22name% - %top22ref%\n23. %top23name% - %top23ref%\n24. %top24name% - %top24ref%\n25. %top25name% - %top25ref%\n26. %top26name% - %top26ref%\n27. %top27name% - %top27ref%\n28. %top28name% - %top28ref%\n29. %top29name% - %top29ref%\n30. %top30name% - %top30ref%\n31. %top31name% - %top31ref%\n32. %top32name% - %top32ref%\n33. %top33name% - %top33ref%\n34. %top34name% - %top34ref%\n35. %top35name% - %top35ref%\n36. %top36name% - %top36ref%\n37. %top37name% - %top37ref%\n38. %top38name% - %top38ref%\n39. %top39name% - %top39ref%\n40. %top40name% - %top40ref%\n41. %top41name% - %top41ref%\n42. %top42name% - %top42ref%\n43. %top43name% - %top43ref%\n44. %top44name% - %top44ref%\n45. %top45name% - %top45ref%\n46. %top46name% - %top46ref%\n47. %top47name% - %top47ref%\n48. %top48name% - %top48ref%\n49. %top49name% - %top49ref%\n50. %top50name% - %top50ref%\n51. %top51name% - %top51ref%\n52. %top52name% - %top52ref%\n53. %top53name% - %top53ref%\n54. %top54name% - %top54ref%\n55. %top55name% - %top55ref%\n56. %top56name% - %top56ref%\n57. %top57name% - %top57ref%\n58. %top58name% - %top58ref%\n59. %top59name% - %top59ref%\n60. %top60name% - %top60ref%\n61. %top61name% - %top61ref%\n62. %top62name% - %top62ref%\n63. %top63name% - %top63ref%\n64. %top64name% - %top64ref%\n65. %top65name% - %top65ref%\n66. %top66name% - %top66ref%\n67. %top67name% - %top67ref%\n68. %top68name% - %top68ref%\n69. %top69name% - %top69ref%\n70. %top70name% - %top70ref%\n71. %top71name% - %top71ref%\n72. %top72name% - %top72ref%\n73. %top73name% - %top73ref%\n74. %top74name% - %top74ref%\n75. %top75name% - %top75ref%\n76. %top76name% - %top76ref%\n77. %top77name% - %top77ref%\n78. %top78name% - %top78ref%\n79. %top79name% - %top79ref%\n80. %top80name% - %top80ref%\n81. %top81name% - %top81ref%\n82. %top82name% - %top82ref%\n83. %top83name% - %top83ref%\n84. %top84name% - %top84ref%\n85. %top85name% - %top85ref%\n86. %top86name% - %top86ref%\n87. %top87name% - %top87ref%\n88. %top88name% - %top88ref%\n89. %top89name% - %top89ref%\n90. %top90name% - %top90ref%\n91. %top91name% - %top91ref%\n92. %top92name% - %top92ref%\n93. %top93name% - %top93ref%\n94. %top94name% - %top94ref%\n95. %top95name% - %top95ref%\n96. %top96name% - %top96ref%\n97. %top97name% - %top97ref%\n98. %top98name% - %top98ref%\n99. %top99name% - %top99ref%\n100. %top100name% - %top100ref%\n\nTime until the next update: <b>%toph%h %topm%m</b>.'
    message_text = message_text.replace('%toph%', str(toph)).replace('%topm%', str(topm))
    bot.send_message(call.from_user.id, replace_placeholders(message_text, top_users), reply_markup=keyboard)

@bot.callback_query_handler(lambda call: call.data == "correctanswer")
def correctanswer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "You answered this question correct.", show_alert=True)

@bot.callback_query_handler(lambda call: call.data == "incorrectanswer")
def incorrectanswer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "You answered this question incorrect.", show_alert=True)

@bot.message_handler(commands=['export'], func=lambda message: message.from_user.id in [1700282162, 5755417067], chat_types=['private'])
def export(message: types.Message):
    bot.send_chat_action(message.from_user.id, "upload_document")
    my_dict = coll.find({})
    filename = botusername + '.csv'
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        dict_writer = DictWriter(f, ["_id", "username", "firstname", "quiz_point", "refcount", "email", "wallet", "twitter", "instagram", "facebook", "youtube", "refparent"], extrasaction='ignore', delimiter=',')
        dict_writer.writeheader()
        dict_writer.writerows(my_dict)
    try:
        bot.send_document(message.chat.id, open(filename, 'rb'))
    except Exception as e:
        print(e)
    os.remove(filename)

@bot.message_handler(commands=['status'], func=lambda message: message.from_user.id in [1700282162, 5755417067], chat_types=['private'])
def status(message: types.Message):
     bot.send_message(message.from_user.id, f'Total participants: {coll.count_documents({})}')

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def other(message: types.Message):
        find_state = coll2.find_one({"_id": message.from_user.id})
        if find_state:
            state = find_state['state']
            if state == "email":
                get_email(message)
            elif state == "wallet":
                get_wallet(message)
            elif state == "twitter":
                get_twitter(message)
            elif state == "instagram":
                get_instagram(message)
            elif state == "facebook":
                get_facebook(message)
            elif state == "cmc":
                get_cmc(message)
            elif state == "youtube":
                get_youtube(message)
        else:
            bot.send_message(message.from_user.id, "Press /start to restart the bot.")

bot.infinity_polling()