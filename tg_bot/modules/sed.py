
import re
import sre_constants

import telegram
from telegram import Update, Bot
from telegram.ext import run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleRegexHandler

DELIMITERS = ("/", ":", "|", "_")


def separate_sed(sed_string):
    if len(sed_string) >= 3 and sed_string[1] in DELIMITERS and sed_string.count(sed_string[1]) >= 2:
        delim = sed_string[1]
        start = counter = 2
        while counter < len(sed_string):
            if sed_string[counter] == "\\":
                counter += 1

            elif sed_string[counter] == delim:
                replace = sed_string[start:counter]
                counter += 1
                start = counter
                break

            counter += 1

        else:
            return None

        while counter < len(sed_string):
            if sed_string[counter] == "\\" and counter + 1 < len(sed_string) and sed_string[counter + 1] == delim:
                sed_string = sed_string[:counter] + sed_string[counter + 1:]

            elif sed_string[counter] == delim:
                replace_with = sed_string[start:counter]
                counter += 1
                break

            counter += 1
        else:
            return replace, sed_string[start:], ""

        flags = ""
        if counter < len(sed_string):
            flags = sed_string[counter:]
        return replace, replace_with, flags.lower()


@run_async
def sed(bot: Bot, update: Update):
    sed_result = separate_sed(update.effective_message.text)
    if sed_result and update.effective_message.reply_to_message:
        if update.effective_message.reply_to_message.text:
            to_fix = update.effective_message.reply_to_message.text
        elif update.effective_message.reply_to_message.caption:
            to_fix = update.effective_message.reply_to_message.caption
        else:
            return

        repl, repl_with, flags = sed_result

        if not repl:
            update.effective_message.reply_to_message.reply_text("yerine koymaya ??al??????yorsun... "
                                                                 "bir ??eyle hi??bir ??ey?")
            return

        try:
            check = re.match(repl, to_fix, flags=re.IGNORECASE)

            if check and check.group(0).lower() == to_fix.lower():
                update.effective_message.reply_to_message.reply_text("Selam millet, {} yapmaya ??al??????yor "
                                                                     "istemedi??im ??eyler s??yl??yorum "
                                                                     "s??ylemek!".format(update.effective_user.first_name))
                return

            if 'i' in flags and 'g' in flags:
                text = re.sub(repl, repl_with, to_fix, flags=re.I).strip()
            elif 'i' in flags:
                text = re.sub(repl, repl_with, to_fix, count=1, flags=re.I).strip()
            elif 'g' in flags:
                text = re.sub(repl, repl_with, to_fix).strip()
            else:
                text = re.sub(repl, repl_with, to_fix, count=1).strip()
        except sre_constants.error:
            LOGGER.warning(update.effective_message.text)
            LOGGER.exception("SRE sabit hatas??")
            update.effective_message.reply_text("Hatta sed misin? G??r??n????e g??re ??yle de??il.")
            return

        # empty string errors -_-
        if len(text) >= telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text("sed komutunun sonucu i??in ??ok uzundu \
                                                 telegram!")
        elif text:
            update.effective_message.reply_to_message.reply_text(text)


__help__ = """
 - s/<text1>/<text2>(/<flag>): Bir mesaja, o mesajda bir sed i??lemi ger??ekle??tirmek i??in t??m \ yerine bununla yan??t verin
'text2' ile 'text1' olu??umlar??. Bayraklar iste??e ba??l??d??r ve ??u anda yoksayma durumu i??in 'i', global i??in 'g', \
veya hi??bir??ey. Ay??r??c??lar aras??nda `/`, `_`, `|` ve `:` bulunur. Metin grupland??rma desteklenir. Ortaya ????kan mesaj \ olamaz
daha geni?? {}.
*Hat??rlat??c??:* Sed, e??le??tirmeyi kolayla??t??rmak i??in a??a????daki gibi baz?? ??zel karakterler kullan??r: `+*.?\\`
Bu karakterleri kullanmak istiyorsan??z, onlardan ka??t??????n??zdan emin olun!
??rne??in: \\?.
""".format(telegram.MAX_MESSAGE_LENGTH)

__mod_name__ = "Sed/Regex"


SED_HANDLER = DisableAbleRegexHandler(r's([{}]).*?\1.*'.format("".join(DELIMITERS)), sed, friendly="sed")

dispatcher.add_handler(SED_HANDLER)
