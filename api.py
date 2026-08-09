import base64

import requests
from flask import Blueprint, request, jsonify, current_app

from models import db, User

api_bp = Blueprint("launcher_api", __name__)


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "hwid": user.hwid,
        "active": user.is_active_subscriber,
        "lifetime": user.lifetime,
        "subscription_until": user.subscription_until.isoformat() if user.subscription_until else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "license_token": user.license_token,
    }


@api_bp.post("/login")
def launcher_login():
    """Launcher sends username/password once, gets back a license_token
    it stores locally and reuses for /verify + /manifest calls."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"ok": False, "error": "invalid_credentials"}), 401

    return jsonify({"ok": True, "user": _user_payload(user)})


def _authenticate():
    token = request.headers.get("X-License-Token") or (request.get_json(silent=True) or {}).get("license_token")
    if not token:
        return None
    return User.query.filter_by(license_token=token).first()


@api_bp.post("/verify")
def verify():
    """Checks the license token + binds/validates the HWID.
    A fresh account has hwid = NULL and gets bound on first successful check.
    A mismatched HWID is rejected until the user buys a HWID reset."""
    user = _authenticate()
    if not user:
        return jsonify({"ok": False, "error": "invalid_token"}), 401

    if not user.is_active_subscriber:
        return jsonify({"ok": False, "error": "subscription_expired", "user": _user_payload(user)}), 402

    data = request.get_json(silent=True) or {}
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"ok": False, "error": "missing_hwid"}), 400

    if user.hwid is None:
        user.hwid = hwid
        db.session.commit()
    elif user.hwid != hwid:
        return jsonify({"ok": False, "error": "hwid_mismatch"}), 403

    return jsonify({"ok": True, "user": _user_payload(user)})


@api_bp.get("/manifest")
def manifest():
    """Returns where to download the encrypted build from GitHub and the
    AES key to decrypt it. Only served to a verified, paying, HWID-matched user."""
    user = _authenticate()
    if not user:
        return jsonify({"ok": False, "error": "invalid_token"}), 401
    if not user.is_active_subscriber:
        return jsonify({"ok": False, "error": "subscription_expired"}), 402

    hwid = request.args.get("hwid")
    if not hwid or user.hwid != hwid:
        return jsonify({"ok": False, "error": "hwid_mismatch"}), 403

    repo = current_app.config["GITHUB_REPO"]
    if not repo:
        return jsonify({"ok": False, "error": "server_not_configured"}), 500

    headers = {"Accept": "application/vnd.github+json"}
    token = current_app.config["GITHUB_TOKEN"]
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(f"https://api.github.com/repos/{repo}/releases/latest", headers=headers, timeout=10)
    if resp.status_code != 200:
        return jsonify({"ok": False, "error": "github_unavailable"}), 502

    release = resp.json()
    asset = next((a for a in release.get("assets", []) if a["name"].endswith(".enc")), None)
    if not asset:
        return jsonify({"ok": False, "error": "no_build_asset"}), 502

    return jsonify(
        {
            "ok": True,
            "version": release.get("tag_name"),
            "download_url": asset["browser_download_url"],
            "size": asset.get("size"),
            # AES-256-CBC key, base64. The .enc file itself starts with a 16-byte IV.
            "key_b64": current_app.config["KRAKEN_ENC_KEY_B64"],
        }
    )
