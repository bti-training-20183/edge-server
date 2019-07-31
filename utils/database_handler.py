import io
import os
import sys
import config
from pymongo import MongoClient
sys.path.append(os.getcwd())


class DatabaseHandler:
    def __init__(self, mongo_url, mongo_db, mongo_collection):
        self.mongo_url = mongo_url
        self.client = MongoClient(mongo_url)
        print("Connected to Mongo")
        self.db = self.client[mongo_db]
        self.collection = self.db[mongo_collection]

    def insert(self, obj):
        return self.collection.insert_one(obj)

    def find_by_name(self, name):
        query = {"name": name}
        result = self.collection.find(query)
        if result.count():
            return result[0]
        else:
            return None

    def get_latest(self, model):
        return self.collection.find_one()

    def find_all(self):
        return self.collection.find()

    def update(self, query, new):
        return self.collection.update_one(query, new)

    def update_by_name(self, name, new):
        return self.update({"name": name}, new)

    def remove(self, query):
        return self.collection.delete_one(query)

    def remove_by_name(self, name):
        query = {"name": name}
        return self.collection.delete_one(query)

Database_Handler = DatabaseHandler(config.MONGO_URL,config.MONGO_DB, config.MONGO_COLLECTION)