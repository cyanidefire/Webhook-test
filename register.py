import requests

TOKEN = "pk_99808413_AZIFHDOR8TXP2VVV7K5B6I74H6SLNK4L"
LIST_ID = "901222756953"
ENDPOINT = "https://webhook-test-bz5m.onrender.com/clickup?key=testingkey12345"

headers = {"Authorization": TOKEN}

teams = requests.get("https://api.clickup.com/api/v2/team", headers=headers).json()
team_id = teams["teams"][0]["id"]
print("Workspace:", teams["teams"][0]["name"], team_id)

r = requests.post(
	f"https://api.clickup.com/api/v2/team/{team_id}/webhook",
	headers=headers,
	json={
		"endpoint": ENDPOINT,
		"events": ["taskCreated"],
		"list_id": LIST_ID,
	},
)

print(r.status_code)
print(r.json())