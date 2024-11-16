from telegram import KeyboardButton, ReplyKeyboardMarkup
import BotSettings as BS
import BroadCast as BC
import Courses as CS
import ReviewAndLottery as RAL

def show_buttons(update, context, mode):
    if isinstance(update, int):
        user_id = update
    elif update != "GZ":
        user_id = update.effective_user.id
    else:
        user_id = context
    keyboard = []

    if (BS.ADMIN_USER_ID == user_id):
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
                [KeyboardButton("بزن بریم❤️‍🔥")]
            ]
        elif(mode == "Course"):
            if(RAL.lot_code_cheack(user_id)=="None" or RAL.lot_code_cheack(user_id)=="Auto"):
                keyboard = [
                    [KeyboardButton("ارسال تکالیف و نظرات")],
                ]
            else:
                keyboard = [
                    [KeyboardButton("ارسال تکالیف و نظرات")],
                    [KeyboardButton("ارسال کد قرعه کشی")]
                ]
        elif(mode == "Review"):
            keyboard = [
                [KeyboardButton("پایان ارسال")]
            ]
        elif(mode == "Code"):
            keyboard = [
                [KeyboardButton("لغو ارسال")]
            ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)#, one_time_keyboard=True)
    return reply_markup

async def button_callback(update, context,data):
    if data == "شروع بازپخش":
        await BC.start_broadcast(update, context, True)
    elif data == "شروع باز پخش بدون پاک شدن":
        await BC.start_broadcast(update, context, False)
    elif data == "پایان بازپخش":
        await BC.stop_broadcast(update, context)
    elif data == "اضافه کردن دوره":
        await CS.add_course_part(update, context)
    elif data == "پایان دوره":
        await CS.end_course_part(update, context)
    elif data == "بزن بریم❤️‍🔥":
        await CS.send_course_parts(update, context)
    elif data == "ارسال تکالیف و نظرات":
        await RAL.send_review_lotcode(update,context,"Review")
    elif data == "ارسال کد قرعه کشی":
        await RAL.send_review_lotcode(update,context,"Code")
    elif data == "پایان ارسال" or data == "لغو ارسال":
        await RAL.send_review_lotcode(update,context,"Course")
    else:
        return False
    return True