from io import BytesIO
from time import sleep
from typing import Optional, List
from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler
from telegram.ext.dispatcher import run_async
from tg_bot.modules.helper_funcs.chat_status import is_user_ban_protected, bot_admin

import tg_bot.modules.sql.users_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4


@run_async
def quickscope(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[1])
        to_kick = str(args[0])
    else:
        update.effective_message.reply_text("Bir sohbete/kullanıcıya atıfta bulunmuyor gibisiniz")
    try:
        bot.kick_chat_member(chat_id, to_kick)
        update.effective_message.reply_text("Yasaklanmaya çalışıldı " + to_kick + " from" + chat_id)
    except BadRequest as excp:
        update.effective_message.reply_text(excp.message + " " + to_kick)


@run_async
def quickunban(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[1])
        to_kick = str(args[0])
    else:
        update.effective_message.reply_text("Bir sohbete/kullanıcıya atıfta bulunmuyor gibisiniz")
    try:
        bot.unban_chat_member(chat_id, to_kick)
        update.effective_message.reply_text("Yasak kaldırılmaya çalışıldı " + to_kick + " from" + chat_id)
    except BadRequest as excp:
        update.effective_message.reply_text(excp.message + " " + to_kick)


@run_async
def banall(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[0])
        all_mems = sql.get_chat_members(chat_id)
    else:
        chat_id = str(update.effective_chat.id)
        all_mems = sql.get_chat_members(chat_id)
    for mems in all_mems:
        try:
            bot.kick_chat_member(chat_id, mems.user)
            update.effective_message.reply_text("Yasaklamaya çalıştı " + str(mems.user))
            sleep(0.1)
        except BadRequest as excp:
            update.effective_message.reply_text(excp.message + " " + str(mems.user))
            continue


@run_async
def snipe(bot: Bot, update: Update, args: List[str]):
    try:
        chat_id = str(args[0])
        del args[0]
    except TypeError as excp:
        update.effective_message.reply_text("Lütfen bana yankılanacak bir sohbet verin!")
    to_send = " ".join(args)
    if len(to_send) >= 2:
        try:
            bot.sendMessage(int(chat_id), str(to_send))
        except TelegramError:
            LOGGER.warning("Gruba gönderilemedi %s", str(chat_id))
            update.effective_message.reply_text("Mesaj gönderilemedi. Belki ben o grubun bir parçası değilim?")


@run_async
@bot_admin
def getlink(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = int(args[0])
    else:
        update.effective_message.reply_text("Bir sohbetten bahsetmiyor gibisin")
    chat = bot.getChat(chat_id)
    bot_member = chat.get_member(bot.id)
    if bot_member.can_invite_users:
        invitelink = bot.get_chat(chat_id).invite_link
        update.effective_message.reply_text(invitelink)
    else:
        update.effective_message.reply_text("Davet bağlantısına erişimim yok!")


@bot_admin
def leavechat(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = int(args[0])
        bot.leaveChat(chat_id)
    else:
        update.effective_message.reply_text("Bir sohbetten bahsetmiyor gibisin")

__help__ = """
**Yalnızca sahip:**
- /getlink **chatid**: Belirli bir sohbet için davet bağlantısını alın.
- /banall: Bir sohbetteki tüm üyeleri yasakla
- /leavechat **chatid** : sohbetten ayrıl
**Yalnızca Sudo/sahip:**
- /quickscope **userid** **chatid**: Kullanıcıyı sohbetten yasaklar.
- /quickunban **userid** **chatid**: Kullanıcının sohbetteki yasağını kaldırır.
- /snipe **chatid** **string**: Belirli bir sohbete mesaj göndermemi sağla.
- /rban **userid** **chatid** bir kullanıcıyı sohbetten uzaktan yasaklama
- /runban **userid** **chatid** bir kullanıcının sohbetteki yasağını uzaktan kaldırma
- /Stats: botun istatistiklerini kontrol edin
- /chatlist: sohbet listesini al
- /gbanlist: gbanlı kullanıcı listesini al
- /gmutelist: gmuted kullanıcı listesini al
- /restrict chat_id ve /unrestrict chat_id komutlarıyla sohbet yasakları
**Destek kullanıcısı:**
- /Gban : Bir kullanıcıyı global olarak yasakla
- /Ungban : Bir kullanıcıyı Ungban
- /Gmute : Bir kullanıcıyı Gmute
- /Ungmute : Bir kullanıcının sesini aç
Sudo/sahip de bu komutları kullanabilir.
**Kullanıcılar:**
- /listsudo Sudo kullanıcılarının bir listesini verir
- /listsupport, destek kullanıcılarının bir listesini verir
"""
__mod_name__ = "Special"

SNIPE_HANDLER = CommandHandler("snipe", snipe, pass_args=True, filters=CustomFilters.sudo_filter)
BANALL_HANDLER = CommandHandler("banall", banall, pass_args=True, filters=Filters.user(OWNER_ID))
QUICKSCOPE_HANDLER = CommandHandler("quickscope", quickscope, pass_args=True, filters=CustomFilters.sudo_filter)
QUICKUNBAN_HANDLER = CommandHandler("quickunban", quickunban, pass_args=True, filters=CustomFilters.sudo_filter)
GETLINK_HANDLER = CommandHandler("getlink", getlink, pass_args=True, filters=Filters.user(OWNER_ID))
LEAVECHAT_HANDLER = CommandHandler("leavechat", leavechat, pass_args=True, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(SNIPE_HANDLER)
dispatcher.add_handler(BANALL_HANDLER)
dispatcher.add_handler(QUICKSCOPE_HANDLER)
dispatcher.add_handler(QUICKUNBAN_HANDLER)
dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)
