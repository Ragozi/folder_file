from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from folder_file.accounts import Account
from folder_file.runner import SweepParams, sweep_once


@dataclass
class Job:
    id: str
    status: str = "queued"            # queued | running | done | error
    log: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    saved: int = 0
    deleted: int = 0
    error: str | None = None
    started_at: float | None = None
    ended_at: float | None = None

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "log": self.log[-200:],
            "files": self.files,
            "saved": self.saved,
            "deleted": self.deleted,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def get(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def list_recent(limit: int = 20) -> list[Job]:
    with _lock:
        items = sorted(
            _jobs.values(),
            key=lambda j: j.started_at or 0,
            reverse=True,
        )
        return items[:limit]


def submit_sweep(account: Account, params: SweepParams) -> Job:
    job = Job(id=uuid.uuid4().hex)
    with _lock:
        _jobs[job.id] = job

    def append(line: str) -> None:
        with _lock:
            job.log.append(line)

    def worker() -> None:
        with _lock:
            job.status = "running"
            job.started_at = time.time()
        try:
            res = sweep_once(account, params, log=append)
            with _lock:
                job.saved = res.saved
                job.deleted = res.deleted
                job.files = res.files
                job.status = "done"
                job.ended_at = time.time()
                if res.saved == 0:
                    job.log.append("No new attachments matched.")
                else:
                    job.log.append(f"Done. {res.saved} file(s) saved.")
        except Exception as e:
            with _lock:
                job.status = "error"
                job.error = f"{type(e).__name__}: {e}"
                job.ended_at = time.time()
                job.log.append(f"ERROR: {job.error}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return job
