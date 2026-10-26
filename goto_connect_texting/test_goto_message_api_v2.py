"""
Experimental script to verify GoTo Connect OAuth credentials (client id, secret, PAT)
by exchanging them for an access token, then calling the Send Message endpoint:
https://developer.goto.com/guides/GoToConnect/18_HOW_useMessagingV2Api/

Credentials file format (--credentials-file):
    A JSON file containing an array of credential-combination objects to test, e.g.:

    [
        {
            "label": "amy_v2_pt10",
            "client_id": "",
            "client_secret": "",
            "personal_access_token": "",
            "account_key": ""
        }
    ]

    Each object requires:
        label                   - a short name identifying this combination, used in
                                   printed output and appended to the test message body.
        client_id               - the OAuth client id, used as the Basic auth username
                                   when requesting an access token.
        client_secret           - the OAuth client secret, used as the Basic auth
                                   password when requesting an access token.
        personal_access_token   - the PAT exchanged for an access token via the
                                   "personal_access_token" grant type.
        account_key             - the GoTo Connect account key used in the Messaging V2
                                   send URL.
"""

import argparse
import json

import requests

CREDENTIALS_FILE_HELP = """Credentials file format:
A JSON file containing an array of credential-combination objects to test, e.g.:

[
    {
        "label": "amy_v2_pt10",
        "client_id": "",
        "client_secret": "",
        "personal_access_token": "",
        "account_key": ""
    }
]

Each object requires:
  label                 - a short name identifying this combination, used in printed
                            output and appended to the test message body.
  client_id              - the OAuth client id, used as the Basic auth username when
                            requesting an access token.
  client_secret           - the OAuth client secret, used as the Basic auth password
                            when requesting an access token.
  personal_access_token   - the PAT exchanged for an access token via the
                            "personal_access_token" grant type.
  account_key             - the GoTo Connect account key used in the Messaging V2
                            send URL.
"""

DEFAULT_CREDENTIALS_FILE = "../../api_tokens/live/pt10/goto_connect_credentials.json"

OWNER_PHONE_NUMBER = "+17025837850"     # the GoTo Connect number sending the message
CONTACT_PHONE_NUMBER = "+19452108869"     # the number receiving the message
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


def send_test_message(access_token, account_key, label):
    # Messaging V2 expects multipart/form-data with a JSON "request" part;
    # requests sets the multipart Content-Type itself when given `files`.
    headers = {"Authorization": f"Bearer {access_token}"}

    request_json = {
        "channel": "SMS",
        "from": OWNER_PHONE_NUMBER,
        "to": [CONTACT_PHONE_NUMBER],
        "type": "simple",
        "components": [
            {
                "type": "body",
                "components": [
                    {
                        "type": "text",
                        "attributes": {"text": MESSAGE_BODY + label},
                    }
                ],
            }
        ],
    }

    response = requests.post(
        API_URL.format(account_key=account_key),
        headers=headers,
        files={"request": (None, json.dumps(request_json), "application/json")},
    )

    print(f"Send message status code: {response.status_code}")
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
        help="Path to the JSON file containing the credential combinations to test "
        "(see format description below). Default: %(default)s",
    )
    args = parser.parse_args()

    with open(args.credentials_file, "r", encoding="utf-8") as f:
        credential_combinations = json.load(f)

    for combination in credential_combinations:
        print(f"\n===== Testing {combination['label']} =====")
        token = get_access_token(
            combination["client_id"],
            combination["client_secret"],
            combination["personal_access_token"],
        )
        if not token:
            print("No access token received - not attempting to send message.")
            continue

        send_test_message(token, combination["account_key"], combination['label'])
