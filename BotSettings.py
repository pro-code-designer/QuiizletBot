import os
import re
import logging
from pymongo import MongoClient


# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://GdfhOIHJhihhger:nadlfj72bnksajd94@mongo:27017/")
#MONGO_URI = os.getenv("MONGO_URI", "mongodb://GdfhOIHJhihhger:nasdklfjbnksdjf@mongo:27017/")
  # Replace with your MongoDB URI
client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]  # Database name
users_collection = db["users"]
messages_collection = db["messages"]
courses_collection = db["courses"]  # New collection for storing course parts
lottery_collection = db["lottery_database"] 

# Replace with your admin user ID
#ADMIN_USER_ID =  5766796317
ADMIN_USER_ID =  281349921
#SAVE_GP_ID = -1002250211802
SAVE_GP_ID = -1002252999665
#Bot_Token = "7549275813:AAETAkZlM8PU7h6RZ6hnpxJTycq6iFjX4yE"
Bot_Token = "7393447211:AAFPRoa203ot_z9uqaVdvBu6L1K-mFxslSw"
Check_Time_Second = 30
Delete_Time_Second = 30
injection_pattern = re.compile(r"[\$\\{}\[\]\(\)]|\"|\b(eval|function)\b", re.IGNORECASE)
MAX_NAME_LENGTH = 30
voice_file_path = "welcome_voice.ogg"  # Replace with your file path

# Initialize broadcast mode and course part flag
broadcast_mode = False
broadcast_Type = "multiple" # or "single"
broadcast_User_ID = 0
broadcast_delete_mode = False
adding_course_part = False
current_course_part_number = None
biggest_course_part_number = 0
current_course_part_content = []
current_course_lot_code="testlot"
