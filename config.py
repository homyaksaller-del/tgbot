import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "YOUR_CRYPTO_BOT_TOKEN")
KEYAUTH_SELLER_KEY = os.getenv("KEYAUTH_SELLER_KEY", "YOUR_KEYAUTH_SELLER_KEY")
KEYAUTH_APP_NAME = os.getenv("KEYAUTH_APP_NAME", "YOUR_APP_NAME")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@noethleft")

# Реквизиты для банков (можно менять в .env)
MONO_CARD = os.getenv("MONO_CARD", "4441 1111 2222 3333")
MONO_NAME = os.getenv("MONO_NAME", "Іван І.")
PRIVAT_CARD = os.getenv("PRIVAT_CARD", "5168 7421 0000 1234")
PRIVAT_NAME = os.getenv("PRIVAT_NAME", "Іван І.")

# CryptoBot API
CRYPTO_API_URL = "https://pay.crypt.bot/api"

# KeyAuth API
KEYAUTH_API_URL = "https://keyauth.cc/api/seller/"
