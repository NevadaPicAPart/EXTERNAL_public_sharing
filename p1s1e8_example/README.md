# p1s1e8 (getVehicleImageUrls) example client

Demonstrates calling the `POST /wp-json/pt1/v1/p1s1e8-vehicle-image-urls` endpoint.

Run:

```
python p1s1e8_example.py
```

Requires only the Python standard library (`urllib`, `json`).

The script shows three cases:
1. A mixed request of stock IDs and VINs, including two stock IDs (`H061988`,
   `H064083`) that have no pictures, to show how a "no images" result looks
   (an empty array, not an error).
2. A VIN-only request.
3. An intentionally invalid request (empty `stock_ids`/`vins`) to show the
   error response shape.

See the docstring at the top of `p1s1e8_example.py` for the full request/
response contract.
