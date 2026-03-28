"""{{CLASS_NAME}} business API - define your public methods here."""

from __future__ import annotations

from pywebvue import ApiBase, Result, ErrCode


class {{CLASS_NAME}}Api(ApiBase):
    """Main API class for {{PROJECT_TITLE}}.

    All public methods (not prefixed with _) are automatically exposed
    to the frontend via pywebview's JS bridge.
    """

    def health_check(self) -> Result:
        """Return backend status information."""
        return Result.ok(data={"status": "running"})

    def on_file_drop(self, file_paths: list[str]) -> None:
        """Handle files dropped onto the window.

        Override this method to process dropped files.
        """
        for path in file_paths:
            self.logger.info(f"File dropped: {path}")
            self.emit("file:dropped", {"path": path})
