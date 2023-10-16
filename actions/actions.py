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
import base64
import email

CLIENT_FILE = 'credz.json'
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://mail.google.com/']

class ActionGetEmails(Action):

    def name(self) -> Text:
        return "action_get_emails"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            service = self.get_mail_service()
            results = service.users().messages().list(userId="me", labelIds=["INBOX", "IMPORTANT", "CATEGORY_PERSONAL"], maxResults=3).execute()
            
            latest_id = results["messages"][0]["id"]
            latest_message = service.users().messages().get(userId='me', id=latest_id).execute()
            
            payload = latest_message['payload']
            headers = payload['headers']

            sender = ""
            for x in headers:
                if x['name'] == 'From':
                    sender = x['value']

            subject = ""
            for x in headers:
                if x['name'] == 'Subject':
                    subject = x['value']

            # ids = []
            # for i in results["messages"]:
            #     ids.append(results["messages"][i]["id"])

            dispatcher.utter_message(text=f"From {sender} || {subject}")
            dispatcher.utter_message(text="")
        except Exception as e:
            dispatcher.utter_message(text=f"<<ERROR>> {str(e)}")
        return []

    def get_mail_service(self):
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
        try:
            service = build('gmail', 'v1', credentials=creds)
            return service
        except Exception as e:
            return e

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
    
    def get_calendar_service(self):
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

        service = build('calendar', 'v3', credentials=creds)
        return service

    def add_event(self, time, event):
        service = self.get_calendar_service()

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
