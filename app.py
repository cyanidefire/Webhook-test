# imports
import os
import threading
import requests
from flask import Flask, request, abort

# Create the web application
app = Flask(__name__)

# Read the private values from Render's env variables
TOKEN = os.environ["CLICKUP_TOKEN"]
SHARED_SECRET = os.environ["WEBHOOK_SECRET"]
LIST_ID = os.environ["LIST_ID"]

# Data sent with every API call
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}
API = "https://api.clickup.com/api/v2"

# Subtask headings for tasks
SUBTASK_SUFFIXES = ["CNC", "Sewing", "Foaming", "Upholstering"]

# Create a tag
def ensure_tag(space_id, tag_name):
    requests.post(
        f"{API}/space/{space_id}/tag",
        headers=HEADERS,
        json={"tag": {"name": tag_name, "tag_fg": "#ffffff", "tag_bg": "#4169e1"}},
    )

# Recieve the ID for newly created task
def create_subtasks(task_id):
    # store details of task (info from clickup)
    task = requests.get(f"{API}/task/{task_id}", headers=HEADERS).json()

    # Loop guard
    if task.get("parent"):
        return
    if task["list"]["id"] != LIST_ID:
        return

    space_id = task["space"]["id"]

    # Only repeats for categories above
    for suffix in range(SUBTASK_SUFFIXES):
        # Adds a tag to each subtask or each station
        tag_name = suffix.lower()
        ensure_tag(space_id, tag_name)
        
        requests.post(
            f"{API}/list/{LIST_ID}/task",
            headers=HEADERS,
            json={
                "name": f"{task["name"]} - {suffix}", 
                "parent": task_id,
                "tags": [tag_name],
                },
        ).raise_for_status()

# Runs when port request recieved
@app.post("/clickup")
def handle():
    # Checks against secret header, gives randos a 401 :3
    if request.args.get("key") != SHARED_SECRET:
        abort(401)

    data = request.get_json()
    if data.get("event") == "taskCreated":
        threading.Thread(target=create_subtasks, args=(data["task_id"],)).start()
    return "", 200