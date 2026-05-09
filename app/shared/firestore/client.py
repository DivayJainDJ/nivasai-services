"""Firebase client initialization for local credential-file auth."""

from __future__ import annotations

from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.config import settings


def _initialize_firebase_app() -> firebase_admin.App:
    if firebase_admin._apps:
        return firebase_admin.get_app()
    cred_path = Path("credentials/serviceAccountKey.json")
    if not cred_path.exists():
        raise RuntimeError(f"Missing Firebase service account key: {cred_path}")
    cred = credentials.Certificate(str(cred_path))
    return firebase_admin.initialize_app(cred, {"storageBucket": settings.FIREBASE_STORAGE_BUCKET})


def get_firestore_client() -> firestore.Client:
    _initialize_firebase_app()
    return firestore.client()


def get_storage_bucket():
    _initialize_firebase_app()
    return storage.bucket()


db = get_firestore_client()
bucket = get_storage_bucket()
