"""
Experimental script to register a GoTo Notification Channel of type "Webhook":
https://developer.goto.com/guides/GoToConnect/14_HOW_useNotificationChannelApi/

Exchanges the webhook OAuth credentials (client id, secret, PAT) for an access token, then
creates the channel with POST /notification-channel/v1/channels/{channelNickname}. GoTo
answers 201 and sends an empty request (user-agent "GoTo Notifications") to the webhook URL
as a creation check, so the webhook must be live and answer it.

The returned "channelId" is what a later subscription call (Call Events / Messaging V2)
uses, and the SAME token/user that creates the channel must create those subscriptions.

Credentials file format (--credentials-file):
    A JSON file containing a single object. This script reads the webhook_* keys (the
    message_* keys are used by test_goto_message_api_v2.py):

    {
        "webhook_client_id": "",
        "webhook_client_secret": "",
        "webhook_personal_access_token": "",
        "webhook_channel_nickname": "",
        "webhook_url": ""
    }

        webhook_client_id               - OAuth client id, Basic auth username for the token.
        webhook_client_secret           - OAuth client secret, Basic auth password.
        webhook_personal_access_token   - PAT exchanged via the "personal_access_token" grant.
        webhook_channel_nickname        - nickname for the channel, used in the request URL path.
        webhook_url                     - public URL GoTo posts notifications to.
"""

import argparse
import json
import os

import requests

DEFAULT_CREDENTIALS_FILE = "goto_connect_credentials.json"
# Written next to this script, so register_goto_webhook_subscription.py finds it.
DEFAULT_OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goto_webhook_channel.json")

TOKEN_URL = "https://authentication.logmeininc.com/oauth/token"
CHANNEL_URL = "https://api.goto.com/notification-channel/v1/channels/{channel_nickname}"

REQUIRED_KEYS = [
    "webhook_client_id",
    "webhook_client_secret",
    "webhook_personal_access_token",
    "webhook_channel_nickname",
    "webhook_url",
]


def get_access_token(client_id, client_secret, personal_access_token):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "personal_access_token",
        "pat": personal_access_token,
    }

    # Secrets are redacted so the printed request/response is safe to share.
    print(f"Token request: POST {TOKEN_URL}")
    print("Token request headers:")
    print(json.dumps({**headers, "Authorization": f"Basic <{client_id}:redacted>"}, indent=2))
    print("Token request body:")
    print(json.dumps({**data, "pat": "<redacted>"}, indent=2))

    response = requests.post(TOKEN_URL, auth=(client_id, client_secret), headers=headers, data=data)

    print(f"Token request status code: {response.status_code}")
    print("Token response headers:")
    print(json.dumps(dict(response.headers), indent=2))
    try:
        response_json = response.json()
    except ValueError:
        print("Token response text:")
        print(response.text)
        return None

    printed_response = {
        k: ("<redacted>" if k in ("access_token", "refresh_token", "id_token") else v)
        for k, v in response_json.items()
    }
    print("Token response JSON:")
    print(json.dumps(printed_response, indent=2))
    return response_json.get("access_token")


def create_webhook_channel(access_token, channel_nickname, webhook_url, output_file):
    url = CHANNEL_URL.format(channel_nickname=channel_nickname)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "channelType": "Webhook",
        "webhookChannelData": {"webhook": {"url": webhook_url}},
    }

    # The access token is redacted so the printed request is safe to share.
    printed_headers = {**headers, "Authorization": "Bearer <redacted>"}
    print(f"Create channel request: POST {url}")
    print("Create channel request headers:")
    print(json.dumps(printed_headers, indent=2))
    print("Create channel request body:")
    print(json.dumps(body, indent=2))

    response = requests.post(url, headers=headers, json=body)

    print(f"Create channel status code: {response.status_code} (201 = created)")
    print("Create channel response headers:")
    print(json.dumps(dict(response.headers), indent=2))
    try:
        response_json = response.json()
    except ValueError:
        print("Create channel response text:")
        print(response.text)
        return

    print("Create channel response JSON (record channelId):")
    print(json.dumps(response_json, indent=2))

    if response.status_code == 201:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(response_json, f, indent=2)
        print(f"Channel response written to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--credentials-file",
        default=DEFAULT_CREDENTIALS_FILE,
        help="Path to the JSON credentials file (see format description above). "
        "Default: %(default)s",
    )
    parser.add_argument(
        "--output-file",
        default=DEFAULT_OUTPUT_FILE,
        help="Path the channel response JSON (including channelId) is written to when the "
        "channel is created. Default: %(default)s",
    )
    args = parser.parse_args()

    with open(args.credentials_file, "r", encoding="utf-8") as f:
        credentials = json.load(f)

    missing_keys = [k for k in REQUIRED_KEYS if not credentials.get(k)]
    if missing_keys:
        raise SystemExit(f"Credentials file is missing/empty keys: {', '.join(missing_keys)}")

    token = get_access_token(
        credentials["webhook_client_id"],
        credentials["webhook_client_secret"],
        credentials["webhook_personal_access_token"],
    )
    if not token:
        raise SystemExit("No access token received - not creating channel.")

    create_webhook_channel(
        token,
        credentials["webhook_channel_nickname"],
        credentials["webhook_url"],
        args.output_file,
    )
