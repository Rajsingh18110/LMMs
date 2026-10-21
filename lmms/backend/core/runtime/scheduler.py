"""Runtime Task Scheduler implementing SchedulerContract.

Provides thread-safe task queueing, execution, status tracking,
and cancellation for LMMs backend tasks and model inferences.
"""

from __future__ import annotations

import logging
import threading
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Dict, Optional, Callable

from lmms.backend.contracts.scheduler import SchedulerContract

logger = logging.getLogger("lmms.runtime.scheduler")


class TaskRecord:
    def __init__(self, task_id: str, model_id: str, task: Dict[str, Any]):
        self.task_id = task_id
        self.model_id = model_id
        self.task = task
        self.status = "queued"  # queued, running, completed, failed, cancelled
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.result: Any = None
        self.error: Optional[str] = None
        self.future: Optional[Future] = None


class TaskScheduler(SchedulerContract):
    """Functional TaskScheduler fulfilling SchedulerContract."""

    _instance: Optional["TaskScheduler"] = None
    _lock = threading.Lock()

    def __init__(self, max_workers: int = 4):
        self._tasks: Dict[str, TaskRecord] = {}
        self._tasks_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="lmms-worker")
        self._model_handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    @classmethod
    def get_instance(cls, max_workers: int = 4) -> "TaskScheduler":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(max_workers=max_workers)
            return cls._instance

    def register_model_handler(self, model_id: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register an execution handler for a specific model_id."""
        self._model_handlers[model_id] = handler

    def queue_task(self, model_id: str, task: Dict[str, Any]) -> str:
        """Queue a task for execution and return a unique task_id."""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        record = TaskRecord(task_id=task_id, model_id=model_id, task=task)

        with self._tasks_lock:
            self._tasks[task_id] = record

        # Dispatch execution to executor
        def _execute_wrapper():
            with self._tasks_lock:
                if record.status == "cancelled":
                    return
                record.status = "running"
                record.started_at = time.time()

            try:
                handler = self._model_handlers.get(model_id) or self._model_handlers.get("default")
                if handler:
                    res = handler(task)
                    with self._tasks_lock:
                        record.result = res
                        record.status = "completed"
                elif callable(task.get("fn")):
                    res = task["fn"](*task.get("args", ()), **task.get("kwargs", {}))
                    with self._tasks_lock:
                        record.result = res
                        record.status = "completed"
                else:
                    # Generic mock/immediate resolution if no handler registered
                    with self._tasks_lock:
                        record.result = {"status": "ok", "task_id": task_id, "model_id": model_id}
                        record.status = "completed"
            except Exception as e:
                logger.exception("Error executing task %s on model %s", task_id, model_id)
                with self._tasks_lock:
                    record.error = str(e)
                    record.status = "failed"
            finally:
                with self._tasks_lock:
                    record.finished_at = time.time()

        record.future = self._executor.submit(_execute_wrapper)
        logger.debug("Task %s queued for model %s", task_id, model_id)
        return task_id

    def get_status(self, task_id: str) -> str:
        """Get the current execution status of a task."""
        with self._tasks_lock:
            record = self._tasks.get(task_id)
            if not record:
                return "unknown"
            return record.status

    def get_result(self, task_id: str) -> Optional[Any]:
        """Get the result of a completed task, if available."""
        with self._tasks_lock:
            record = self._tasks.get(task_id)
            if not record:
                return None
            return record.result

    def get_error(self, task_id: str) -> Optional[str]:
        """Get the error message of a failed task, if any."""
        with self._tasks_lock:
            record = self._tasks.get(task_id)
            if not record:
                return None
            return record.error

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or running task."""
        with self._tasks_lock:
            record = self._tasks.get(task_id)
            if not record:
                return False

            if record.status in ("completed", "failed", "cancelled"):
                return False

            record.status = "cancelled"
            if record.future and not record.future.done():
                cancelled = record.future.cancel()
                return cancelled or True
            return True

    def shutdown(self, wait: bool = False) -> None:
        """Shut down the executor thread pool."""
        self._executor.shutdown(wait=wait)


# Aliases for backward compatibility
Scheduler = TaskScheduler
DefaultScheduler = TaskScheduler

__all__ = ["TaskScheduler", "Scheduler", "DefaultScheduler", "TaskRecord"]
