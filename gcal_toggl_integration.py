import logging
import re
import yaml
import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

from toggl_interface import TogglInterface

class GcalInterface():

    def __init__(self, credentials_path="credentials.json", token_path="token.json", blacklist=[]) -> None:
        # Get google calendar token
        creds = self.get_creds(token_path=token_path, credentials_path=credentials_path)
        self.service = build('calendar', 'v3', credentials=creds)
        self.blacklist=blacklist
        self.calendars = self.get_calendars()


    def get_creds(self, token_path="token.json", credentials_path="credentials.json"):
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        return creds


    def get_calendars(self):
        calendars = []
        page_token = None
        while True:
            calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
            for calendar_list_entry in calendar_list['items']:
                logging.debug(calendar_list_entry["id"])
                if calendar_list_entry["id"] not in self.blacklist:
                    calendars.append(calendar_list_entry)
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break
        return calendars


    def get_events(self, start_time, end_time):
        event_list = []
        for calendar in self.calendars:
            events_result = self.service.events().list(calendarId=calendar["id"], timeMin=start_time, timeMax=end_time,
                                                    singleEvents=True,
                                                    orderBy='startTime').execute()
            events = events_result.get('items', [])
            for event in events:
                event["calendar"] = calendar["id"]
                event_list.append(event)
        return event_list


class GcalTogglUploader():

    def __init__(self, config_path=os.path.dirname(__file__)+"/config.yaml",
                        gcal_credentials_path="credentials.json",
                        gcal_token_path="token.json",
                        toggl_token_path="toggl_token.txt") -> None:
        with open(config_path, "r") as stream:
            try:
                config = yaml.safe_load(stream) # Throws yaml parse error
            except yaml.YAMLError as e:
                logging.exception(e)
                logging.error("Broken config file. Exiting.")
                exit(1)

        # Get user configurations
        self.summary_blacklist = config["summary_blacklist"]
        self.summary_project_dict = config["summary_project_map"]
        calendar_blacklist = config["calendar_blacklist"]
        self.calendar_project_map = config["calendar_project_map"]

        self.gcal = GcalInterface(credentials_path=gcal_credentials_path,token_path=gcal_token_path, blacklist=calendar_blacklist)
        self.toggl = TogglInterface(toggl_token_path)


    def is_blacklisted(self, event):
        for regexp in self.summary_blacklist:
            if re.search(regexp, event["summary"]) is not None: # If event matches blacklist, skip it.
                return True
        return False


    def update(self, start_time, end_time):
        """ Go through all events in the specified time frame and create events for them."""
        events = self.gcal.get_events(start_time=start_time, end_time=end_time)
        logging.debug(f"{events}\n")
        for event in events:
            logging.debug(event)
            event_start = event["start"].get("dateTime")
            event_end = event["end"].get("dateTime")
            if event_start is None or event_end is None:
                logging.debug(f"event has no end/start, skipping")
                continue
            event_start = event_start.split("+")[0] if "Z" not in event_start else event["start"].get("dateTime")[:-1]
            event_end = event_end.split("+")[0]  if "Z" not in event_end else event["end"].get("dateTime")[:-1]

            event_start = datetime.datetime.fromisoformat(event_start)#.replace(tzinfo=None)
            event_end = datetime.datetime.fromisoformat(event_end)#.replace(tzinfo=None)
            if event_start <= datetime.datetime.fromisoformat(end_time[:-1]) <= event_end:
                logging.debug(f"event is currently running, skipping")
                continue

            if self.is_blacklisted(event):
                logging.debug(f"event is blacklisted, skipping")
                continue
            summary = event["summary"]
            logging.info(f"Adding event {summary}")

            data = {}
            data["description"] = event["summary"]

            for regexp in self.summary_project_dict:
                if re.search(regexp, event["summary"]) is not None: # If summary matches an expression, use the mapped project
                    data["project_id"] = self.summary_project_dict[regexp]
            if data.get("project_id") is None:
                data["project_id"] = self.calendar_project_map.get(event["calendar"])

            data["start_time"] = event["start"]["dateTime"]
            data["stop_time"] = event["end"]["dateTime"]

            logging.debug(data)

            self.toggl.add_entry(**data)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("gcal_toggl.log", mode="w"),
            logging.StreamHandler()
        ])
    uploader = GcalTogglUploader()

    # Time range to look at events
    if os.path.exists("previous_time.txt"):
        with open("previous_time.txt") as f:
            start_time = f.read().strip()
    else:
        start_time = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat() + 'Z'
    end_time = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

    uploader.update(start_time=start_time, end_time=end_time)
    with open("previous_time.txt", "w") as f:
        f.write(end_time)


if __name__ == '__main__':
    main()
