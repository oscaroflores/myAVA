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
import pytz
import pickle

CLIENT_FILE = 'creds.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

class ActionAddEvent(Action):

    def name(self) -> Text:
        return "action_add_event"

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

    def fetch(self):
        service = self.get_calendar_service()

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                                maxResults=10, singleEvents=True,
                                                orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events')
            return
        
        # Prints start and name of next 10 events
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

    def add_event(self, time, event):
        # creates one hour event tomorrow 10 AM IST
        service = self.get_calendar_service()

        # start = datetime.datetime.now(pytz.timezone('Etc/GMT-4'))
        start = datetime.datetime.strptime(time)
        end = start + datetime.timedelta(hours=1)

        event = service.events().insert(calendarId='primary',
            body={
                "summary": event,
                "description": 'This is a tutorial example of automating google calendar with python',
                "start": {
                    "dateTime": start.isoformat(), 
                    "timeZone": 'Etc/GMT-4'
                    },
                "end": {
                    "dateTime": end.isoformat(), 
                    "timeZone": 'Etc/GMT-4'
                    },
            }
        ).execute()
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        try:
            event = tracker.get_slot("event")
            # self.add_event(time, event)

            if not event:
                dispatcher.utter_message(text=f"Event given is wrong: {event}")
            else:
                dispatcher.utter_message(text=f"Added event {event}")
        except Exception as e:
            dispatcher.utter_message(text=f"<<ERROR>> {str(e)}")
        
        return[]

class ActionHelloWorld(Action):

    def name(self) -> Text:
        return "action_hello_world"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World!")

        return []
