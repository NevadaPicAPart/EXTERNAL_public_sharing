"""
Experimental script to subscribe a GoTo Notification Channel to Messaging V2 events:
https://developer.goto.com/guides/GoToConnect/18_HOW_useMessagingV2Api/

Run register_goto_webhook_channel.py first; it writes goto_webhook_channel.json, and this
script reads the "channelId" from it. It then exchanges the webhook OAuth credentials for an
access token and creates the subscription with POST /messaging/v2/subscriptions.

The access token must belong to the SAME user that created the channel, must be a Super Admin
token, and needs the messaging.v1.notifications.manage scope. The subscription is tied to
that user: if the user is deactivated or loses Super Admin, notifications stop and the
subscription must be re-created. The webhook must answer every event with an HTTP 2XX.

Credentials file format (--credentials-file):
    A JSON file containing a single object. This script reads the webhook_* keys:

    {
        "webhook_client_id": "",
        "webhook_client_secret": "",
        "webhook_personal_access_token": "",
        "webhook_account_key": ""
    }

        webhook_client_id               - OAuth client id, Basic auth username for the token.
        webhook_client_secret           - OAuth client secret, Basic auth password.
        webhook_personal_access_token   - PAT exchanged via the "personal_access_token" grant.
        webhook_account_key             - the organization key, sent as both "accountKey" and
                                          "ownerEntity" of the subscription.
"""

import argparse
import json
import os

import requests

DEFAULT_CREDENTIALS_FILE = "goto_connect_credentials.json"
# Written by register_goto_webhook_channel.py, next to these scripts.
DEFAULT_CHANNEL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goto_webhook_channel.json")

TOKEN_URL = "https://authentication.logmeininc.com/oauth/token"
SUBSCRIPTION_URL = "https://api.goto.com/messaging/v2/subscriptions"

OWNER_ENTITY_TYPE = "ORGANIZATION"
EVENT_TYPES = ["INBOUND_MESSAGE", "DELIVERY_STATUS"]

REQUIRED_KEYS = [
    "webhook_client_id",
    "webhook_client_secret",
    "webhook_personal_access_token",
    "webhook_account_key",
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


def create_subscription(access_token, account_key, channel_id):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "accountKey": account_key,
        "ownerEntity": account_key,
        "ownerEntityType": OWNER_ENTITY_TYPE,
        "channelId": channel_id,
        "eventTypes": EVENT_TYPES,
    }

    # The access token is redacted so the printed request is safe to share.
    print(f"Create subscription request: POST {SUBSCRIPTION_URL}")
    print("Create subscription request headers:")
    print(json.dumps({**headers, "Authorization": "Bearer <redacted>"}, indent=2))
    print("Create subscription request body:")
    print(json.dumps(body, indent=2))

    response = requests.post(SUBSCRIPTION_URL, headers=headers, json=body)

    print(f"Create subscription status code: {response.status_code} (201 = created)")
    print("Create subscription response headers:")
    print(json.dumps(dict(response.headers), indent=2))
    try:
        print("Create subscription response JSON:")
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print("Create subscription response text:")
        print(response.text)


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
        "--channel-file",
        default=DEFAULT_CHANNEL_FILE,
        help="Path to the channel JSON written by register_goto_webhook_channel.py. "
        "Default: %(default)s",
    )
    args = parser.parse_args()

    with open(args.credentials_file, "r", encoding="utf-8") as f:
        credentials = json.load(f)

    missing_keys = [k for k in REQUIRED_KEYS if not credentials.get(k)]
    if missing_keys:
        raise SystemExit(f"Credentials file is missing/empty keys: {', '.join(missing_keys)}")

    with open(args.channel_file, "r", encoding="utf-8") as f:
        channel = json.load(f)
    channel_id = channel.get("channelId")
    if not channel_id:
        raise SystemExit(f"No 'channelId' found in {args.channel_file}")

    token = get_access_token(
        credentials["webhook_client_id"],
        credentials["webhook_client_secret"],
        credentials["webhook_personal_access_token"],
    )
    if not token:
        raise SystemExit("No access token received - not creating subscription.")

    create_subscription(token, credentials["webhook_account_key"], channel_id)
