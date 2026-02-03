import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
MY_USER_ID = int(os.getenv('MY_USER_ID'))
GIRLFRIEND_USER_ID = int(os.getenv('GIRLFRIEND_USER_ID'))
DB_PATH = 'finance_planner.db'