import config
from utils.message_handler import MessageHandler
from utils.datastore_handler import Minio_Handler
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
def udpate():
    print(request.data)
    return '???'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='8000')
