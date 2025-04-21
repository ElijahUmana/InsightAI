import motor.motor_asyncio
from config import MONGODB_URL, DB_NAME

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
database = client[DB_NAME]

def get_database():
    return database
