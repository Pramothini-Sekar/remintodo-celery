## Flask and Twilio includes and setup
import os
import time
import json
from flask_cors import CORS
import firebase_admin
from flask import Flask, request, jsonify, redirect, session, render_template
from firebase_admin import credentials, firestore, initialize_app
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from celery import Celery
from time import sleep
from datetime import datetime, timedelta

#### ADD YOUR CELERY BROKER HERE
# I enabled the Heroku add-on called cloudAMQP to use rabbitMQ as my broker
# Go to your heroku project Dashboard to find add ons.
# enable cloudAMPQ, then click on the info link to get the URL and paste it here.

from_number = '+15739733743' # put your twilio number here'
to_number = '+16467326671' # put your own phone number here

api_key = os.environ['API_KEY']
api_secret = os.environ['API_SECRET']
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
client = Client(account_sid, auth_token)

cloud_amqp_url = os.environ['CELERY_BROKER_URL']
app = Celery('tasks', broker=cloud_amqp_url)
app.config['CELERY_BROKER_URL'] = cloud_amqp_url
app.secret_key = api_secret

# Initialize Firestore DB
if not firebase_admin._apps:
    cred = credentials.Certificate('google-credentials.json')
    default_app = initialize_app(cred)
db = firestore.client()
todo_ref = db.collection('todos')

def get_tasks_for_today():
    """
        read() : Fetches documents from Firestore collection as JSON.
        todo : Return document that matches query ID.
        all_todos : Return all documents.
    """
    try:
        # Check if ID was passed to URL query
        todo_id = request.args.get('id')
        if todo_id:
            todo = todo_ref.document(todo_id).get()
            return jsonify(todo.to_dict())
        else:
            all_todos = [doc.to_dict() for doc in todo_ref.stream()]
            return jsonify(all_todos)
    except Exception as e:
        return f"An Error Occured: {e}"
    
# This will one ONCE in the future.
@app.task()
def hello():
    tasks = get_tasks_for_today()
    message = client.messages.create(
         body=str(jsonify(tasks)),
         from_=from_number,
         to=to_number
     )
    return 'hello world'

in_a_minute = datetime.utcnow() + timedelta(minutes=1)
hello.apply_async(eta=in_a_minute)

# to start:
# heroku ps:scale worker=1
# heroku ps:scale beat=1

# to stop:
# heroku ps:scale worker=0
# heroku ps:scale beat=0