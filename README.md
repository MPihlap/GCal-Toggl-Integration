# GCal-Toggl-Integration
Integration to create time entries automatically based on google calendar events.


## Usage

1. Setup the google calendar API (https://developers.google.com/calendar/api/quickstart/python)
    * Use the OAuth2 desktop app credentials
2. Save your toggl API token into a file named "toggl_token.txt".
3. Install requirements using `python3 -m pip install -r requirements.txt`
4. Modify `config.yaml` to customize behaviour to your needs.
5. Run the `gcal_toggl_integration.py` file to add events from the past 24 hours or create your own scripts based on the example found in the `main` function.
