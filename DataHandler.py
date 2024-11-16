# Contact handler
import datetime
import logging
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes
import BotSettings as BS
import ButtonHandler as BH
from telegram.constants import ParseMode


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        # Ignore the message if it is from a group
        return
    contact = update.message.contact
    name = update.message.from_user.full_name
    user_id = update.message.from_user.id

    if BS.users_collection.find_one({"_id": user_id, "contact": {"$exists": True}}):
        await update.message.reply_text("خوش آمدید! شما قبلاً اطلاعات تماس خود را به اشتراک گذاشته‌اید.")
        return
    LastDownload = (datetime.datetime.now() - datetime.timedelta(seconds=BS.Delete_Time_Second)).isoformat()
    BS.users_collection.update_one(
        {"_id": user_id},
        {"$set": {"Telegram_name": name, "contact": contact.phone_number, "awaiting_name": True, "course_part_number": 1, "LastDownload" : LastDownload, "RemindCheck" : True, "Mode" : "Normal"}},
        upsert=True
    )

    await update.message.reply_text(f"لطفاً اسم و فامیلیتم برامون بنویس و ارسالش کن😍", reply_markup=ReplyKeyboardRemove())

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    name = update.message.text
    # Check for MongoDB injection patterns
    
    user_id = update.message.from_user.id
    user = BS.users_collection.find_one({"_id": user_id})

    if user and user.get("awaiting_name"):
        if BS.injection_pattern.search(name):
            await update.message.reply_text("نام شما شامل کاراکترهای غیرمجاز است. لطفاً یک نام معتبر وارد کنید.")
            return
        if len(name) > BS.MAX_NAME_LENGTH:
            await update.message.reply_text(f"نام شما خیلی طولانی است. لطفاً آن را زیر {BS.MAX_NAME_LENGTH} کاراکتر نگه دارید.")
            return
        else:
            BS.users_collection.update_one({"_id": user_id}, {"$set": {"name": name, "awaiting_name": False}})
            await update.message.reply_text(f"{name} عزیز شما با موفقیت عضو خانواده بزرگ کوییزلت شدین🥳🥰💛\nقبل از اینکه این چالشو شروع کنیم حتماً به ویس میثاق و تینا گوش بدین تا کامل دستورالعمل این دوره رو متوجه بشین👇",reply_markup=BH.show_buttons(update, context,"Normal"))
            # Send a voice message first
            with open(BS.voice_file_path, 'rb') as voice_file:
                await context.bot.send_voice(
                    chat_id=update.effective_chat.id,
                    voice=voice_file,
                    caption="🎙️ گوش بده و شروع کن!",
                    parse_mode=ParseMode.HTML
                )
            await update.message.reply_text("برای شروع چالش ۳کلید 🔑 بروی کلید زیر بزنید و متعهدانه آموزش هارو شروع کنید❤️",reply_markup=BH.show_buttons(update, context,"Normal"))
    elif await BH.button_callback(update, context,name):
        pass
    else:
        await broadcast_content(update, context)

async def broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        # Ignore the message if it is from a group
        return
    if BS.broadcast_mode and update.message.from_user.id == BS.ADMIN_USER_ID:
        if BS.broadcast_Type == "multiple":
            user_ids = BS.users_collection.distinct("_id")
        else:
            user_ids = [BS.broadcast_User_ID]
        timestamp = datetime.datetime.now().isoformat()

        for user_id in user_ids:
            try:
                sent_message = await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                if(BS.broadcast_delete_mode):
                    BS.messages_collection.insert_one({"user_id": user_id, "message_id": sent_message.message_id, "message_type": "broadcast", "timestamp": timestamp})
            except Exception as e:
                logging.error(f"Failed to send message to {user_id}: {e}")
    else:
        await course_content_handler(update, context)

async def course_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    if BS.adding_course_part and user_id == BS.ADMIN_USER_ID:
        BS.current_course_part_content.append(str({"user_id": user_id, "message_id": message_id}))
        await update.message.reply_text("محتوا اضافه شد. برای ادامه افزودن، ادامه دهید یا برای پایان دادن /end_course_part را تایپ کنید.")
    else:
        await user_data_handler(update, context)

async def user_data_handler (update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    par_user = BS.users_collection.find_one({"_id":user_id, "Mode": "Review"})
    end_user = BS.users_collection.find_one({"_id":user_id, "Mode": "End"})
    code_user = BS.users_collection.find_one({"_id":user_id, "Mode": "Code"})
    if user_id != BS.ADMIN_USER_ID:
        if par_user or end_user:
            await context.bot.send_message(
                chat_id=BS.SAVE_GP_ID,
                text=user_id
            )
            await context.bot.forward_message(
                    chat_id=BS.SAVE_GP_ID,
                    from_chat_id=user_id, 
                    message_id=message_id
                )
            await update.message.reply_text("نظر شما با موفقیت ثبت شد.🥳❤️ می‌توانید با استفاده از دکمه 'پایان ارسال' را به پایان برسانید یا ادامه دهید.")
        elif code_user:
            part_number =code_user["course_part_number"]-1
            code_course = BS.courses_collection.find_one({"part_number":part_number})
            try:
                if update.message.text and code_course and update.message.text.strip() == code_course["lot_code"]:
                    try:
                        if BS.lottery_collection.find_one({"user_id": user_id, "course_part" : part_number}):
                            await update.message.reply_text("شما قبلاً در قرعه‌کشی این بخش دوره ثبت‌نام کرده‌اید.")
                            return
                    except:
                        pass
                    BS.lottery_collection.update_one({"course_part" : part_number, "user_id": user_id},
                        {"$set":{"timestamp": datetime.datetime.now().isoformat()}},
                        upsert=True
                    )
                    await update.message.reply_text("تبریک! کد قرعه‌کشی شما تایید شد و با موفقیت در قرعه‌کشی ثبت‌نام شدید.")
                else:
                    await update.message.reply_text("متاسفیم! کد قرعه‌کشی وارد شده نامعتبر است. لطفاً دوباره تلاش کنید.")
            except Exception as e:
                logging.error(f"Error inserting into lottery collection: {e}")
                await update.message.reply_text("متاسفیم! مشکلی پیش آمده است. لطفاً دوباره تلاش کنید.")
