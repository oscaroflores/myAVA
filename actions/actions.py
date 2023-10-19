from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import datetime
import pickle
from dateutil.parser import *

CLIENT_FILE = 'credz.json'
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/tasks']

class ActionGoogleConnect(Action):

    def name(self) -> Text:
        return "action_google_connect"

# Connect to my google account
creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

# Google API Services:
tasks_service = build('tasks', 'v1', credentials=creds)
gmail_service = build('gmail', 'v1', credentials=creds)
calendar_service = build('calendar', 'v3', credentials=creds)

class ActionAddTask(Action):

    def name(self) -> Text:
        return "action_add_task"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get task list where task will be added
        task_lists = tasks_service.tasklists().list().execute()['items']
        my_tasks_id = None
        for x in task_lists:
            if x['title'] == 'My Tasks':
                my_tasks_id = x['id']
        my_tasks = tasks_service.tasklists().get(tasklist=my_tasks_id).execute()

        # Insert new task to the list
        task = tracker.get_slot("task")
        self.add_task(my_tasks_id, task)
        dispatcher.utter_message(text=f"Added {task} to {my_tasks['title']}")

        return []
    
    def add_task(self, task_list_id, task):
        tasks_service.tasks().insert(tasklist=task_list_id, body={
            "title":task
        }).execute()


class ActionReadEmails(Action): 

    def name(self) -> Text:
        return "action_read_emails"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        service = gmail_service
        labels = service.users().labels().get(userId='me', id='INBOX').execute()

        if labels["messagesUnread"] != 0:
            results = service.users().messages().list(userId="me", labelIds=["INBOX", "UNREAD"]).execute()
            for x in results["messages"]:
                service.users().messages().modify(userId='me', id=x["id"], body={ 'removeLabelIds': ['UNREAD']}).execute()
            dispatcher.utter_message(text="I have marked your unread emails as 'read'")
        else:
            dispatcher.utter_message(text="You have no mail at the moment.")

        return []
    
class ActionGetEmails(Action):

    def name(self) -> Text:
        return "action_get_emails"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        service = gmail_service
        labels = service.users().labels().get(userId='me', id='INBOX').execute()
        
        if labels["messagesUnread"] != 0:
            unread_messages = []
            results = service.users().messages().list(userId="me", labelIds=["INBOX", "UNREAD"]).execute()

            for m in results['messages']:
                message = service.users().messages().get(userId='me', id=m['id']).execute()
                payload = message['payload']
                headers = payload['headers']

                date = ""
                for x in headers:
                    if x['name'] == 'Date':
                        date_parse = parse(x['value'])
                        date = date_parse.date()
                    else:
                        pass

                sender = ""
                for x in headers:
                    if x['name'] == 'From':
                        sender = x['value'].split(" <")[0]
                    else:
                        pass

                subject = ""
                for x in headers:
                    if x['name'] == 'Subject':
                        subject = x['value']
                    else:
                        pass

                unread_messages.append(
                    {
                        "date" : date,
                        "sender" : sender,
                        "subject" : subject
                    }
                )

            for x in unread_messages:
                    dispatcher.utter_message(text=f"{x['date']} || {x['sender']} || {x['subject']}")
                    dispatcher.utter_message(text=" ")
        else:
            dispatcher.utter_message(text="You have no mail at the moment.")

        return []

class ActionAddEvent(Action):

    def name(self) -> Text:
        return "action_add_event"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            event = tracker.get_slot("event")
            name = event.split(',')[0]
            date = self.format_event(event)
            self.add_event(date, name)
            dispatcher.utter_message(text=f"Added event {name} at {date}")
        except Exception as e:
            dispatcher.utter_message(text=f"<<ERROR>> {str(e)}")
        return[]

    def add_event(self, time, event):
        service = calendar_service

        start = time
        end = start + datetime.timedelta(hours=1)

        event = service.events().insert(calendarId='primary',
            body={
                "summary": event,
                "description": 'This is a tutorial example of automating google calendar with python',
                "start": {
                    "dateTime": start.isoformat(),
                    "timeZone": 'America/Puerto_Rico'
                    },
                "end": {
                    "dateTime": end.isoformat(),
                    "timeZone": 'America/Puerto_Rico'
                    },
            }
        ).execute()
    
    def format_event(self, event):
        substring = event.split(',')
        if (len(substring) < 3):
            return
        
        # Format date
        if len(substring[1]) < 10:
            temp = substring[1].split('/')
            if len(temp[0]) == 1:
                temp[0] = temp[0].zfill(2)
            if len(temp[1]) == 1:
                temp[1] = temp[1].zfill(2) 
        
        date = datetime.datetime.strptime(substring[1] + " " + substring[2] + ":00", "%m/%d/%Y %H:%M:%S")
        return date


class ActionHelloWorld(Action):

    def name(self) -> Text:
        return "action_hello_world"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World!")

        return []
