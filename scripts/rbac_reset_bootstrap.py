"""
Wipe RBAC CSVs (users, roles, user_roles, role_permissions, user_brands) to headers only.
Restart the API after running so startup can seed SuperAdmin + SuperAdmin Console role.

Usage (from project root):
  python scripts/rbac_reset_bootstrap.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

# Project root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import config  # noqa: E402


def _wipe(path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=list(fieldnames)).writeheader()


def main() -> None:
    _wipe(config.RBAC_USERS_PATH, list(config.RBAC_USERS_FIELDS))
    _wipe(config.RBAC_ROLES_PATH, list(config.RBAC_ROLES_FIELDS))
    _wipe(config.RBAC_USER_ROLES_PATH, list(config.RBAC_USER_ROLES_FIELDS))
    _wipe(config.RBAC_ROLE_PERMISSIONS_PATH, list(config.RBAC_ROLE_PERMISSIONS_FIELDS))
    _wipe(config.RBAC_USER_BRANDS_PATH, list(config.RBAC_USER_BRANDS_FIELDS))
    print("RBAC CSVs reset to empty (headers only). Restart the server to bootstrap SuperAdmin + SuperAdmin Console role.")


if __name__ == "__main__":
    main()
