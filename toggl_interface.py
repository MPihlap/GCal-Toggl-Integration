from toggl import api
from toggl.utils import Config

class TogglInterface:
  def __init__(self, token_filename="toggl_token.txt") -> None:
    token = ""
    with open(token_filename) as f:
        token = f.read().strip()

    self.config = Config.factory()  # Without None it will load the default config file
    self.config.api_token = token
    self.config.timezone = 'utc'  # Custom timezone

  def add_entry(self, description=None, start_time=None, stop_time=None, project_id=None):
    entry = api.TimeEntry(start_time, stop_time, description=description, project=project_id)
    entry.save()

  def start_tracking(self, description, project_id=None, client=None):
    api.TimeEntry.start_and_save(
        config=self.config,
        description=description,
        project=project_id
    )

  def stop_tracking(self):
    current = api.TimeEntry.objects.current(config=self.config)
    if current is not None:
      current.stop_and_save()
