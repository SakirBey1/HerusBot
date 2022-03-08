
from telegram import Update, Bot
from telegram.ext import run_async

from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher

from requests import get

@run_async
def ud(bot: Bot, update: Update):
  message = update.effective_message
  text = message.text[len('/ud '):]
  results = get(f'http://api.urbandictionary.com/v0/define?term={text}').json()
  reply_text = f'Kelime: {text}\nTanım: {results["list"][0]["definition"]}'
  message.reply_text(reply_text)

__help__ = """
 - /ud:{word} Aramak istediğiniz kelimeyi veya ifadeyi yazın. like /ud telegram Sözcük: Telegram Tanım: Gönderenin telgraf hizmetiyle bağlantı kuracağı ve [mesajını] [telefon] üzerinden konuşacağı bir zamanların popüler telekomünikasyon sistemi. Mesajı alan kişi daha sonra bir teletype makinesi aracılığıyla alıcının [adresine] yakın bir telgraf ofisine gönderir. Mesaj daha sonra muhatabına elden teslim edilecektir. 1851'den 2006'da hizmeti durdurana kadar, Western Union dünyanın en iyi bilinen telgraf hizmetiydi.
"""

__mod_name__ = "kentsel sözlük"
  
ud_handle = DisableAbleCommandHandler("ud", ud)

dispatcher.add_handler(ud_handle)
