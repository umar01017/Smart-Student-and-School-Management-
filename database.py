from pymongo import MongoClient
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client[Config.MONGO_DBNAME]

# Export collections for easy access
users_collection = db.users
students_collection = db.students
teachers_collection = db.teachers
attendance_collection = db.attendance
announcements_collection = db.announcements
fees_collection = db.fees
settings_collection = db.settings
salaries_collection = db.salaries
expenses_collection = db.expenses
infrastructure_collection = db.infrastructure
library_collection = db.library
