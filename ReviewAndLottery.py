
import datetime
from telegram import Update
from telegram.ext import ContextTypes
import BotSettings as BS
import ButtonHandler as BH
import logging

def lot_code_cheack(user_id,mode=""):
    if mode == "Code":
        code_user = BS.users_collection.find_one({"_id":user_id, "Mode": mode})
    else:
        code_user = BS.users_collection.find_one({"_id":user_id})
    part_number =code_user["course_part_number"]-1
    code_course = BS.courses_collection.find_one({"part_number":part_number})
    return code_course["lot_code"]


async def send_review_lotcode(update: Update, context: ContextTypes.DEFAULT_TYPE,mode):
    if update.message.chat.type != 'private':
        return
    user_id = update.message.from_user.id
    user = BS.users_collection.find_one({"_id" : user_id})
    time_threshold = datetime.datetime.now() - datetime.timedelta(seconds=BS.Delete_Time_Second)
    old_user = BS.users_collection.find_one({"_id":user_id, "LastDownload": {"$lt": time_threshold.isoformat()}, "RemindCheck" : False})
    if old_user:
        BS.users_collection.update_one({"_id": user_id}, {"$set": {"Mode":"Normal"}})
        await update.message.reply_text("زمان ارسال شما به پایان رسیده است.",reply_markup=BH.show_buttons(update, context,"Normal"))
        return
    if user_id != BS.ADMIN_USER_ID:
        if not user :
            return
        if user["Mode"] =="End":
            if mode == "Code":
                return
        else :
            BS.users_collection.update_one({"_id": user_id}, {"$set": {"Mode":mode}})#practric and review
        if(mode == "Review"):
            await update.message.reply_text("میتوانید نظرات و تمارین خود را ارسال کنید",reply_markup=BH.show_buttons(update, context,mode))
        elif(mode == "Code"):
            if(lot_code_cheack(user_id,"Code")=="None"):
                await update.message.reply_text("این قسمت کد قرعه کشی ندارد",reply_markup=BH.show_buttons(update, context,mode))
            else:
                await update.message.reply_text("کد قرعه کشی خود را ارسال کنید",reply_markup=BH.show_buttons(update, context,mode))
        elif(mode == "Course"):
                await update.message.reply_text("لغو ارسال",reply_markup=BH.show_buttons(update, context,mode))
