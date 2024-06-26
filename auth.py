from flask import Flask, render_template, redirect, session
from datetime import datetime
from flask import request, jsonify
from pymongo import MongoClient
from werkzeug.security import check_password_hash
import os

auth = Flask(__name__)
auth.secret_key =  'mysecretkey'
mongo_client = MongoClient('localhost', 27017)
db = mongo_client['flask-database']

@auth.route('/')
def hello_world():
    return render_template('index.html')

@auth.route('/', methods=['POST'])
def login():
    # Get data from request
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Extract username and password from request
    username = data.get('username')
    password = data.get('password')

    # Check if both username and password are provided
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    # Find user in the database
    user = db['users'].find_one({'username': username})

    # Check if user exists and password matches
    if user and check_password_hash(user['password'], password):
        session['username'] = username  # Save username to session
        return redirect('/dashboard', code=302)
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

@auth.route('/dashboard', methods=['GET'])
def dashboard():
    all_user = db['users'].find()
    users = []
    for user in all_user:
        users.append(user['username'])
    return render_template('dashboard.html', users=users)

@auth.route('/import-data', methods=['POST'])
def import_data():
    # Get data from request
    group = request.form.get('group')
    file = request.files.get('file')
    time = datetime.now().strptime('%Y-%m-%d %H:%M:%S')

    if not group or not file:
        return jsonify({'error': 'No data provided'}), 400

    # Create uploads directory if it doesn't exist
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    # Process file
    # Save file to disk
    file.save(os.path.join('uploads', file.filename))

    # Process file
    # Insert data into database
    db['data'].insert_one({'group': group, 'file': file.filename, 'username': session['username'], 'created_at': time})

    # Open file and process data
    with open(os.path.join('uploads', file.filename)) as f:
        data = f.readlines()
        for line in data:
            print(line)

    return jsonify({'message': 'File processed successfully'}), 200

if __name__ == '__main__':
    auth.run()