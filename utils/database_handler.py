import io
import os
import sys
import config
from pymongo import MongoClient
sys.path.append(os.getcwd())


class DatabaseHandler:
    def __init__(self, mongo_url, mongo_db):
        self.mongo_url = mongo_url
        self.client = MongoClient(mongo_url)
        print("Connected to Mongo")
        self.db = self.client[mongo_db]

    def insert(self, collection, obj):
        return self.db[collection].insert_one(obj)

    def find_in_collection(self, collection, query):
        return self.db[collection].find_one(query)

    def find_by_name(self, collection, name):
        query = {"name": name}
        result = self.db[collection].find(query)
        if result.count():
            return result[0]
        else:
            return None

    def get_latest(self, collection, model):
        return self.db[collection].find_one()

    def find_all(self, collection):
        return self.db[collection].find()

    def update(self, collection, query, new):
        return self.db[collection].update_one(query, new)

    def update_by_name(self, collection, name, new):
        return self.update(collection, {"name": name}, new)

    def remove(self, collection, query):
        return self.db[collection].delete_one(query)

    def remove_by_name(self, collection, name):
        query = {"name": name}
        return self.db[collection].delete_one(query)

Database_Handler = DatabaseHandler(config.MONGO_URL,config.MONGO_DB)