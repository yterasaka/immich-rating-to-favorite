#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PAGE_SIZE = 1000
BATCH_SIZE = 500


def api_request(headers, method, url, body=None):
    """
    Call the API and return the parsed JSON response.
    Returns None if the response body is empty (e.g. 204 No Content).
    """
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"\nAPI error: {method} {url}", file=sys.stderr)
        print(f"HTTP {e.code}", file=sys.stderr)
        print(e.read().decode("utf-8", errors="replace")[:2000], file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"\nRequest failed: {method} {url}", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)

    return json.loads(text) if text else None


def find_assets_by_rating(headers, base_url, rating):
    """
    Fetch all pages of assets with the given rating
    using Immich's metadata search API.
    """
    page = 1

    while True:
        body = {
            "rating": rating,
            # Exclude already-favorited assets on the server side
            "isFavorite": False,
            "page": page,
            "size": PAGE_SIZE,
        }

        data = api_request(
            headers,
            "POST",
            f"{base_url}/search/metadata",
            body,
        )

        # Handle responses with or without the "assets" wrapper,
        # which varies by Immich version
        assets_data = data.get("assets", data)
        items = assets_data.get("items", [])

        if not items:
            break

        for asset in items:
            yield asset

        # A null nextPage means this is the last page
        next_page = assets_data.get("nextPage")
        if not next_page:
            break

        page = int(next_page)


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    parser = argparse.ArgumentParser(
        description="Immich: Rating >= 1 のAssetをFavoriteにする"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="変更せず対象だけ表示する",
    )

    parser.add_argument(
        "--min-rating",
        type=int,
        default=1,
        choices=range(1, 6),
        help="Favoriteにする最低Rating (default: 1)",
    )

    args = parser.parse_args()

    base_url = os.environ.get("IMMICH_URL")
    api_key = os.environ.get("IMMICH_API_KEY")

    if not base_url or not api_key:
        print(
            "IMMICH_URL と IMMICH_API_KEY を環境変数に設定してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    if not base_url.startswith(("http://", "https://")):
        print(
            "IMMICH_URL は http:// または https:// から指定してください。"
            f" (現在の値: {base_url})",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = base_url.rstrip("/")

    # Accept both https://example.com and https://example.com/api
    if not base_url.endswith("/api"):
        base_url += "/api"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    me = api_request(headers, "GET", f"{base_url}/users/me")
    my_id = me["id"]

    print(f"Immich: {base_url}")
    print(f"User: {me.get('email', my_id)}")
    print(f"Minimum rating: {args.min_rating}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'UPDATE'}")
    print()

    targets = {}
    skipped_partner = 0

    # Rating is an exact match, so search each rating (1-5) separately
    for rating in range(args.min_rating, 6):
        count = 0

        for asset in find_assets_by_rating(
            headers, base_url, rating
        ):
            asset_id = asset["id"]

            # Search results include partner-shared assets, but other users'
            # assets cannot be updated and would fail the whole bulk update
            if asset.get("ownerId") != my_id:
                skipped_partner += 1
                continue

            # No update needed if already a favorite
            if asset.get("isFavorite", False):
                continue

            targets[asset_id] = {
                "id": asset_id,
                "name": asset.get("originalFileName", ""),
                "rating": rating,
            }

            count += 1

        print(f"Rating {rating}: {count} asset(s) to favorite")

    print()
    if skipped_partner:
        print(f"Skipped: {skipped_partner} partner asset(s)")
    print(f"Total: {len(targets)} asset(s)")

    if not targets:
        print("変更対象はありません。")
        return

    if args.dry_run:
        print()
        print("DRY RUNなので変更していません。")

        # Show only the first 20 as examples
        print("\nExamples:")
        for item in list(targets.values())[:20]:
            print(
                f"  Rating {item['rating']}  "
                f"{item['name']}  "
                f"{item['id']}"
            )

        if len(targets) > 20:
            print(f"  ... and {len(targets) - 20} more")

        return

    ids = list(targets.keys())

    print("\nUpdating favorites...")

    updated = 0

    for batch in chunks(ids, BATCH_SIZE):
        api_request(
            headers,
            "PUT",
            f"{base_url}/assets",
            {
                "ids": batch,
                "isFavorite": True,
            },
        )

        updated += len(batch)
        print(f"  {updated}/{len(ids)}")

    print()
    print(f"Done: {updated} asset(s) marked as Favorite.")


if __name__ == "__main__":
    main()