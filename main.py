import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from abc import ABC, abstractmethod

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Ühe eventi puhul:
#   Kui pole kellaaegasid, igno
#   Kui pole lõppkellaaega, igno (või allokeeri mingi tund vms??)
#   Jaluta läbi filtrid, esimene, mis matchib, läheb käiku. Spetsiifilisemad asjad peaks siis enne olema.
#       Nt kõigepealt, et kas on mingi ainekood sees, muu sõne pealkirjas (üldistatav veidi)
#       Siis, et mis kalendrisse kuulub, map kalendri ID ja toggl project ID vahel.


class Filter(ABC):
    """ A toggl-specific filter. Converts specific events into time entries."""
    @abstractmethod
    def match(self, event) -> bool:
        return

    @abstractmethod
    def upload(self, event) -> bool:
        return


class ProjectFilter(Filter):
    def __init__(self, project_dict) -> None:
        super().__init__()
        self.project_dict = project_dict


    def match(self, event) -> bool:
        if self.project_dict[event["calendar"]["id"]] is not None:
            return True

    def upload(self, event) -> bool:
        return False


class SortingHat:
    def __init__(self) -> None:
        self.filters = []


    def sort_event(self, event):
        for filter in self.filters:
            if filter.match(event):
                filter.upload(event)
                break


def get_creds():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def get_calendars(service, blacklist=[]):
    calendars = []
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            print(calendar_list_entry["id"])
            if calendar_list_entry["id"] not in blacklist:
                calendars.append(calendar_list_entry)
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    return calendars


def main():
    blacklist = ["13lt9o68crpjggp36kv84qbn40@group.calendar.google.com"]

    creds = get_creds()
    service = build('calendar', 'v3', credentials=creds)
    calendars = get_calendars(service, blacklist=blacklist)

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    yesterday = yesterday.isoformat() + 'Z'

    print('Get all events in the past 24 hours')
    for calendar in calendars:
        events_result = service.events().list(calendarId=calendar["id"], timeMin=yesterday, timeMax=now,
                                                singleEvents=True,
                                                orderBy='startTime').execute()
        events = events_result.get('items', [])

        # Prints the start and name of the next 10 events
        for event in events:
            event["calendar"] = calendar
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(event)
            print(start, event['summary'])


if __name__ == '__main__':
    main()
