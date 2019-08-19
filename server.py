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
import pickle
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


@app.route('/predict/<model_name>', methods=["GET"])
def predict(model_name):
    # Get Model by Model Name
    result = 0
    model_info = Database_Handler.find_by_name(config.MONGO_COLLECTION, model_name)
    if model_info is None:
        return json.dumps(result)
    
    model_name = model_info['name']
    model_type = model_info['type']
    model_path = model_info['file_uri']
    files = model_info['files']
    to_path = 'tmp/' + model_name + '/'
    for file in files:
        Minio_Handler.download(model_path + file, to_path + file)

    # Predict
    if model_type == '.pkl':
        with open(to_path + 'model.pkl', 'rb') as pkl:
            result = pickle.load(pkl).predict(n_periods=1).tolist()[0]
    elif model_type == '.h5':
        # TODO load model and necessary files in 'tmp/' + model_name folder and predict
        result = 2 # fake result
    else:
        # Load other model type
        result = 3 # fake result
    return json.dumps(result)


@app.route('/update', methods=["POST"])
def update():
    print(f'Received {request.data}')
    msg = json.loads(request.data)
    from_path = msg['file_uri']
   
    # Download from S3
    S3_Handler = DataStoreHandler(config.S3_ENDPOINT, 
        msg['S3_ACCESS_KEY'], 
        msg['S3_SECRET_KEY'], 
        msg['S3_BUCKET'])
    files = msg['files']
    for file in files:
        S3_Handler.download(from_path + file, 'tmp/' + file)
    
    # Upload to Minio
    dest = msg['name'] + '/model/'
    for filename in files:
        Minio_Handler.upload('tmp/'+filename, dest + filename)
        os.remove('tmp/'+filename)


    logs = {
        'name': msg['name'],
        'type': msg['type'],
        'file_uri': dest,
        'files': files
    }
    if Database_Handler.find_by_name(config.MONGO_COLLECTION, msg['name']):
        Database_Handler.update_by_name(config.MONGO_COLLECTION, msg['name'], logs)
    else:
        Database_Handler.insert(config.MONGO_COLLECTION, logs)
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='8000')
