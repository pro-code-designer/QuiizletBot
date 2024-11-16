import BotSettings as BS
import ButtonHandler as BH
import BroadCast as BC
import Courses as CS
import DataHandler as DH
import ReviewAndLottery as RAL
import datetime
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user_id = update.message.from_user.id
    user = BS.users_collection.find_one({"_id": user_id})
    # Send the appropriate text message
    if user and user.get("contact"):
        if user["Mode"] =="End":
            return
        await update.message.reply_text(
            "خوش آمدید! شما قبلاً اطلاعات تماس خود را به اشتراک گذاشته‌اید.",
            reply_markup=BH.show_buttons(update, context, "Normal")
        )
    else:
        contact_button = KeyboardButton("اشتراک اطلاعات تماس ", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "برای ورود و شروع آموزش‌ها نیاز به یه حساب کاربری داری که سریع برات می‌سازیمش😎\n\n"
            "رفیق حساب کاربریت با شماره خودت ساخته میشه پس روی کلید زیر بزنید❤️👇",
            reply_markup=reply_markup
        )

# Periodic task to delete messages older than 24 hours
async def delete_old_messages(context: ContextTypes.DEFAULT_TYPE):
    while True:
        time_threshold = datetime.datetime.now() - datetime.timedelta(seconds=BS.Delete_Time_Second)

        old_messages = BS.messages_collection.find({"timestamp": {"$lt": time_threshold.isoformat()}})
        if not old_messages:
            return

        for message in old_messages:
            user_id = message["user_id"]
            message_id = message["message_id"]
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=message_id)
                BS.messages_collection.delete_one({"_id": message["_id"]})
            except BadRequest as e:
                if "Message to delete not found" in str(e):
                    logging.warning(f"Message {message_id} for user {user_id} not found. Removing from database.")
                    BS.messages_collection.delete_one({"_id": message["_id"]})
                else:
                    # Log other BadRequest errors
                    logging.error(f"Unexpected error while deleting message {message_id}: {e}")
            except Exception as e:
                logging.error(f"An error occurred while deleting message {message_id}: {e}")

        old_users = BS.users_collection.find({"LastDownload": {"$lt": time_threshold.isoformat()}, "RemindCheck" : False})
        for old_user in old_users:
            user_id = old_user["_id"]
            new_course = BS.courses_collection.find_one({"part_number": old_user["course_part_number"]})
            if new_course:
                if new_course["lot_code"] == "Auto":
                    await CS.send_course_parts(user_id , context)
                else:
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="بخش های قبلی دوره پاک شده و شما میتوانید بخش ها جدید را دانلود کنید",
                            reply_markup=BH.show_buttons("GZ",user_id, "Normal")
                         )
                
                        BS.users_collection.update_one({"_id": user_id}, {"$set": {"RemindCheck" : True, "Mode":"Normal"}})
                    except Exception as e:
                        logging.error(f"Failed to send delete message")

        await asyncio.sleep(BS.Check_Time_Second)


# Main function to start the bot
def main():
    BS.biggest_course_part_number = CS.get_max_code_part()
    application = Application.builder().token(BS.Bot_Token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, DH.contact_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, DH.name_handler))
    application.add_handler(CommandHandler("start_broadcast", lambda update, context: BC.start_broadcast(update, context, True)))
    application.add_handler(CommandHandler("start_no_delete_broadcast", lambda update, context: BC.start_broadcast(update, context, False)))
    application.add_handler(CommandHandler("stop_broadcast", BC.stop_broadcast))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, DH.broadcast_content))
    application.add_handler(CommandHandler("add_course_part", CS.add_course_part))
    application.add_handler(CommandHandler("end_course_part", CS.end_course_part))
    application.add_handler(CommandHandler("get_course_parts", CS.send_course_parts))
    application.add_handler(CommandHandler("send_practices_review",lambda update, context: RAL.send_review_lotcode(update,context,"Review")))
    application.add_handler(CommandHandler("send_code",lambda update, context: RAL.send_review_lotcode(update,context,"Code" )))
    application.add_handler(CommandHandler("end_send",lambda update, context: RAL.send_review_lotcode(update,context,"Normal" )))

    # Add the periodic task to the job queue
    application.job_queue.run_repeating(delete_old_messages, interval=BS.Check_Time_Second, first=0)

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
