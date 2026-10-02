"""
Example client for the PT1 "p1s1e8" endpoint: getVehicleImageUrls.

Endpoint contract (per the approved Software Blueprint Document for this endpoint):

    POST /wp-json/pt1/v1/p1s1e8-vehicle-image-urls
    Content-Type: application/json

    Request body:
        {
            "stock_ids": ["<stock id>", ...],   # optional
            "vins":      ["<vin>", ...]         # optional
        }
    At least one of "stock_ids" / "vins" must be present and non-empty.

    Success response (HTTP 200) - a flat object, NOT the standard error envelope:
        {
            "base_url": "https://www.nvpap.com/wp-content/uploads/inventory-images/",
            "stock_ids": { "<stock id>": ["<filename>", ...], ... },
            "vins":      { "<vin>": ["<filename>", ...], ... }
        }
        - "base_url" always ends in "/" - a full image URL is base_url + filename.
        - An empty filename array for a key means that vehicle has no pictures
          available (a valid ID/VIN with zero images), not an error.
        - "vins" is keyed by the VIN exactly as requested, not by the stock
          number it resolves to.

    Error response - the standard CCL10ClientResponse envelope:
        {
            "success": <int code>,
            "return_msg": "<safe description>",
            "data": null
        }
        Codes used by this endpoint:
            1001  input validation failed (e.g. neither stock_ids nor vins sent)
            1002  caller not on the IP allow-list
            2     general/internal failure

This script is a vendor-facing demonstration only - it is not part of the
PT1 production codebase.
"""

import argparse
import json
import urllib.error
import urllib.request

LIVE_HOST = "https://www.nvpap.com"
DEV_HOST = "https://dev.nvpap.com"


def call_get_vehicle_image_urls(host, stock_ids=None, vins=None):
    """Send one request to the p1s1e8 endpoint and return the parsed JSON body.

    Raises urllib.error.HTTPError on a non-2xx response; the caller is expected
    to read the error body (see print_error_response below) to see the
    endpoint's standard error envelope.
    """
    body = {}
    if stock_ids is not None:
        body["stock_ids"] = stock_ids
    if vins is not None:
        body["vins"] = vins

    request = urllib.request.Request(
        f"{host}/wp-json/pt1/v1/p1s1e8-vehicle-image-urls",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def print_success_response(parsed_response):
    base_url = parsed_response["base_url"]

    print(f"  base_url: {base_url}")

    # The endpoint returns "stock_ids"/"vins" as {} when populated, but as a
    # bare [] when that key wasn't part of the request at all - normalize
    # that here rather than assuming it's always a dict.
    response_stock_ids = parsed_response.get("stock_ids") or {}
    response_vins = parsed_response.get("vins") or {}

    print("  stock_ids:")
    for stock_id, filenames in response_stock_ids.items():
        if filenames:
            urls = [base_url + filename for filename in filenames]
            print(f"    {stock_id}: {len(filenames)} image(s)")
            for url in urls:
                print(f"      {url}")
        else:
            print(f"    {stock_id}: no images available")

    print("  vins:")
    for vin, filenames in response_vins.items():
        if filenames:
            urls = [base_url + filename for filename in filenames]
            print(f"    {vin}: {len(filenames)} image(s)")
            for url in urls:
                print(f"      {url}")
        else:
            print(f"    {vin}: no images available (VIN unknown, or vehicle has no pictures)")


def print_error_response(http_error):
    error_body = json.loads(http_error.read().decode("utf-8"))
    print(f"  HTTP status: {http_error.code}")
    print(f"  success code: {error_body.get('success')}")
    print(f"  return_msg: {error_body.get('return_msg')}")
    print(f"  data: {error_body.get('data')}")


def run_example(host, title, stock_ids=None, vins=None):
    print(f"\n=== {title} ===")
    print(f"Request body: {json.dumps({'stock_ids': stock_ids, 'vins': vins})}")
    try:
        parsed_response = call_get_vehicle_image_urls(host, stock_ids=stock_ids, vins=vins)
        print_success_response(parsed_response)
    except urllib.error.HTTPError as http_error:
        print_error_response(http_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="p1s1e8 (getVehicleImageUrls) example client")
    parser.add_argument(
        "-dev",
        action="store_true",
        help=f"call {DEV_HOST} instead of {LIVE_HOST}",
    )
    args = parser.parse_args()
    host = DEV_HOST if args.dev else LIVE_HOST

    print(f"Using host: {host}")

    # Example 1: a mix of stock IDs and VINs, including two stock IDs
    # (H061988, H064083) that are known to have no pictures, to show how an
    # ID with zero images looks in the response (an empty filename array,
    # not an error).
    run_example(
        host,
        "Mixed stock IDs and VINs, including two vehicles with no pictures",
        stock_ids=["H061988", "H064083", "L132371", "H064918"],
        vins=["JHMCG66852C006157", "3B7HC13YXVG763731"],
    )

    # Example 2: VINs only.
    run_example(
        host,
        "VINs only",
        vins=["JT4RN55DXH7011155", "1FMZK02176GA31572", "4M2CU91188KJ37873"],
    )

    # Example 3: an intentionally invalid request - neither stock_ids nor
    # vins is populated - to show what a validation error looks like.
    run_example(
        host,
        "Invalid request - empty stock_ids and vins (expect a validation error)",
        stock_ids=[],
        vins=[],
    )
