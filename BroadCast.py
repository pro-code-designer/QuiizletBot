import logging
from telegram import Update
from telegram.ext import ContextTypes
import BotSettings as BS
import ButtonHandler as BH
 
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE,delete_mode):
    if update.message.chat.type != 'private':
        logging.info(update.message.chat_id)
        # Ignore the message if it is from a group
        return
    user = int(context.args[0]) if context.args else None
    if user:
        BS.broadcast_Type="single"
        BS.broadcast_User_ID = user
    else:
        BS.broadcast_Type="multiple"
    BS.broadcast_delete_mode = delete_mode
    logging.info(update.message.chat_id)
    BS.adding_course_part = False
    if update.message.from_user.id == BS.ADMIN_USER_ID:
        BS.broadcast_mode = True
        await update.message.reply_text("حالت پخش شروع شد. هر محتوایی را ارسال کنید تا به تمام کاربران پخش شود.\nبرای پایان دادن، /stop_broadcast را وارد کنید.",reply_markup=BH.show_buttons(update, context,"Broadcast"))
    else:
        await update.message.reply_text("شما مجاز به شروع پخش نیستید.")

async def stop_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        # Ignore the message if it is from a group
        return
    if update.message.from_user.id == BS.ADMIN_USER_ID:
        BS.broadcast_mode = False
        await update.message.reply_text("حالت پخش متوقف شد.",reply_markup=BH.show_buttons(update, context,"Normal"))
    else:
        await update.message.reply_text("شما مجاز به متوقف کردن پخش نیستید.")
