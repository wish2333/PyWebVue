"""Native system dialog wrappers."""

from __future__ import annotations

from typing import Any

import webview


class Dialog:
    """Wrapper around pywebview native file dialogs.

    Must be bound to a pywebview window via bind() before use.
    """

    def __init__(self) -> None:
        self._window: Any = None

    def bind(self, window: Any) -> None:
        """Bind a pywebview window reference."""
        self._window = window

    def open_file(
        self,
        title: str = "Open File",
        file_types: tuple[str, ...] = (),
        folder: str = "",
        multiple: bool = False,
    ) -> list[str] | None:
        """Open a native file selection dialog.

        Args:
            title: Dialog title.
            file_types: Filter tuples like ('Excel Files (*.xlsx;*.xls)',).
            folder: Initial directory path.
            multiple: Allow selecting multiple files.

        Returns:
            List of selected file paths, or None if cancelled.
        """
        return self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            directory=folder,
            allow_multiple=multiple,
            file_types=tuple(file_types) if file_types else (),
        )

    def open_folder(self, title: str = "Select Folder", folder: str = "") -> list[str] | None:
        """Open a native folder selection dialog.

        Returns:
            List containing the selected folder path, or None if cancelled.
        """
        return self._window.create_file_dialog(
            webview.FileDialog.FOLDER,
            directory=folder,
        )

    def save_file(
        self,
        title: str = "Save As",
        default_name: str = "",
        file_types: tuple[str, ...] = (),
        folder: str = "",
    ) -> list[str] | None:
        """Open a native save file dialog.

        Returns:
            List containing the save path, or None if cancelled.
        """
        return self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=folder,
            save_filename=default_name,
            file_types=tuple(file_types) if file_types else (),
        )
