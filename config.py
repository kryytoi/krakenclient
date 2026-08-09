import os


class Config:
    # Neon connection string, e.g.
    # postgresql://user:password@ep-xxxx.eu-central-1.aws.neon.tech/kraken?sslmode=require
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///kraken_dev.db"
    ).replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # AES-256 key used to encrypt the .jar before it is uploaded to GitHub
    # Releases, and handed to authenticated launchers to decrypt it.
    # Must be 32 raw bytes, base64-encoded here.
    KRAKEN_ENC_KEY_B64 = os.environ.get("KRAKEN_ENC_KEY_B64", "")

    # GitHub repo that hosts the encrypted client builds, e.g. "kraken/client-builds"
    GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # optional, for private repos

    ADMIN_USERNAMES = set(
        u.strip() for u in os.environ.get("ADMIN_USERNAMES", "admin").split(",")
    )
