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

sys.path.append(os.getcwd())
if not os.path.exists('tmp'):
    os.makedirs('tmp')
if not os.path.exists('tmp/data'):
    os.makedirs('tmp/data')

app = Flask(__name__)

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
CORS(app)


@app.route('/')
def hello():
    models_info= list(Database_Handler.find_all(config.MONGO_COLLECTION))
    print(models_info)
    models = (model['name'] for model in models_info)
    print(models)
    return render_template('home.html', models=models)


@app.route('/data', methods=["POST"])
def data():
    return 'data'


@app.route('/predict/<model_name>/<data_name>', methods=["GET"])
def predict(model_name,data_name):
    print(model_name, data_name)
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
    print(to_path)

    # Download models if necessary
    if not os.path.exists(to_path+files[0]):
        for file in files:
            Minio_Handler.download(model_path + file, to_path + file)

    # Get data for prediction, download if necessary
    data_info = Database_Handler.find_by_name('edge-data',data_name+'.csv')
    data_name, data_path = data_info['name'], data_info['file_uri']
    data_to_path = 'tmp/data/' + data_name
    print(to_path)
    if not os.path.exists(data_to_path):
        for file in files:
            Minio_Handler.download(data_path, data_to_path)

    pred_data = pd.read_csv(data_to_path, header=None)

    # Predict
    if model_type == '.pkl':
        with open(to_path + 'model.pkl', 'rb') as pkl:
            result_one_day = pickle.load(pkl).predict(n_periods=1).tolist()
            result_five_days = pickle.load(pkl).predict(n_periods=5).tolist()
            result_one_month = pickle.load(pkl).predict(n_periods=30).tolist()
            result_six_months = pickle.load(pkl).predict(n_periods=180).tolist()
            result_one_year = pickle.load(pkl).predict(n_periods=365).tolist()

    elif model_type == '.h5':   # Keras model
        # Load scaler
        with open(to_path + 'scaler.pkl', 'rb') as pkl:
            scaler = pickle.load(pkl)

        # Scale data
        pred_data = np.expand_dims(pred_data, 0)        # to fit with input shape of lstm model
        scaled_data = scaler.transform(pred_data.reshape(pred_data.shape[0]*pred_data.shape[1], pred_data.shape[2]))
        scaled_data = scaled_data.reshape(pred_data.shape[0], pred_data.shape[1], pred_data.shape[2])

        # TODO: preprocess data if needed
        
        # Load model
        one_day_model = load_model(to_path + 'one_day_model.h5')
        five_days_model = load_model(to_path + 'five_days_model.h5')
        one_month_model = load_model(to_path + 'one_month_model.h5')
        six_months_model = load_model(to_path + 'six_months_model.h5')
        one_year_model = load_model(to_path + 'one_year_model.h5')

        # Predict 
        result_one_day = predict_keras(scaled_data, one_day_model, scaler)
        result_five_days = predict_keras(scaled_data, five_days_model, scaler)
        result_one_month = predict_keras(scaled_data, one_month_model, scaler)
        result_six_months = predict_keras(scaled_data, six_months_model, scaler)
        result_one_year = predict_keras(scaled_data, one_year_model, scaler)
    else:
        # Load other model type - currently there is no other model type
        result_one_day = None
        result_five_days = None
        result_one_month = None
        result_six_months = None
        result_one_year = None

    return json.dumps([result_one_day, result_five_days, result_one_month, 
                        result_six_months, result_one_year])

def predict_keras(scaled_data, model, scaler):
    preds = model.predict(scaled_data)
    tmp = np.zeros(shape=(preds.shape[0]*preds.shape[1], scaled_data.shape[2]))
    tmp[:,3] = preds.reshape(preds.shape[0]*preds.shape[1])
    preds = scaler.inverse_transform(tmp)[:,3]

    return preds.tolist()


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
