import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from pync import Notifier  # For macOS notifications
import pyperclip  # For copying to clipboard
import pickle
from google.oauth2.credentials import Credentials
import random

# Function to generate a unique title and description for the video
def generate_title_and_description(video_path):
    base_name = os.path.basename(video_path)
    video_name, _ = os.path.splitext(base_name)

    # Generate a unique title using the video name and a random number
    title = f"{video_name.replace('_', ' ').title()} - {random.randint(1000, 9999)}"

    # Create a short description
    description = (
        f"This video was automatically uploaded using a Python script.\n"
        f"Filename: {base_name}\n"
        f"Enjoy the content!"
    )

    return title, description

# Function to upload the video to YouTube
def upload_to_youtube(video_path):
    print(f"Uploading video: {video_path}")

    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    credentials = None
    credentials_file = 'youtube_credentials.pkl'

    # Check if credentials file exists
    if os.path.exists(credentials_file):
        with open(credentials_file, 'rb') as token:
            credentials = pickle.load(token)

    # If no valid credentials, prompt user to log in
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES
            )
            credentials = flow.run_local_server(port=0)

        # Save the credentials for future use
        with open(credentials_file, 'wb') as token:
            pickle.dump(credentials, token)

    youtube = build('youtube', 'v3', credentials=credentials)

    # Generate title and description
    title, description = generate_title_and_description(video_path)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["automation", "python", "script"],
                "categoryId": "22"  # Category 22 is "People & Blogs"
            },
            "status": {
                "privacyStatus": "unlisted"  # Set video to Unlisted
            }
        },
        media_body=MediaFileUpload(video_path)
    )
    response = request.execute()
    video_link = f"https://www.youtube.com/watch?v={response['id']}"
    print(f"Video uploaded successfully: {video_link}")

    # Send desktop notification
    send_notification(video_link)

# Function to send macOS notification
def send_notification(video_link):
    Notifier.notify(
        f"Video uploaded successfully:\n{video_link}\nClick to copy.",
        title="YouTube Upload Complete",
        open=video_link  # Open link on click
    )
    pyperclip.copy(video_link)
    print("Link copied to clipboard.")

# Event handler to monitor the folder for new video files
class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(('.mov', '.mp4', '.mpeg')):
            print(f"New video detected: {event.src_path}")
            upload_to_youtube(event.src_path)  # Upload video

# Main script to monitor the Desktop folder
if __name__ == "__main__":
    # Set the specific path to monitor
    desktop_path = "/Users/homesachin/Desktop"
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, path=desktop_path, recursive=False)
    observer.start()

    print(f"Monitoring {desktop_path} for new videos...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
