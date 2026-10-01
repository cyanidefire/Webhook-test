import os
import threading
from urllib.parse import quote

import requests
from flask import Flask, request, abort

app = Flask(__name__)
print("VERSION: rename-subtasks v2")

TOKEN = os.environ["CLICKUP_TOKEN"]
SHARED_SECRET = os.environ["WEBHOOK_SECRET"]
LIST_ID = os.environ["LIST_ID"]
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}
API = "https://api.clickup.com/api/v2"

# Subtask headings for tasks
SUBTASK_SUFFIXES = ["CNC", "Sewing", "Foaming", "Upholstering"]

def get_task(task_id):
    r = requests.get(f"{API}/task/{task_id}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def ensure_tag(space_id, tag_name):
    # Errors are ignored on purpose: the tag may already exist
    requests.post(
        f"{API}/space/{space_id}/tag",
        headers=HEADERS,
        json={"tag": {"name": tag_name, "tag_fg": "#ffffff", "tag_bg": "#4169e1"}},
        timeout=20,
    )


def process(task_id):
    task = get_task(task_id)

    parent_id = task.get("parent")
    if not parent_id:
        print("parent task, nothing to do:", task_id)
        return
    if task["list"]["id"] != LIST_ID:
        print("skipped: list", task["list"]["id"], "does not match", LIST_ID)
        return

    parent_name = get_task(parent_id)["name"]
    original = task["name"].strip()

    # Skip anything already renamed
    if original.startswith(parent_name + " - "):
        return

    tag_name = original.lower()
    ensure_tag(task["space"]["id"], tag_name)

    requests.put(
        f"{API}/task/{task_id}",
        headers=HEADERS,
        json={"name": f"{parent_name} - {original}"},
        timeout=20,
    ).raise_for_status()
    print("renamed:", original, "->", f"{parent_name} - {original}")

    requests.post(
        f"{API}/task/{task_id}/tag/{quote(tag_name)}",
        headers=HEADERS,
        timeout=20,
    ).raise_for_status()
    print("tagged:", tag_name)


@app.post("/clickup")
def handle():
    if request.args.get("key") != SHARED_SECRET:
        abort(401)

    data = request.get_json()
    if data.get("event") == "taskCreated":
        threading.Thread(target=process, args=(data["task_id"],)).start()
    return "", 200