from PyQt6.QtCore import QThread, pyqtSignal
from services.dependency_manager import DependencyManager


class EngineCheckWorker(QThread):
    """Background worker for querying the PyPI registry for yt-dlp updates."""
    checked = pyqtSignal(dict)

    def run(self):
        dm = DependencyManager()
        result = dm.check()
        self.checked.emit(result)


class EngineUpdateWorker(QThread):
    """Background worker for downloading, staging, verifying, and applying yt-dlp updates."""
    updated = pyqtSignal(dict)

    def run(self):
        dm = DependencyManager()
        result = dm.update()
        self.updated.emit(result)


class EngineRollbackWorker(QThread):
    """Background worker for restoring the previous engine version from backup."""
    rolled_back = pyqtSignal(dict)

    def run(self):
        dm = DependencyManager()
        result = dm.rollback()
        self.rolled_back.emit(result)
