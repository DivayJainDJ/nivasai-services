"""Firestore trigger listener for complaint classification."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.complaint_classifier.service import get_firestore_client, process_complaint_document
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)
_listener_registration: Any = None
_trigger_thread: threading.Thread | None = None
_stop_event = threading.Event()
_state_lock = threading.Lock()


def _is_processable(data: dict) -> bool:
    if not data:
        return False
    if data.get("aiProcessed") is True:
        return False
    return data.get("status") == "processing"


def _on_snapshot(col_snapshot, changes, read_time) -> None:
    del col_snapshot, read_time
    for change in changes:
        if change.type.name not in {"ADDED", "MODIFIED"}:
            continue
        data = change.document.to_dict() or {}
        if not _is_processable(data):
            continue
        complaint_id = change.document.id
        logger.info("trigger_received", complaint_id=complaint_id)
        _executor.submit(process_complaint_document, complaint_id)


def _trigger_worker() -> None:
    global _listener_registration
    logger.info("complaint_trigger_worker_started")
    try:
        db = get_firestore_client()
        registration = db.collection("complaints").on_snapshot(_on_snapshot)
        with _state_lock:
            _listener_registration = registration
        logger.info("complaint_trigger_started")
    except Exception as exc:
        logger.error("complaint_trigger_start_failed", error=str(exc))
        return

    while not _stop_event.is_set():
        time.sleep(0.5)

    with _state_lock:
        registration = _listener_registration
        _listener_registration = None
    if registration is not None:
        try:
            registration.unsubscribe()
        except Exception as exc:
            logger.error("complaint_trigger_unsubscribe_failed", error=str(exc))
    logger.info("complaint_trigger_worker_stopped")


def start_complaint_trigger() -> None:
    """Start Firestore listener in non-blocking background thread."""
    global _trigger_thread
    with _state_lock:
        if _trigger_thread is not None and _trigger_thread.is_alive():
            logger.info("complaint_trigger_already_running")
            return
        _stop_event.clear()
        _trigger_thread = threading.Thread(
            target=_trigger_worker,
            name="complaint-trigger-thread",
            daemon=True,
        )
        _trigger_thread.start()
    logger.info("complaint_trigger_start_requested")


def stop_complaint_trigger() -> None:
    """Signal trigger worker to stop and unsubscribe safely."""
    global _trigger_thread
    _stop_event.set()
    thread = _trigger_thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=5)
    with _state_lock:
        _trigger_thread = None
    logger.info("complaint_trigger_stopped")
