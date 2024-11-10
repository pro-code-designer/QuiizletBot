import os
import logging
import datetime
import asyncio
import ast
from pymongo import MongoClient
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove 
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://cnoi1986Assdn:55Xg804U3SMsa@localhost:2617/")
  # Replace with your MongoDB URI
client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]  # Database name
users_collection = db["users"]
messages_collection = db["messages"]
courses_collection = db["courses"]  # New collection for storing course parts
lottery_collection = db["lottery_database"] 

# Replace with your admin user ID
ADMIN_USER_ID = 281349921
SAVR_GP_ID = -1002250211802
Bot_Token = "7393447211:AAFPRoa203ot_z9uqaVdvBu6L1K-mFxslSw"
Check_Time_Second = 3600
Delete_Time_Second = 24*3600

# Initialize broadcast mode and course part flag
broadcast_mode = False
broadcast_delete_mode = False
adding_course_part = False
current_course_part_number = None
biggest_course_part_number = 0
current_course_part_content = []
current_course_lot_code="testlot"

def get_max_code_part():
    max_document = courses_collection.find_one(sort=[("part_number", -1)])
    if max_document and "part_number" in max_document:
        return max_document["part_number"]
    else:
        return 0

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = users_collection.find_one({"_id": user_id})

    if user and user.get("contact"):
        await update.message.reply_text("خوش آمدید! شما قبلاً اطلاعات تماس خود را به اشتراک گذاشته‌اید.",reply_markup=show_buttons(update, context,"Normal"))
        
    else:
        contact_button = KeyboardButton("اشتراک اطلاعات تماس ", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("برای ورود و شروع آموزش‌ها نیاز به یه حساب کاربری داری که سریع برات می‌سازیمش😎\n\nرفیق حساب کاربریت با شماره خودت ساخته میشه پس روی کلید زیر بزنید❤️👇", reply_markup=reply_markup)

# Contact handler
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        # Ignore the message if it is from a group
        return
    contact = update.message.contact
    name = update.message.from_user.full_name
    user_id = update.message.from_user.id

    if users_collection.find_one({"_id": user_id, "contact": {"$exists": True}}):
        await update.message.reply_text("خوش آمدید! شما قبلاً اطلاعات تماس خود را به اشتراک گذاشته‌اید.")
        return
    LastDownload = (datetime.datetime.now() - datetime.timedelta(seconds=Delete_Time_Second)).isoformat()
    users_collection.update_one(
        {"_id": user_id},
        {"$set": {"Telegram_name": name, "contact": contact.phone_number, "awaiting_name": True, "course_part_number": 1, "LastDownload" : LastDownload, "RemindCheck" : True, "Mode" : "Normal"}},
        upsert=True
    )

    await update.message.reply_text(f"لطفاً اسم و فامیلیتم برامون بنویس و ارسالش کن😍", reply_markup=ReplyKeyboardRemove())

# name handler
async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    name = update.message.text
    if len(name) > 60:
        update.message.reply_text("نام شما خیلی طولانی است. لطفاً آن را زیر 60 کاراکتر نگه دارید.")
        return
    user_id = update.message.from_user.id
    user = users_collection.find_one({"_id": user_id})

    if user and user.get("awaiting_name"):
        users_collection.update_one({"_id": user_id}, {"$set": {"name": name, "awaiting_name": False}})
        await update.message.reply_text(f"{name} عزیز شما با موفقیت عضو خانواده بزرگ کوییزلت شدین🥳🥰💛\nقبل از اینکه این چالشو شروع کنیم حتماً به ویس میثاق و تینا گوش بدین تا کامل دستورالعمل این دوره رو متوجه بشین👇",reply_markup=show_buttons(update, context,"Normal"))
        await update.message.reply_text("برای شروع چالش ۳کلید 🔑 بروی کلید زیر بزنید و متعهدانه آموزش هارو شروع کنید❤️",reply_markup=show_buttons(update, context,"Normal"))
    elif await button_callback(update, context,name):
        pass
    else:
        await broadcast_content(update, context)

# Start broadcasting command
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE,delete_mode):
    if update.message.chat.type != 'private':
        # Ignore the message if it is from a group
        return
    global broadcast_mode, adding_course_part,broadcast_delete_mode
    broadcast_delete_mode = delete_mode
    logging.info(update.message.chat_id)
    adding_course_part = False
    if update.message.from_user.id == ADMIN_USER_ID:
        broadcast_mode = True
        await update.message.reply_text("حالت پخش شروع شد. هر محتوایی را ارسال کنید تا به تمام کاربران پخش شود.\nبرای پایان دادن، /stop_broadcast را وارد کنید.",reply_markup=show_buttons(update, context,"Broadcast"))
    else:
        await update.message.reply_text("شما مجاز به شروع پخش نیستید.")

# Stop broadcasting command
async def stop_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        # Ignore the message if it is from a group
        return
    global broadcast_mode
    if update.message.from_user.id == ADMIN_USER_ID:
        broadcast_mode = False
        await update.message.reply_text("حالت پخش متوقف شد.",reply_markup=show_buttons(update, context,"Normal"))
    else:
        await update.message.reply_text("شما مجاز به متوقف کردن پخش نیستید.")

# Message handler for broadcasting content
async def broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        # Ignore the message if it is from a group
        return
    global broadcast_mode,broadcast_delete_mode
    if broadcast_mode and update.message.from_user.id == ADMIN_USER_ID:
        user_ids = users_collection.distinct("_id")
        timestamp = datetime.datetime.now().isoformat()

        for user_id in user_ids:
            try:
                sent_message = await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                if(broadcast_delete_mode):
                    messages_collection.insert_one({"user_id": user_id, "message_id": sent_message.message_id, "message_type": "broadcast", "timestamp": timestamp})
            except Exception as e:
                logging.error(f"Failed to send message to {user_id}: {e}")
    else:
        await course_content_handler(update, context)

# Course part handlers
async def add_course_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    global adding_course_part, current_course_part_number, current_course_part_content, broadcast_mode,biggest_course_part_number,current_course_lot_code
    broadcast_mode = False
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("شما مجاز به افزودن قسمت‌های دوره نیستید.")
        return

    if adding_course_part:
        await update.message.reply_text("یک قسمت از دوره در حال افزودن است. برای پایان دادن، /end_course_part را وارد کنید.",reply_markup=show_buttons(update, context,"Course"))
        return

    # Get the part number from the command arguments
    try:
        part_number = int(context.args[0]) if context.args else None
        lot_code =context.args[1] if context.args else None
        if (not part_number) or (not lot_code):
            await update.message.reply_text( "لطفاً شماره قسمت را با دستور وارد کنید: /add_course_part <شماره دوره> <کد قرعه کشی>")
            return
    except:
        await update.message.reply_text( "لطفاً شماره قسمت را با دستور وارد کنید: /add_course_part <شماره دوره> <کد قرعه کشی>")
        return

    # Check if the new part number exceeds the largest part number by more than 2
    if part_number > biggest_course_part_number + 1:
        await update.message.reply_text(f"خطا: شما نمی‌توانید قسمت {part_number} را اضافه کنید زیرا این قسمت بیشتر از ({biggest_course_part_number+1}) است.")
        return

    current_course_lot_code = lot_code
    # Proceed with adding the new course part
    current_course_part_number = part_number
    current_course_part_content = []
    adding_course_part = True

    await update.message.reply_text(f"در حال افزودن محتوا برای قسمت دوره {part_number} هستیم. لطفاً محتوا را در پیام‌ها ارسال کنید. برای پایان دادن، /end_course_part را وارد کنید.",reply_markup=show_buttons(update, context,"Course"))

async def end_course_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    global adding_course_part, current_course_part_number, current_course_part_content,biggest_course_part_number
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("شما مجاز به پایان دادن به قسمت دوره نیستید.")
        return

    if not adding_course_part:
        await update.message.reply_text("هیچ قسمتی از دوره در حال افزودن نیست.",reply_markup=show_buttons(update, context,"Course"))
        return

    # Create the course part data
    course_part = {
        "part_number": current_course_part_number,
        "content": "\n".join(current_course_part_content),
        "lot_code":current_course_lot_code,
    }

    # Update or insert the course part in the database
    result = courses_collection.update_one(
        {"part_number": current_course_part_number},  # Search by part_number
        {"$set": course_part},  # Update the existing record or set new data
        upsert=True  # If no record exists, insert a new one
    )

    # Reset the flags
    adding_course_part = False
    print_num = current_course_part_number
    current_course_part_number = None
    current_course_part_content = []

    if result.matched_count > 0:
        await update.message.reply_text(f"قسمت دوره {print_num} با موفقیت به روز رسانی شد.",reply_markup=show_buttons(update, context,"Normal"))
    else:
        await update.message.reply_text(f"قسمت دوره {print_num} با موفقیت اضافه شد.",reply_markup=show_buttons(update, context,"Normal"))
        biggest_course_part_number += 1

async def course_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global adding_course_part, current_course_part_content
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    if adding_course_part and user_id == ADMIN_USER_ID:
        current_course_part_content.append(str({"user_id": user_id, "message_id": message_id}))
        await update.message.reply_text("محتوا اضافه شد. برای ادامه افزودن، ادامه دهید یا برای پایان دادن /end_course_part را تایپ کنید.")
    else:
        await user_data_handler(update, context)
        
async def user_data_handler (update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    par_user = users_collection.find_one({"_id":user_id, "Mode": "Review"})
    code_user = users_collection.find_one({"_id":user_id, "Mode": "Code"})
    if user_id != ADMIN_USER_ID:
        if par_user:
            await context.bot.forward_message(
                    chat_id=SAVR_GP_ID,
                    from_chat_id=user_id, 
                    message_id=message_id
                )
            await update.message.reply_text("نظر شما با موفقیت ثبت شد.🥳❤️ می‌توانید با استفاده از دکمه 'پایان ارسال' را به پایان برسانید یا ادامه دهید.")
        """elif code_user:
            part_number =code_user["course_part_number"]-1
            code_course = courses_collection.find_one({"part_number":part_number})
            try:
                if update.message.text and code_course and update.message.text.strip() == code_course["lot_code"]:
                    try:
                        if lottery_collection.find_one({"user_id": user_id, "course_part" : part_number}):
                            await update.message.reply_text("شما قبلاً در قرعه‌کشی این بخش دوره ثبت‌نام کرده‌اید.")
                            return
                    except:
                        pass
                    lottery_collection.update_one({"course_part" : part_number, "user_id": user_id},
                        {"$set":{"timestamp": datetime.datetime.now().isoformat()}},
                        upsert=True
                    )
                    await update.message.reply_text("تبریک! کد قرعه‌کشی شما تایید شد و با موفقیت در قرعه‌کشی ثبت‌نام شدید.")
                else:
                    await update.message.reply_text("متاسفیم! کد قرعه‌کشی وارد شده نامعتبر است. لطفاً دوباره تلاش کنید.")
            except Exception as e:
                logging.error(f"Error inserting into lottery collection: {e}")
                await update.message.reply_text("متاسفیم! مشکلی پیش آمده است. لطفاً دوباره تلاش کنید.")"""

# Periodic task to delete messages older than 24 hours
async def delete_old_messages(context: ContextTypes.DEFAULT_TYPE):
    while True:
        time_threshold = datetime.datetime.now() - datetime.timedelta(seconds=Delete_Time_Second)

        old_messages = messages_collection.find({"timestamp": {"$lt": time_threshold.isoformat()}})
        if not old_messages:
            return

        for message in old_messages:
            user_id = message["user_id"]
            message_id = message["message_id"]
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=message_id)
                messages_collection.delete_one({"_id": message["_id"]})
            except Exception as e:
                logging.error(f"Failed to delete message {message_id} for user {user_id}: {e}")

        old_users = users_collection.find({"LastDownload": {"$lt": time_threshold.isoformat()}, "RemindCheck" : False})
        for old_user in old_users:
            user_id = old_user["_id"]
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="بخش های قبلی دوره پاک شده و شما میتوانید بخش ها جدید را دانلود کنید",
                    reply_markup=show_buttons("GZ",user_id, "Normal")
                 )
                
                users_collection.update_one({"_id": user_id}, {"$set": {"RemindCheck" : True, "Mode":"Normal"}})
            except Exception as e:
                    logging.error(f"Failed to send delete message")

        await asyncio.sleep(Check_Time_Second)

# Function to send course parts to users
async def send_course_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    user_id = update.message.from_user.id
    time_threshold = datetime.datetime.now() - datetime.timedelta(seconds=Delete_Time_Second)
    # Fetch all course parts from the database
    user_Data = users_collection.find_one(
        {"_id": user_id},
        )
    # If the user has received a 'course' message in the last 24 hours, deny the request
    if user_Data and user_Data["LastDownload"] > time_threshold.isoformat():
        await update.message.reply_text("شما بخش‌های دوره را در ۲۴ ساعت گذشته دریافت کرده‌اید. لطفاً کمی صبر کنید و سپس دوباره درخواست کنید.",reply_markup=show_buttons(update, context,"Course"))
        return

    user_data = users_collection.find_one({"_id": user_id})
    course_part_number = user_data['course_part_number']
    logging.info(course_part_number)
    course_part = courses_collection.find_one({"part_number": course_part_number})
    if not course_part:
        await update.message.reply_text("هیچ بخشی از دوره برای ارسال موجود نیست.",reply_markup=show_buttons(update, context,"Normal"))
        return

    now = datetime.datetime.now().isoformat()
    try:
        # Send the course part content to the user
        content_str = str(course_part['content'])
        #===========================================================================================
        content_items = content_str.split('\n')
        # Loop through each item and process it
        for item in content_items:
        
            # Convert the string to a dictionary using ast.literal_eval
            logging.info(item)
            content = ast.literal_eval(item)
        
            # Extract user_id and message_id
            user_id = content['user_id']
            message_id = content['message_id']
        
            # Send the message using bot.copy_message
            sent_message = await context.bot.copy_message(
                chat_id=update.message.chat_id,
                from_chat_id=user_id, 
                message_id=message_id
            )
            messages_collection.insert_one({"user_id": update.message.chat_id, "message_id": sent_message.message_id, "message_type": "course", "timestamp": now})
        users_collection.update_one(
            {"_id": update.message.from_user.id},
            {"$inc": {"course_part_number": 1}}  # Increment the course_part_number by 1
        )
        users_collection.update_one({"_id": update.message.from_user.id}, {"$set": {"LastDownload": now, "RemindCheck" : False}})
        await update.message.reply_text("منتظر تمرینت هستیما!❤️",reply_markup=show_buttons(update, context,"Course"))
        logging.info(f"Sent course part {course_part['part_number']} to user {user_id}")
    except Exception as e:
        logging.error(f"Failed to send course part to {user_id}: {e}")

async def send_review_lotcode(update: Update, context: ContextTypes.DEFAULT_TYPE,mode):
    if update.message.chat.type != 'private':
        return
    user_id = update.message.from_user.id
    time_threshold = datetime.datetime.now() - datetime.timedelta(seconds=Delete_Time_Second)
    old_user = users_collection.find_one({"_id":user_id, "LastDownload": {"$lt": time_threshold.isoformat()}, "RemindCheck" : False})
    if old_user:
        users_collection.update_one({"_id": user_id}, {"$set": {"Mode":"Normal"}})
        await update.message.reply_text("زمان ارسال شما به پایان رسیده است.",reply_markup=show_buttons(update, context,"Normal"))
        return
    if user_id != ADMIN_USER_ID:
        users_collection.update_one({"_id": user_id}, {"$set": {"Mode":mode}})#practric and review
        if(mode == "Review"):
            await update.message.reply_text("میتوانید نظرات و تمارین خود را ارسال کنید",reply_markup=show_buttons(update, context,mode))
        #elif(mode == "Code"):
            #await update.message.reply_text("کد قرعه کشی خود را ارسال کنید",reply_markup=show_buttons(update, context,mode))
        elif(mode == "Course"):
                await update.message.reply_text("لغو ارسال",reply_markup=show_buttons(update, context,mode))


def show_buttons(update, context, mode):
    if update != "GZ":
        user_id = update.effective_user.id
    else:
        user_id = context
    keyboard = []

    if (ADMIN_USER_ID == user_id):
        # If user is admin, show all the admin buttons
        if(mode == "Normal"):
            keyboard = [
                [KeyboardButton("شروع بازپخش")],
                [KeyboardButton("شروع باز پخش بدون پاک شدن")],
                [KeyboardButton("اضافه کردن دوره")]
            ]
        elif(mode == "Broadcast"):
            keyboard = [
                [KeyboardButton("پایان بازپخش")]
            ]
        elif(mode == "Course"):
            keyboard = [
                [KeyboardButton("پایان دوره")]
            ]
    else:
        if(mode == "Normal"):
            keyboard = [
                [KeyboardButton("دریافت کلید🔑\nبزن بریم❤️‍🔥")]
            ]
        elif(mode == "Course"):
            keyboard = [
                [KeyboardButton("ارسال تکالیف و نظرات")],
                #[KeyboardButton("ارسال کد قرعه کشی")]
            ]
        elif(mode == "Review"):
            keyboard = [
                [KeyboardButton("پایان ارسال")]
            ]
        """elif(mode == "Code"):
            keyboard = [
                [KeyboardButton("لغو ارسال")]
            ]"""
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)#, one_time_keyboard=True)
    return reply_markup

async def button_callback(update, context,data):
    if data == "شروع بازپخش":
        await start_broadcast(update, context, True)
    elif data == "شروع باز پخش بدون پاک شدن":
        await start_broadcast(update, context, False)
    elif data == "پایان بازپخش":
        await stop_broadcast(update, context)
    elif data == "اضافه کردن دوره":
        await add_course_part(update, context)
    elif data == "پایان دوره":
        await end_course_part(update, context)
    elif data == "دریافت کلید🔑:\nبزن بریم❤️‍🔥":
        await send_course_parts(update, context)
    elif data == "ارسال تکالیف و نظرات":
        await send_review_lotcode(update,context,"Review")
    #elif data == "ارسال کد قرعه کشی":
        #await send_review_lotcode(update,context,"Code")
    elif data == "پایان ارسال":# or data == "لغو ارسال":
        await send_review_lotcode(update,context,"Course")
    else:
        return False
    return True
# Main function to start the bot
def main():
    global biggest_course_part_number
    biggest_course_part_number = get_max_code_part()
    application = Application.builder().token(Bot_Token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler))
    application.add_handler(CommandHandler("start_broadcast", lambda update, context: start_broadcast(update, context, True)))
    application.add_handler(CommandHandler("start_no_delete_broadcast", lambda update, context: start_broadcast(update, context, False)))
    application.add_handler(CommandHandler("stop_broadcast", stop_broadcast))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_content))
    application.add_handler(CommandHandler("add_course_part", add_course_part))
    application.add_handler(CommandHandler("end_course_part", end_course_part))
    application.add_handler(CommandHandler("get_course_parts", send_course_parts))
    application.add_handler(CommandHandler("send_practices_review",lambda update, context: send_review_lotcode(update,context,"Review")))
    #application.add_handler(CommandHandler("send_code",lambda update, context: send_review_lotcode(update,context,"Code" )))
    application.add_handler(CommandHandler("end_send",lambda update, context: send_review_lotcode(update,context,"Normal" )))

    # Add the periodic task to the job queue
    application.job_queue.run_repeating(delete_old_messages, interval=Check_Time_Second, first=0)

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
