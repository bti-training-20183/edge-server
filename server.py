import config
from utils.message_handler import MessageHandler
from utils.datastore_handler import Minio_Handler
from utils.datastore_handler import DataStoreHandler
from utils.database_handler import Database_Handler
from flask import Flask, request, flash, redirect, render_template
from flask_cors import CORS, cross_origin
from werkzeug.datastructures import ImmutableMultiDict
import os
import json
import sys
import pickle
import pandas as pd
import numpy as np
from keras.models import load_model
from keras import backend as K
import tensorflow as tf
from tensorflow import Graph
from tensorflow import Session
from crawl import do_job

sys.path.append(os.getcwd())
if not os.path.exists('tmp'):
    os.makedirs('tmp')
if not os.path.exists('tmp/data'):
    os.makedirs('tmp/data')

app = Flask(__name__)

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
CORS(app)
model_objects = {}
model_graphs = {}
model_session = {}
@app.route('/')
def hello():
    models_info= list(Database_Handler.find_all(config.MONGO_COLLECTION))
    models = (model['name'] for model in models_info)
    return render_template('home.html', models=models)


@app.route('/data', methods=["POST"])
def data():
    return 'data'


@app.route('/predict/<model_name>/<periods>/<data_name>', methods=["GET"])
def predict(model_name,data_name, periods):
    periods = int(periods)

    # Get Model by Model Name
    result = 0
    model_info = Database_Handler.find_by_name(config.MONGO_COLLECTION, model_name)

    if model_info is None:
        return json.dumps(result)
    
    model_name = model_info['name']
    stock_name = model_name.split('.')[0].upper()
    model_type = model_info['type']
    model_path = model_info['file_uri']
    files = model_info['files']
    to_path = 'tmp/' + model_name + '/'

    # Download models if necessary
    if not os.path.exists(to_path+files[0]):
        for file in files:
            Minio_Handler.download(model_path + file, to_path + file)

    # Get data for prediction, download if necessary
    data_to_path = 'tmp/data/' + stock_name + '/' + data_name + '.csv'
    data_folder = 'tmp/data' + stock_name
    print("Data to path:", data_to_path)
    if not os.path.exists(data_to_path):
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol":  stock_name,
            "apikey": config.API_KEY,
            "datatype": "csv"
        }
        do_job(params,stock_name,data_name)
        data_info = Database_Handler.find_by_name('edge-data',stock_name)
        data_name, data_path = data_info['name'], data_info['file_uri']       
        Minio_Handler.download(data_path, data_to_path)
        
    pred_data = pd.read_csv(data_to_path, header=None)

    # Predict
    if model_type == '.pkl':
        with open(to_path + 'model.pkl', 'rb') as pkl:
            result = pickle.load(pkl).predict(n_periods=periods)

    elif model_type == '.h5':   # Keras model
        # Load scaler
        with open(to_path + 'scaler.pkl', 'rb') as pkl:
            scaler = pickle.load(pkl)

        # Scale data
        pred_data_expanded = np.expand_dims(pred_data, 0)        # to fit with input shape of lstm model
        scaled_data = scaler.transform(pred_data_expanded.reshape(pred_data_expanded.shape[0]*pred_data_expanded.shape[1]
            , pred_data_expanded.shape[2]))
        scaled_data = scaled_data.reshape(pred_data_expanded.shape[0], pred_data_expanded.shape[1], pred_data_expanded.shape[2])
        
        # Load model
        if model_name not in model_objects:
            print("Load model from file")
            model_graphs[model_name] = Graph()
            with model_graphs[model_name].as_default():
                model_session[model_name] = Session()
                with model_session[model_name].as_default():
                    model = load_model(to_path + 'model.h5')
                    model._make_predict_function()	# have to initialize before threading
                    model_objects[model_name] = model
        else:
            print("Load model from memory")
            model = model_objects[model_name]
        # Predict 
        with model_graphs[model_name].as_default():
            with model_session[model_name].as_default():
                result = predict_keras(scaled_data, model, scaler, periods)
    else:
        # Load other model type - currently there is no other model type
        result = None

    print("\n\n\nPrediction done!\n\n\n")
    # K.clear_session()
    return json.dumps({"input": pred_data[-periods:][3].tolist(), "output": result.tolist()})

def predict_keras(scaled_data, model, scaler, n_periods):
    preds = model.predict(scaled_data)
    tmp = np.zeros(shape=(preds.shape[0]*preds.shape[1], scaled_data.shape[2]))
    tmp[:,3] = preds.reshape(preds.shape[0]*preds.shape[1])
    preds = scaler.inverse_transform(tmp)[:,3]

    return preds[:n_periods]


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
    
    if not os.path.exists('tmp/' + msg['name']):
        os.makedirs('tmp/' + msg['name'])
    # Upload to Minio
    dest = msg['name'] + '/model/'
    for filename in files:
        Minio_Handler.upload('tmp/'+filename, dest + filename)
        os.rename('tmp/'+filename, 'tmp/' + msg['name'] + '/' + filename)

    print("Save model to memory")
    model_graphs[msg['name']] = Graph()
    with model_graphs[msg['name']].as_default():
        model_session[msg['name']] = Session()
        with model_session[msg['name']].as_default():
            model = load_model( 'tmp/' + msg['name'] + '/' + 'model.h5')
            model._make_predict_function()	# have to initialize before threading
            model_objects[msg['name']] = model
    # K.clear_session()
    logs = {
        'name': msg['name'],
        'type': msg['type'],
        'file_uri': dest,
        'files': files
    }
    Database_Handler.update_by_name(config.MONGO_COLLECTION, msg['name'], logs)
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='8000')
