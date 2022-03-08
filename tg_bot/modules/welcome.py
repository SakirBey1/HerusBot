import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin, can_delete
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_welcome_type
from tg_bot.modules.helper_funcs.string_handling import markdown_parser, \
    escape_invalid_curly_brackets
from tg_bot.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# do not async
def send(update, message, keyboard, backup_message):
    try:
        msg = update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except IndexError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNot: şimdiki mesaj şuydu"
                                                                  "işaretleme sorunları nedeniyle geçersiz. Olabilirdi "
                                                                  "Kullanıcının adından dolayı."),
                                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nNot: şu anki mesaj "
                                                                  "bazı yanlış yerleştirilmiş bir sorun nedeniyle geçersiz "
                                                                  "kıvırcık parantezler. Lütfen güncelle"),
                                                  parse_mode=ParseMode.MARKDOWN)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: mevcut iletide geçersiz bir url var "
                                                                      "düğmelerinden birinde. Lütfen güncelle."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Desteklenmeyen url protokolü":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: geçerli mesajın düğmeleri var "
                                                                      "tarafından desteklenmeyen url protokollerini kullanın "
                                                                      "telgram. Lütfen güncelle."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Yanlış url barındırıcısı":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: mevcut mesajda bazı hatalı URL'ler var. "
                                                                      "Lütfen güncelle."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Ayrıştırılamadı! geçersiz url ana bilgisayar hataları var")
        else:
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nNot: gönderirken bir hata oluştu "
                                                                      "özel mesaj. Lütfen güncelle."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.exception()

    return msg


@run_async
@user_admin
@loggable
def del_joined(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if not args:
        del_pref = sql.get_del_pref(chat.id)
        if del_pref:
            update.effective_message.reply_text("Şimdi sohbet mesajlarına katılan `kullanıcı`yı silmeliydim.")
        else:
            update.effective_message.reply_text("Şu anda eski katıldığım mesajları silmiyorum!")
        return ""

    if args[0].lower() in ("üzerinde", "evet"):
        sql.set_del_joined(str(chat.id), True)
        update.effective_message.reply_text("Eski katıldığım mesajları silmeye çalışacağım!")
        return "<b>{}:</b>" \
               "\n#CLEAN_SERVICE_MESSAGE" \
               "\n<b>Admin:</b> {}" \
               "\nKatılma silmeyi şuna değiştirdi <code>ON</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[0].lower() in ("kapalı", "hayır"):
        sql.set_del_joined(str(chat.id), False)
        update.effective_message.reply_text("Eski katılmış mesajları silmeyeceğim.")
        return "<b>{}:</b>" \
               "\n#CLEAN_SERVICE_MESSAGE" \
               "\n<b>Admin:</b> {}" \
               "\nBirleştirilmiş silmeyi şuna değiştirdi <code>OFF</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("Sadece 'açık/evet' veya 'kapalı/hayır' anlıyorum!")
        return ""


@run_async
def delete_join(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    join = update.effective_message.new_chat_members
    if can_delete(chat, bot.id):
        del_join = sql.get_del_pref(chat.id)
        if del_join:
            update.message.delete()

@run_async
def new_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    if should_welc:
        sent = None
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("Usta evde, hadi bu partiyi başlatalım!")
                continue

            # Don't welcome yourself
            elif new_mem.id == bot.id:
                continue

            else:
                # If welcome message is media, send with appropriate function
                if welc_type != sql.Types.TEXT and welc_type != sql.Types.BUTTON_TEXT:
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
                    return
                # else, move on
                first_name = new_mem.first_name or "İsimsiz Kişi"  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if new_mem.last_name:
                        fullname = "{} {}".format(first_name, new_mem.last_name)
                    else:
                        fullname = first_name
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)
                else:
                    res = sql.DEFAULT_WELCOME.format(first=first_name)
                    keyb = []

                keyboard = InlineKeyboardMarkup(keyb)

                sent = send(update, res, keyboard,
                            sql.DEFAULT_WELCOME.format(first=first_name))  # type: Optional[Message]
            delete_join(bot, update)

        prev_welc = sql.get_clean_pref(chat.id)
        if prev_welc:
            try:
                bot.delete_message(chat.id, prev_welc)
            except BadRequest as excp:
                pass

            if sent:
                sql.set_clean_welcome(chat.id, sent.message_id)


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:
            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("RIP Ustası")
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "İsimsiz Kişi"  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape_markdown(first_name),
                                          last=escape_markdown(left_mem.last_name or first_name),
                                          fullname=escape_markdown(fullname), username=username, mention=mention,
                                          count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = sql.DEFAULT_GOODBYE
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(update, res, keyboard, sql.DEFAULT_GOODBYE)
            delete_join(bot, update)


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    # if no args, show current replies.
    if len(args) == 0 or args[0].lower() == "noformat":
        noformat = args and args[0].lower() == "noformat"
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            "Bu sohbetin karşılama ayarı şu şekilde ayarlanmıştır: `{}`.\n*karşılama mesajı "
            "(doldurmamak {{}}) is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

            else:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("üzerinde", "evet"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("Kibar olacağım!")

        elif args[0].lower() in ("kapalı", "hayır"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("Somurtuyorum, artık merhaba demiyorum.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("Sadece 'açık/evet' veya 'kapalı/hayır' anlıyorum!")


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]

    if len(args) == 0 or args[0] == "noformat":
        noformat = args and args[0] == "noformat"
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            "Bu sohbetin veda ayarı şu şekilde ayarlanmıştır: `{}`.\n*veda mesajı "
            "(doldurmamak {{}}) is:*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("üzerinde", "evet"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("İnsanlar gittiğinde üzüleceğim!")

        elif args[0].lower() in ("kapalı", "hayır"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Gidiyorlar, benim için ölüler.")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text("Sadece 'açık/evet' veya 'kapalı/hayır' anlıyorum!")


@run_async
@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Ne cevap vereceğinizi belirtmemişsiniz!")
        return ""

    sql.set_custom_welcome(chat.id, content or text, data_type, buttons)
    msg.reply_text("Özel karşılama mesajını başarıyla ayarla!")

    return "<b>{}:</b>" \
           "\n#SET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nKarşılama mesajını ayarlayın.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_welcome(chat.id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("Karşılama mesajını başarıyla varsayılana sıfırlayın!")
    return "<b>{}:</b>" \
           "\n#RESET_WELCOME" \
           "\n<b>Admin:</b> {}" \
           "\nKarşılama mesajını varsayılana sıfırlayın.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def set_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Ne cevap vereceğinizi belirtmemişsiniz!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("Özel veda mesajını başarıyla ayarla!")
    return "<b>{}:</b>" \
           "\n#SET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nHoşçakal mesajını ayarlayın.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("Hoşçakal mesajını başarıyla varsayılana sıfırla!")
    return "<b>{}:</b>" \
           "\n#RESET_GOODBYE" \
           "\n<b>Admin:</b> {}" \
           "\nHoşçakal mesajını sıfırlayın.".format(html.escape(chat.title),
                                                 mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def clean_welcome(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text("İki güne kadar olan karşılama mesajlarını silmeliyim.")
        else:
            update.effective_message.reply_text("Şu anda eski karşılama mesajlarını silmiyorum!")
        return ""

    if args[0].lower() in ("üzerinde", "evet"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("Eski karşılama mesajlarını silmeye çalışacağım!")
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nTemiz karşılama arasında geçiş yaptı <code>ON</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[0].lower() in ("kapalı", "hayır"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("Eski karşılama mesajlarını silmeyeceğim.")
        return "<b>{}:</b>" \
               "\n#CLEAN_WELCOME" \
               "\n<b>Admin:</b> {}" \
               "\nTemiz karşılama arasında geçiş yaptı <code>OFF</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        # idek what you're writing, say yes or no
        update.effective_message.reply_text("Sadece 'açık/evet' veya 'kapalı/hayır' anlıyorum!")
        return ""


WELC_HELP_TXT = "Grubunuzun karşılama/hoşçakal mesajları birçok şekilde kişiselleştirilebilir. mesajları istersen" \
                " varsayılan karşılama mesajı gibi bireysel olarak oluşturulmak için *bu* değişkenleri kullanabilirsiniz:\n" \
                " - `{{first}}`: bu, kullanıcının *ad* adını temsil eder\n" \
                " - `{{last}}`: bu, kullanıcının *soyadı* adını temsil eder. Kullanıcının adı yoksa varsayılan olarak *ad* " \
                "SoyAdı.\n" \
                " - `{{fullname}}`: bu, kullanıcının *tam* adını temsil eder. Kullanıcının adı yoksa varsayılan olarak *ad* " \
                "SoyAdı.\n" \
                " - `{{username}}`: bu, kullanıcının *kullanıcı adını* temsil eder. Varsayılan olarak, kullanıcının bir *bahsetmesi* " \
                "kullanıcı adı yoksa ilk ad.\n" \
                " - `{{mention}}`: bu sadece bir kullanıcıdan *bahsedilir* - onları ilk adlarıyla etiketler.\n" \
                " - `{{id}}`: bu kullanıcının *kimliğini* temsil eder\n" \
                " - `{{count}}`: bu, kullanıcının *üye numarasını* temsil eder.\n" \
                " - `{{chatname}}`: bu *geçerli sohbet adını* temsil eder.\n" \
                "\nHer bir değişkenin çevrelenmesi ZORUNLUDUR `{{}}` değiştirilecek.\n" \
                "Karşılama mesajları ayrıca işaretlemeyi de destekler, böylece herhangi bir öğeyi kalın/italik/kod/bağlantılar yapabilirsiniz. " \
                "Düğmeler de desteklenir, böylece hoş bir girişle karşılamalarınızın harika görünmesini sağlayabilirsiniz. " \
                "düğmeler.\n" \
                "Kurallarınıza bağlanan bir düğme oluşturmak için bunu kullanın: `[Kurallar](buttonurl://t.me/{}?start=group_id)`. " \
                "'group_id' yerine /id yoluyla edinebileceğiniz grubunuzun kimliğiyle değiştirin ve " \
                "Git. Grup kimliklerinin başında genellikle bir "-" işaretinin geldiğine dikkat edin; bu gerekli, bu yüzden lütfen yapma " \
                "onu kaldır.\n" \
                "Eğleniyorsanız, resimleri/gifleri/videoları/sesli mesajları karşılama mesajı olarak bile ayarlayabilirsiniz. " \
                "istenen medyaya yanıt verme ve /setwelcome arama.".format(dispatcher.bot.username)


@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    return "Bu sohbetin karşılama tercihi şu şekilde ayarlandı: `{}`.\n" \
           "Bu veda tercihi `{}`.".format(welcome_pref, goodbye_pref)


__help__ = """
{}

*Yalnızca yönetici:*
 - /welcome <açık/kapalı>: karşılama mesajlarını etkinleştirir/devre dışı bırakır.
 - /welcome: mevcut karşılama ayarlarını gösterir.
 - /welcome noformat: biçimlendirme olmadan mevcut karşılama ayarlarını gösterir - karşılama mesajlarınızı geri dönüştürmek için kullanışlıdır!
 - /hoşçakal -> /welcome ile aynı kullanım ve argümanlar.
 - /setwelcome <sometext>: özel bir karşılama mesajı ayarlayın. Medyaya yanıt vermek için kullanılıyorsa, o medyayı kullanır.
 - /setgoodbye <sometext>: özel bir veda mesajı ayarlayın. Medyaya yanıt vermek için kullanılıyorsa, o medyayı kullanır.
 - /resetwelcome: varsayılan karşılama mesajına sıfırlayın.
 - /resetgoodbye: varsayılan hoşçakal mesajına sıfırlayın.
 - /cleanwelcome <açık/kapalı>: Yeni üyede, sohbetin spam olmasını önlemek için önceki karşılama mesajını silmeyi deneyin.
 - /clearjoin <on/off>: biri katıldığında, grup mesajına katılan *kullanıcıyı* silmeyi deneyin.
 - /welcomehelp: özel karşılama/güle güle mesajları için daha fazla biçimlendirme bilgisi görüntüleyin.

""".format(WELC_HELP_TXT)

__mod_name__ = "Greetings"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("hoşgeldiniz", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("Güle Güle", goodbye, pass_args=True, filters=Filters.group)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, pass_args=True, filters=Filters.group)
DEL_JOINED = CommandHandler("clearjoin", del_joined, pass_args=True, filters=Filters.group)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)


dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(DEL_JOINED)
dispatcher.add_handler(WELCOME_HELP)
