**Status:** Approved
**Code:** Written

# PT1 p1s1e8 — getVehicleImageUrls API Reference

Description: IP-whitelisted endpoint returning the public URLs of every image that actually exists for a set of requested vehicle stock IDs and/or VINs.

## Endpoint

```
POST /wp-json/pt1/v1/p1s1e8-vehicle-image-urls
Content-Type: application/json
```

Not a public route — gated by `VpsIpWhitelistGuard::isCallerAllowed` before any other work (`permission_callback => '__return_true'` at the WP REST layer, same as every other PT1 endpoint, since the real access control is this endpoint's own whitelist check, not WP's permission system). JSON body, not form fields — unlike `p1s1e1`/`p1s1e6`'s `multipart/form-data`, since this payload is arrays (`stock_ids`/`vins`) rather than scalar filter values.

Request Body:
- Key: stock_ids
  - Type: Array of String
  - Required: No (at least one of `stock_ids`/`vins` required)
  - Description: vehicle stock numbers to return image URLs for.
- Key: vins
  - Type: Array of String
  - Required: No (at least one of `stock_ids`/`vins` required)
  - Description: vehicle VINs to resolve to a stock number and return image URLs for.

## Response shape — success and failure are deliberately different

This endpoint is a vendor-facing integration point (an external caller, not another part of this codebase — see `architecture_decisions_log.md`'s p1s1e8 entry for which vendor and why), and its success/failure responses are **not** symmetrical:

- **On success**, the response body is the plain, flat JSON object described in "Success response body" below — no `success`/`return_msg`/`data` envelope. An external vendor's integration only needs the data it asked for, not this codebase's internal standard-return-keys plumbing.
- **On failure**, the response uses the same `CCL10ClientResponse::send()` envelope every other PT1 endpoint uses (see "Error responses" below) — kept consistent with the rest of PT1 specifically so failures are logged, categorized, and debugged the same way across every endpoint, vendor-facing or not. A vendor integration still benefits from a stable, categorized error shape even though its happy-path shape is custom.
- Architect Reasoning: diverging only on the success shape (not also the failure shape) keeps the half of this contract that matters for observability (Z2's "copy-paste-to-AI-agent" debugging goal, `observability_guidelines.md` §2) identical to every other endpoint, while keeping the half that matters for vendor ergonomics (the success payload) clean and purpose-built instead of forcing an external integrator to unwrap `data` and ignore `success`/`return_msg` on every call.

## Success response body

HTTP 200. The response body is exactly this flat object — not nested under `data`:

- Key: base_url
  - Type: String
  - Description: the public base URL every filename in `stock_ids`/`vins` below must be appended directly to (no separator needed — this value already ends in `/`) to form a usable image URL — the same `image_base_url` configured in `pt1_p1s1e8_settings_json_reference.md`, returned once here rather than repeated on every filename.
  - Example Value(s): "https://www.nvpap.com/wp-content/uploads/inventory-images/"
  - Implementation Constraint: this value must always end in `/` — the endpoint builds it by appending `/` to the settings file's `image_base_url` if that value doesn't already end with one, so a caller can always do plain string concatenation (`base_url + filename`) without a conditional separator check.
  - Architect Reasoning: every returned image shares the same base URL, so repeating it on every filename in `stock_ids`/`vins` would just be restating the same value hundreds of times for a large request — returning it once here keeps the response small and keeps the base URL a single point of truth per response.
- Key: stock_ids
  - Type: Dictionary
  - Description: one entry per requested stock ID, keyed by the stock ID exactly as sent in the request.
  - Dictionary Value (per entry):
    - Type: Array of String
    - Description: the existing image filenames for that stock ID — not full URLs; append each one directly to `base_url` above (no separator needed) to build the actual image URL.
    - Example Value(s): ["12345_left.JPG", "12345_right.JPG"]
    - Valid Value(s): an empty array is a valid, successful result — it means the stock ID was recognized but has no images on disk, not an error.
- Key: vins
  - Type: Dictionary
  - Description: one entry per requested VIN, keyed by the VIN exactly as sent in the request (not its resolved stock number).
  - Dictionary Value (per entry):
    - Type: Array of String
    - Description: the existing image filenames for that VIN's vehicle — not full URLs; append each one directly to `base_url` above (no separator needed) to build the actual image URL.
    - Example Value(s): ["12345_left.JPG"]
    - Valid Value(s): an empty array covers two distinct cases this field does not currently distinguish between — the VIN doesn't resolve to any vehicle, or it resolves but that vehicle has no images on disk (see the endpoint SBD's Implementation Constraint).

Full success example (HTTP 200, exactly this shape — no wrapper):

```json
{
  "base_url": "https://www.nvpap.com/wp-content/uploads/inventory-images/",
  "stock_ids": { "12345": ["12345_left.JPG", "12345_right.JPG"], "67890": [] },
  "vins": { "1HGCM82633A004352": ["54321_left.JPG"] }
}
```

## Error responses

Failures use the standard `CCL10ClientResponse::send()` envelope — `{"success": <code>, "return_msg": <string>, "data": null}` — same as every other PT1 endpoint (see "Response shape" above for why success and failure differ here). `data` is always `null` on failure; `return_msg` is always a human-readable `"ClassName:FunctionName: ..."` description (per `CCL8SuccessCodes.php > CR::C_return_msg`) naming *what* failed, safe to show a client, required even on a 500 — it is never raw/technical detail (no stack trace, no SQL error text, no file path); that stays in `debug_data`, which is never sent to the client on any response (`CCL10ClientResponse::send()` has no `debug_data` parameter at all; internal diagnostic detail is logged server-side via `CCL9SentryWrapper` only — same rule `pt1_p1s1e1_getVehicleStock_api_reference.md`/`pt1_p1s1e6_getInterchangeOptions_api_reference.md` already document).

```json
{ "success": 1001, "return_msg": "getVehicleImageUrls: request Validation Failed. ", "data": null }
```

```json
{ "success": 2, "return_msg": "getVehicleImageUrls: VpsVehicleRepository::findStockNumberByVin database lookup failed. ", "data": null }
```

HTTP status is set to match (via `CCL10ClientResponse::C_http_status_by_success_code`):

| `success` code | Numeric value | Meaning | HTTP status |
|---|---|---|---|
| `RC::C_input_validation_failed` | `1001` | Request validation failed (neither `stock_ids` nor `vins` sent, or either is malformed) | 400 |
| `RC::C_ACL_check_failed` | `1002` | Caller's IP is not in the whitelist | 403 |
| `RC::C_general_failure` | `2` | Internal failure (DB lookup failed, or filesystem check failed) — `return_msg` names which call failed (see examples above) | 500 |

(`RC::C_success`/200 is not in this table — a successful response doesn't carry a `success` code at all; see "Success response body" above.)

Potential Issues: none yet — new endpoint.
