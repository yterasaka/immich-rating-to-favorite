# immich/rating_to_favorite.py

Marks every photo in [Immich](https://immich.app/) with a star rating of 1 or higher as a Favorite.

- Only your own assets are updated; partner-shared assets are skipped.
- Assets that are already favorites are left untouched.
- Uses only the Python standard library (no `pip install` needed).

## Usage

```sh
export IMMICH_URL="https://immich.example.com"   # "/api" suffix is optional
export IMMICH_API_KEY="your-api-key"

# Preview the targets without changing anything
python3 ./rating_to_favorite.py --dry-run

# Apply the changes
python3 ./rating_to_favorite.py
```

| Option           | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `--dry-run`      | Show the target assets without updating them         |
| `--min-rating N` | Minimum rating to mark as favorite (1-5, default: 1) |

If the API key has restricted permissions, it needs `asset.read`, `asset.update` and `user.read`.

There is no undo, so run with `--dry-run` first.
