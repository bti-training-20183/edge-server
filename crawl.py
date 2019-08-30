from utils.database_handler import Database_Handler
from utils.datastore_handler import Minio_Handler
import csv
import time
import config
import requests
import os
import json
import sys
sys.path.append(os.getcwd())


def crawl_data(params, filename):
    response = requests.get(config.API_ENDPOINT, params=params)
    print('Crawling: ', response.url)
    empty_rows = 0
    with open(filename, 'w') as f:
        writer = csv.writer(f)
        for i, line in enumerate(response.iter_lines()):
            if i == (91+ empty_rows):
                break
            if i >= 1:
                if len(line) < 4:
                    empty_rows += 1
                else:
                    writer.writerow(line.decode('utf-8').split(',')[1:])


def save(stockname, filename):
    to_path = 'data/' + stockname + '/' + filename
    Minio_Handler.upload(filename, to_path)
    logs = {
        "name": stockname,
        "file_uri": to_path
    }
    os.remove(filename)
    Database_Handler.insert('edge-data', logs)


def do_job(params, stockname, filename):
    crawl_data(params, filename)
    save(stockname, filename)
