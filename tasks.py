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
from celery.schedules import crontab
from time import sleep
from datetime import  date, datetime, timedelta
import datetime

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

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

flask_app = Flask(__name__)
flask_app.config.update(
    CELERY_BROKER_URL=cloud_amqp_url
)
celery = make_celery(flask_app)

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
    our_response = "Hey!\n You NEED to complete the below tasks if you want to have a proper night's sleep. \n"
    try:
        all_todos = [doc.to_dict() for doc in todo_ref.stream()]
        incomplete_task_titles = []
        for task in all_todos:
            if task['status'] != 'Completed':
                deadline_parsed = datetime.datetime.strptime(task['deadline'], "%Y-%m-%dT%H:%M:%S.%fZ")
                task_year = deadline_parsed.year
                task_month = deadline_parsed.month
                task_day = deadline_parsed.day
                now = datetime.datetime.now()
                if(task_month == now.month and task_day == now.day and task_year == now.year):
                    incomplete_task_titles.append(task['title'])
        for task_index in range(len(incomplete_task_titles)):
            our_response += str(task_index + 1) + '. ' + incomplete_task_titles[task_index] + '\n'
        return our_response
    except Exception as e:
        return f"An Error Occured: {e}"
    
# This will one ONCE in the future.
@celery.task()
def check():
    tasks = get_tasks_for_today()
    print('Tasks ', tasks)
    now = datetime.now()
    message = client.messages.create(
         body=tasks,
         from_=from_number,
         to=to_number
    )
    return "check completed"

with flask_app.app_context():
    celery.conf.beat_schedule = {
            "run-me-every-thirty-seconds": {
            "task": "tasks.check",
            "schedule": 30.0
         }
    }

# to start:
# heroku ps:scale worker=1
# heroku ps:scale beat=1

# to stop:
# heroku ps:scale worker=0
# heroku ps:scale beat=0