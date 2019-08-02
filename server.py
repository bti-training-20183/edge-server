import config
from utils.message_handler import MessageHandler
from utils.datastore_handler import Minio_Handler
from utils.datastore_handler import DataStoreHandler
from utils.database_handler import Database_Handler
from flask import Flask, request, flash, redirect
from flask_cors import CORS, cross_origin
from werkzeug.datastructures import ImmutableMultiDict
import os
import json
import sys
sys.path.append(os.getcwd())
if not os.path.exists('tmp'):
    os.makedirs('tmp')
app = Flask(__name__)

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
CORS(app)


@app.route('/')
def hello():
    return 'Hello, World!'


@app.route('/data', methods=["POST"])
def data():
    return 'data'


@app.route('/predict/<model_name>', methods=["POST"])
def predict(model_name):
    # Get Model by Model Name
    # Predict
    return 'result'


@app.route('/update', methods=["POST"])
def update():
    print(f'Received {request.data}')
    msg = json.loads(request.data)
    from_path = msg['file_uri']
    to_path = 'tmp/' + msg['name'] + msg['type']
    
    # Download from S3
    S3_Handler = DataStoreHandler(config.S3_ENDPOINT, 
        msg['S3_ACCESS_KEY'], 
        msg['S3_SECRET_KEY'], 
        msg['S3_BUCKET'])
    S3_Handler.download(from_path, to_path)
    
    # Upload to Minio
    from_path, to_path = to_path, from_path
    Minio_Handler.upload(from_path,to_path)
    os.remove(from_path)
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='8000')
