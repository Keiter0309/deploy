from flask import Flask, render_template, redirect, session
from zipfile import BadZipFile
from datetime import datetime
from flask import request, jsonify
from pymongo import MongoClient
import pandas as pd
from werkzeug.security import check_password_hash
import os

auth = Flask(__name__)
auth.secret_key =  'mysecretkey'
mongo_client = MongoClient('localhost', 27017)
db = mongo_client['flask-database']

@auth.route('/')
def hello_world():
    return render_template('Login.html')

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
    all_sheets = db['sheets'].find()
    sheet_names = []
    sheet_name = request.args.get('sheet_name')
    sheet_content = db['sheets'].find_one({'sheet_name': sheet_name})
    if not dashboard:
        return jsonify({'error': 'Sheet not found'}), 404

    for sheet in all_sheets:
        sheet_names.append(sheet['sheet_name'])

    return render_template('dashboard.html', sheets=sheet_names, sheet=sheet_content)


@auth.route('/import-data', methods=['POST'])
def import_data():
    # Get data from request
    group = request.form.get('group')
    file = request.files.get('file')
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not group or not file:
        return jsonify({'error': 'No data provided'}), 400

    # Create uploads directory if it doesn't exist
    uploads_dir = 'uploads'
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    # Save file to disk
    file_path = os.path.join(uploads_dir, file.filename)
    file.save(file_path)

    # Insert data into database
    db['data'].insert_one({'group': group, 'file': file.filename, 'username': session['username'], 'created_at': time})

    # Load spreadsheet
    try:
        df = pd.ExcelFile(file_path)
        sheet_names = df.sheet_names

        # Parse each sheet individually and store content
        for sheet_name in sheet_names:
            sheet_content = df.parse(sheet_name)
            # Replace NaT and NaN values with None
            sheet_content = sheet_content.replace({pd.NaT: None, pd.NA: None})
            # Create a dictionary with sheet name as key and sheet content as value
            sheet_data = {'sheet_name': sheet_name, 'content': sheet_content.to_dict('records')}
            # Insert the dictionary into the database
            db['sheets'].insert_one(sheet_data)
    except EOFError:
        return jsonify({'error': 'File is not completely uploaded or is corrupted'}), 400
    except BadZipFile:
        return jsonify({'error': 'The Excel file is corrupted'}), 400

    return jsonify({'message': 'File processed successfully'}), 200

@auth.route('/dashboard', methods=['GET'])
def sheet():
    sheet_name = request.args.get('sheet_name')
    sheet_content = db['sheets'].find_one({'sheet_name': sheet_name})
    if not sheet:
        return jsonify({'error': 'Sheet not found'}), 404

    return render_template('dashboard.html', sheet=sheet_content)

if __name__ == '__main__':
    auth.run()