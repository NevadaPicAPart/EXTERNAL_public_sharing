"""
Experimental script to verify GoTo Connect OAuth credentials (client id, secret, PAT)
by exchanging them for an access token, then calling the Send Message endpoint:
https://developer.goto.com/GoToConnect/#tag/Message/paths/~1messaging~1v1~1messages/post

Credentials file format (--credentials-file):
    A JSON file containing an array of credential-combination objects to test, e.g.:

    [
        {
            "label": "amy_v2_pt10",
            "client_id": "ae594850-b4db-4ec6-bf3b-89ab88dc20b1",
            "client_secret": "bRKQlmPV6UliKM7zDWLy8cHL",
            "personal_access_token": "2700252579027495041_UksHCtlgIKniYEa7h3jNbEPMUjm6eY88"
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
"""

import argparse
import json

import requests

CREDENTIALS_FILE_HELP = """Credentials file format:
A JSON file containing an array of credential-combination objects to test, e.g.:

[
    {
        "label": "amy_v2_pt10",
        "client_id": "ae594850-b4db-4ec6-bf3b-89ab88dc20b1",
        "client_secret": "bRKQlmPV6UliKM7zDWLy8cHL",
        "personal_access_token": "2700252579027495041_UksHCtlgIKniYEa7h3jNbEPMUjm6eY88"
    }
]

Each object requires:
  label                  - a short name identifying this combination, used in printed
                            output and appended to the test message body.
  client_id              - the OAuth client id, used as the Basic auth username when
                            requesting an access token.
  client_secret           - the OAuth client secret, used as the Basic auth password
                            when requesting an access token.
  personal_access_token   - the PAT exchanged for an access token via the
                            "personal_access_token" grant type.
"""

DEFAULT_CREDENTIALS_FILE = "../../api_tokens/live/pt10/goto_connect_credentials.json"

OWNER_PHONE_NUMBER = "+17026374410"       # the GoTo Connect number sending the message
CONTACT_PHONE_NUMBER = "+19452108869"     # the number receiving the message
MESSAGE_BODY = "Test message from experimental script"

TOKEN_URL = "https://authentication.logmeininc.com/oauth/token"
API_URL = "https://api.goto.com/messaging/v1/messages"


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


def send_test_message(access_token, label):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "ownerPhoneNumber": OWNER_PHONE_NUMBER,
        "contactPhoneNumbers": [CONTACT_PHONE_NUMBER],
        "body": MESSAGE_BODY + label,
    }

    response = requests.post(API_URL, headers=headers, json=payload)

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
        if token:
            send_test_message(token, combination['label'])
        else:
            print("No access token received - not attempting to send message.")
