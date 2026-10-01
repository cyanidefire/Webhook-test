import os
import time
import threading
from urllib.parse import quote

import requests
from flask import Flask, request, abort

app = Flask(__name__)

TOKEN = os.environ["CLICKUP_TOKEN"]
SHARED_SECRET = os.environ["WEBHOOK_SECRET"]
LIST_ID = os.environ["LIST_ID"]
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}
API = "https://api.clickup.com/api/v2"

# Subtask headings for tasks
SUBTASK_SUFFIXES = ["CNC", "Sewing", "Foaming", "Upholstering"]


WAIT_SECONDS = 5
MAX_TRIES = 12  # waits up to about a minute for the template's subtasks


def ensure_tag(space_id, tag_name):
    # Errors are ignored on purpose: the tag may already exist
    requests.post(
        f"{API}/space/{space_id}/tag",
        headers=HEADERS,
        json={"tag": {"name": tag_name, "tag_fg": "#ffffff", "tag_bg": "#4169e1"}},
    )


def get_task(task_id, with_subtasks=False):
    url = f"{API}/task/{task_id}"
    if with_subtasks:
        url += "?subtasks=true"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def process(task_id):
    task = get_task(task_id)

    # Ignore subtasks (prevents loops) and tasks outside your chosen list
    if task.get("parent"):
        return
    if task["list"]["id"] != LIST_ID:
        return

    # Wait for the template's subtasks to appear
    subtasks = []
    for _ in range(MAX_TRIES):
        time.sleep(WAIT_SECONDS)
        subtasks = get_task(task_id, with_subtasks=True).get("subtasks", [])
        if subtasks:
            break
    if not subtasks:
        print("No subtasks found for", task_id)
        return

    # Let any remaining template subtasks finish being created
    time.sleep(WAIT_SECONDS)
    subtasks = get_task(task_id, with_subtasks=True).get("subtasks", [])

    parent_name = task["name"]
    space_id = task["space"]["id"]

    for sub in subtasks:
        original = sub["name"].strip()

        # Skip anything already renamed
        if original.startswith(parent_name + " - "):
            continue

        tag_name = original.lower()
        ensure_tag(space_id, tag_name)

        requests.put(
            f"{API}/task/{sub['id']}",
            headers=HEADERS,
            json={"name": f"{parent_name} - {original}"},
        ).raise_for_status()

        requests.post(
            f"{API}/task/{sub['id']}/tag/{quote(tag_name)}",
            headers=HEADERS,
        ).raise_for_status()


@app.post("/clickup")
def handle():
    if request.args.get("key") != SHARED_SECRET:
        abort(401)

    data = request.get_json()
    if data.get("event") == "taskCreated":
        threading.Thread(target=process, args=(data["task_id"],)).start()
    return "", 200