import logging
from telegram import Update
from telegram.ext import ContextTypes
import datetime
import BotSettings as BS
import ButtonHandler as BH
import ast

def get_max_code_part():
    max_document = BS.courses_collection.find_one(sort=[("part_number", -1)])
    if max_document and "part_number" in max_document:
        return max_document["part_number"]
    else:
        return 0
    
async def add_course_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    BS.broadcast_mode = False
    if update.message.from_user.id != BS.ADMIN_USER_ID:
        await update.message.reply_text("شما مجاز به افزودن قسمت‌های دوره نیستید.")
        return

    if BS.adding_course_part:
        await update.message.reply_text("یک قسمت از دوره در حال افزودن است. برای پایان دادن، /end_course_part را وارد کنید.",reply_markup=BH.show_buttons(update, context,"Course"))
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
    if part_number > BS.biggest_course_part_number + 1:
        await update.message.reply_text(f"خطا: شما نمی‌توانید قسمت {part_number} را اضافه کنید زیرا این قسمت بیشتر از ({BS.biggest_course_part_number+1}) است.")
        return

    BS.current_course_lot_code = lot_code
    BS.current_course_part_number = part_number
    BS.current_course_part_content = []
    BS.adding_course_part = True

    await update.message.reply_text(f"در حال افزودن محتوا برای قسمت دوره {part_number} هستیم. لطفاً محتوا را در پیام‌ها ارسال کنید. برای پایان دادن، /end_course_part را وارد کنید.",reply_markup=BH.show_buttons(update, context,"Course"))

async def end_course_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    if update.message.from_user.id != BS.ADMIN_USER_ID:
        await update.message.reply_text("شما مجاز به پایان دادن به قسمت دوره نیستید.")
        return

    if not BS.adding_course_part:
        await update.message.reply_text("هیچ قسمتی از دوره در حال افزودن نیست.",reply_markup=BH.show_buttons(update, context,"Course"))
        return

    # Create the course part data
    course_part = {
        "part_number": BS.current_course_part_number,
        "content": "\n".join(BS.current_course_part_content),
        "lot_code":BS.current_course_lot_code,
    }

    # Update or insert the course part in the database
    result = BS.courses_collection.update_one(
        {"part_number": BS.current_course_part_number},  # Search by part_number
        {"$set": course_part},  # Update the existing record or set new data
        upsert=True  # If no record exists, insert a new one
    )

    # Reset the flags
    BS.adding_course_part = False
    print_num = BS.current_course_part_number
    BS.current_course_part_number = None
    BS.current_course_part_content = []

    if result.matched_count > 0:
        await update.message.reply_text(f"قسمت دوره {print_num} با موفقیت به روز رسانی شد.",reply_markup=BH.show_buttons(update, context,"Normal"))
    else:
        await update.message.reply_text(f"قسمت دوره {print_num} با موفقیت اضافه شد.",reply_markup=BH.show_buttons(update, context,"Normal"))
        BS.biggest_course_part_number += 1

async def send_course_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not isinstance(update, int) and update.message.chat.type != 'private':
        return
    if isinstance(update, int):
        user_id = update
    else:
        user_id = update.message.from_user.id
        user = BS.users_collection.find_one({"_id" : user_id})
        if not user:
            return
        if user["Mode"] =="End":
            return
    logging.info(user_id)
    time_threshold = datetime.datetime.now() - datetime.timedelta(seconds=BS.Delete_Time_Second)
    # Fetch all course parts from the database
    user_Data = BS.users_collection.find_one(
        {"_id": user_id},
        )
    # If the user has received a 'course' message in the last 24 hours, deny the request
    if user_Data and user_Data["LastDownload"] > time_threshold.isoformat() and not isinstance(update, int):
        await update.message.reply_text("شما بخش‌های دوره را در ۲۴ ساعت گذشته دریافت کرده‌اید. لطفاً کمی صبر کنید و سپس دوباره درخواست کنید.",reply_markup=BH.show_buttons(update, context,"Course"))
        return

    user_data = BS.users_collection.find_one({"_id": user_id})
    course_part_number = user_data['course_part_number']
    logging.info(course_part_number)
    course_part = BS.courses_collection.find_one({"part_number": course_part_number})
    if not course_part and not isinstance(update, int):
        await update.message.reply_text("هیچ بخشی از دوره برای ارسال موجود نیست.",reply_markup=BH.show_buttons(update, context,"Normal"))
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
            if not isinstance(update, int):
                sent_message = await context.bot.copy_message(
                    chat_id=update.message.chat_id,
                    from_chat_id=user_id, 
                    message_id=message_id
                )
                if(course_part_number <3):
                    BS.messages_collection.insert_one({"user_id": update.message.chat_id, "message_id": sent_message.message_id, "message_type": "course", "timestamp": now})
            else:
                sent_message = await context.bot.copy_message(
                    chat_id=update,
                    from_chat_id=user_id, 
                    message_id=message_id
                )
        if not isinstance(update, int):
            BS.users_collection.update_one(
            {"_id": update.message.from_user.id},
            {"$inc": {"course_part_number": 1}}  # Increment the course_part_number by 1
            )
            BS.users_collection.update_one({"_id": update.message.from_user.id}, {"$set": {"LastDownload": now, "RemindCheck" : False}})
            await update.message.reply_text("منتظر تمرینت هستیما!❤️",reply_markup=BH.show_buttons(update, context,"Course"))
            user_id = update.message.from_user.id
            logging.info(f"Sent course part {course_part['part_number']} to user {user_id}")
        else:
            BS.users_collection.update_one(
            {"_id": update},
            {"$inc": {"course_part_number": 1}}  # Increment the course_part_number by 1
            )
            BS.users_collection.update_one({"_id": update}, {"$set": {"LastDownload": (datetime.datetime.now() + datetime.timedelta(days=365*10)).isoformat(), "RemindCheck" : False, "Mode" : "End" }})
            user_id = update
            await context.bot.send_message(
                chat_id=user_id,  # You need to specify the chat_id
                text="به پایان دوره رسیدیم !دوست عزیز مرسی که همراهمون بودی ❤️", 
                reply_markup=BH.show_buttons(update, context,"Course")  # Assuming no inline keyboard, so this can be omitted as well
                )
            logging.info(f"Sent course part {course_part['part_number']} to user {user_id}")
            
    except Exception as e:
        logging.error(f"Failed to send course part to {user_id}: {e}")
