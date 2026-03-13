import logging
import random
import re
import json
import time
import asyncio
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# ========== ТВОИ ДАННЫЕ ==========
BOT_TOKEN = "8430585997:AAFE8C3ostnoTQiwSlwVmYpnVQI5FjbsCRc"
CHANNEL_LINK = "https://t.me/+WLiiYR7_ymZjYWY1"
CHANNEL_ID = -1003256576224
YOUR_TELEGRAM_ID = 571001160

# ========== БАН-ЛИСТ ==========
BANNED_USERNAMES = {
    "giftrelayer", "mrktbank", "kallent", "monk", "durov",
    "virusgift", "portalsrelayer", "lucha", "snoopdogg", "snoop", 
    "ufc", "ton", "nft", "nftgift", "telegram"
}

# ========== ЖЕНСКИЕ ИМЕНА (КОРОТКИЙ СПИСОК) ==========
FEMALE_NAMES = {
    "anna", "anya", "maria", "masha", "olga", "olya", "katya", "kate",
    "nastya", "dasha", "sveta", "lena", "alena", "yana", "vika",
    "анна", "аня", "маша", "катя", "настя", "даша", "света", "лена"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ПРОСТОЙ СПИСОК NFT ==========
NFT_LIST = [
    {"name": "CandyCane", "min_id": 1000, "max_id": 150000},
    {"name": "CloverPin", "min_id": 1000, "max_id": 60000},
    {"name": "CookieHeart", "min_id": 1000, "max_id": 60000},
    {"name": "EasterEgg", "min_id": 1000, "max_id": 60000},
    {"name": "GingerCookie", "min_id": 1000, "max_id": 60000},
    {"name": "HeartLocket", "min_id": 1000, "max_id": 60000},
    {"name": "LoveCandle", "min_id": 1000, "max_id": 60000},
    {"name": "LovePotion", "min_id": 1000, "max_id": 60000},
    {"name": "Rose", "min_id": 1000, "max_id": 60000},
    {"name": "SweetCookie", "min_id": 1000, "max_id": 60000},
]

# ========== ХРАНИЛИЩЕ ==========
users_db = {}
user_settings = {}

# ========== ПРОВЕРКА ПОДПИСКИ ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

async def require_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Подписаться", url=CHANNEL_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.message.edit_text("⚠️ Подпишись на канал!", reply_markup=reply_markup)
        else:
            await update.message.reply_text("⚠️ Подпишись на канал!", reply_markup=reply_markup)
        return False
    return True

# ========== ПРОСТОЙ ПАРСЕР ==========
async def get_nft_owner(gift_url: str) -> dict:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(gift_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем username
        text = soup.get_text()
        username_match = re.search(r'@(\w{5,32})', text)
        if username_match:
            username = username_match.group(1).lower()
            if username not in BANNED_USERNAMES:
                return {'success': True, 'username': username}
        
        return {'success': False}
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return {'success': False}

# ========== ГЕНЕРАЦИЯ ==========
async def find_girls(count=10):
    gifts = []
    used_ids = set()
    attempts = 0
    max_attempts = 100
    
    while len(gifts) < count and attempts < max_attempts:
        nft = random.choice(NFT_LIST)
        nft_id = random.randint(nft["min_id"], nft["max_id"])
        
        if nft_id in used_ids:
            attempts += 1
            continue
            
        clean_name = re.sub(r"[^\w]", "", nft["name"])
        url = f"https://t.me/nft/{clean_name}-{nft_id}"
        
        owner_info = await get_nft_owner(url)
        
        if owner_info['success']:
            username = owner_info['username']
            # Проверяем на женское имя
            for name in FEMALE_NAMES:
                if name in username:
                    gifts.append({
                        "url": url,
                        "owner": username
                    })
                    logger.info(f"✅ Нашлась: {username}")
                    break
        
        used_ids.add(nft_id)
        attempts += 1
        await asyncio.sleep(0.2)
    
    return gifts

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await require_subscription(update, context):
        return
    
    if user_id not in users_db:
        users_db[user_id] = {
            'username': update.effective_user.username,
            'registered': datetime.now().strftime("%Y-%m-%d")
        }
    
    text = f"👋 Привет! Я ищу девушек в NFT-подарках"
    keyboard = [[InlineKeyboardButton("🔍 Найти девушек", callback_data="find_girls")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

# ========== ПОИСК ==========
async def find_girls_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    await query.message.edit_text("🔍 Ищу девушек... Это может занять до 30 секунд")
    
    girls = await find_girls(5)
    
    if not girls:
        await query.message.edit_text(
            "❌ Не нашлось девушек. Попробуй еще раз.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Еще раз", callback_data="find_girls")]])
        )
        return
    
    text = "*Найденные девушки:*\n\n"
    for i, girl in enumerate(girls, 1):
        text += f"{i}. @{girl['owner']} | [Профиль](tg://user?domain={girl['owner']})\n"
    
    keyboard = [[InlineKeyboardButton("🔄 Искать еще", callback_data="find_girls")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# ========== ЗАПУСК ==========
def main():
    print("🚀 Бот запускается...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(find_girls_handler, pattern="^find_girls$"))
    
    print("✅ Бот готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()
