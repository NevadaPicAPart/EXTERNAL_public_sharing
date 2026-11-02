"""
Experimental script to verify GoTo Connect OAuth credentials (client id, secret, PAT)
by exchanging them for an access token, then calling the Send Message endpoint:
https://developer.goto.com/guides/GoToConnect/18_HOW_useMessagingV2Api/

Credentials file format (--credentials-file):
    A JSON file containing a single object. This script reads the message_* keys (the
    webhook_* keys are used by register_goto_webhook_channel.py), e.g.:

    {
        "message_client_id": "",
        "message_client_secret": "",
        "message_personal_access_token": "",
        "message_account_key": "",
        "message_from_number": "",
        "message_to_number": ""
    }

    Required keys:
        message_client_id               - the OAuth client id, used as the Basic auth
                                          username when requesting an access token.
        message_client_secret           - the OAuth client secret, used as the Basic auth
                                          password when requesting an access token.
        message_personal_access_token   - the PAT exchanged for an access token via the
                                          "personal_access_token" grant type.
        message_account_key             - the GoTo Connect account key used in the
                                          Messaging V2 send URL.
        message_from_number             - the GoTo Connect number sending the message,
                                          E.164 format, e.g. +17025550100.
        message_to_number               - the number receiving the message, E.164 format,
                                          e.g. +17025550101.
"""

import argparse
import json

import requests

CREDENTIALS_FILE_HELP = """Credentials file format:
A JSON file containing a single object, e.g.:

{
    "message_client_id": "",
    "message_client_secret": "",
    "message_personal_access_token": "",
    "message_account_key": "",
    "message_from_number": "",
    "message_to_number": ""
}

Required keys:
  message_client_id               - the OAuth client id, used as the Basic auth username
                                    when requesting an access token.
  message_client_secret           - the OAuth client secret, used as the Basic auth
                                    password when requesting an access token.
  message_personal_access_token   - the PAT exchanged for an access token via the
                                    "personal_access_token" grant type.
  message_account_key             - the GoTo Connect account key used in the Messaging V2
                                    send URL.
  message_from_number             - the GoTo Connect number sending the message, E.164
                                    format, e.g. +17025550100.
  message_to_number               - the number receiving the message, E.164 format,
                                    e.g. +17025550101.
"""

DEFAULT_CREDENTIALS_FILE = "goto_connect_credentials.json"

REQUIRED_KEYS = [
    "message_client_id",
    "message_client_secret",
    "message_personal_access_token",
    "message_account_key",
    "message_from_number",
    "message_to_number",
]

MESSAGE_BODY = "Test message from experimental script"

TOKEN_URL = "https://authentication.logmeininc.com/oauth/token"
API_URL = "https://api.goto.com/messaging/v2/accounts/{account_key}/messages"


def get_access_token(client_id, client_secret, personal_access_token):
    response = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "personal_access_token",
            "pat": personal_access_token,
        },
    )

    print(f"Token request status code: {response.status_code}")
    try:
        response_json = response.json()
    except ValueError:
        print("Token response text:")
        print(response.text)
        return None

    print("Token response JSON:")
    print(response_json)
    return response_json.get("access_token")


def send_test_message(access_token, account_key, from_number, to_number):
    # Messaging V2 expects multipart/form-data with a JSON "request" part;
    # requests sets the multipart Content-Type itself when given `files`.
    headers = {"Authorization": f"Bearer {access_token}"}

    request_json = {
        "channel": "SMS",
        "from": from_number,
        "to": [to_number],
        "type": "simple",
        "components": [
            {
                "type": "body",
                "components": [
                    {
                        "type": "text",
                        "attributes": {"text": MESSAGE_BODY},
                    }
                ],
            }
        ],
    }

    url = API_URL.format(account_key=account_key)

    # The access token is redacted so the printed request is safe to share.
    print(f"Send message request: POST {url}")
    print("Send message request headers:")
    print(json.dumps({**headers, "Authorization": "Bearer <redacted>"}, indent=2))
    print('Send message request body (multipart/form-data, part "request", application/json):')
    print(json.dumps(request_json, indent=2))

    response = requests.post(
        url,
        headers=headers,
        files={"request": (None, json.dumps(request_json), "application/json")},
    )

    print(f"Send message status code: {response.status_code}")
    print("Send message response headers:")
    print(json.dumps(dict(response.headers), indent=2))
    try:
        print("Send message response JSON:")
        print(response.json())
    except ValueError:
        print("Send message response text:")
        print(response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        epilog=CREDENTIALS_FILE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--credentials-file",
        default=DEFAULT_CREDENTIALS_FILE,
        help="Path to the JSON file containing the credentials "
        "(see format description below). Default: %(default)s",
    )
    args = parser.parse_args()

    with open(args.credentials_file, "r", encoding="utf-8") as f:
        credentials = json.load(f)

    missing_keys = [k for k in REQUIRED_KEYS if not credentials.get(k)]
    if missing_keys:
        raise SystemExit(f"Credentials file is missing/empty keys: {', '.join(missing_keys)}")

    token = get_access_token(
        credentials["message_client_id"],
        credentials["message_client_secret"],
        credentials["message_personal_access_token"],
    )
    if not token:
        raise SystemExit("No access token received - not attempting to send message.")

    send_test_message(
        token,
        credentials["message_account_key"],
        credentials["message_from_number"],
        credentials["message_to_number"],
    )
