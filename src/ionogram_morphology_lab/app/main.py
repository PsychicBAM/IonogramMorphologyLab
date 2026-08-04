"""Primary executable entry: IonogramMorphologyLab.exe"""

from __future__ import annotations

import logging
import sys
import traceback

_LOG = logging.getLogger("ionogram_morphology_lab")


def _install_last_resort_excepthook() -> None:
    """Log uncaught errors; never present a false successful scientific result."""

    def _hook(exc_type, exc, tb) -> None:
        try:
            _LOG.error("Uncaught exception:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        except Exception:  # noqa: BLE001
            pass
        # Keep default stderr reporting; do not pretend success.
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--smoke-test" in argv:
        from ionogram_morphology_lab import __app_name__, __version__

        print(f"{__app_name__} {__version__} smoke OK")
        return 0

    # Headless Feature Pipeline V2 child process (Phase 4B.2h) — no QApplication.
    try:
        from ionogram_morphology_lab.ui.v2_process_worker import WORKER_FLAG, is_worker_argv, run_worker_loop

        if is_worker_argv(argv) or WORKER_FLAG in argv:
            return int(run_worker_loop())
    except Exception as exc:  # noqa: BLE001
        print(f"V2 worker failed to start: {exc}", file=sys.stderr)
        return 3

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        print(
            "PySide6 is required for the desktop UI. "
            "Install requirements/requirements-base.txt. "
            f"Blocker: {exc}",
            file=sys.stderr,
        )
        return 2

    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.security import ProtectedStudyConfig, set_active_protection
    from ionogram_morphology_lab.ui.language_dialog import LanguageDialog
    from ionogram_morphology_lab.ui.main_window import MainWindow

    _install_last_resort_excepthook()
    app = QApplication(argv)
    app.setApplicationName("Ionogram Morphology Lab")
    app.setOrganizationName("IonogramMorphologyLab")
    try:
        from pathlib import Path

        from PySide6.QtGui import QIcon

        from ionogram_morphology_lab.utils.paths import app_root

        icon_path = app_root() / "assets" / "IonogramMorphologyLab.ico"
        if not icon_path.exists():
            # Frozen portable layout: icon next to the executable.
            icon_path = Path(getattr(sys, "_MEIPASS", app_root())) / "assets" / "IonogramMorphologyLab.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:  # noqa: BLE001
        pass
    settings = SettingsStore()
    try:
        from ionogram_morphology_lab.ui.theme import apply_app_theme

        apply_app_theme(app, settings.get("general", "theme", "system"))
    except Exception:  # noqa: BLE001
        pass
    # Optional protected study — disabled by default
    if settings.get("privacy", "protected_study_enabled", False):
        cfg_path = settings.get("privacy", "protected_study_config_path", "")
        if cfg_path:
            set_active_protection(ProtectedStudyConfig.load(cfg_path))
        else:
            set_active_protection(ProtectedStudyConfig(enabled=True))
    else:
        set_active_protection(ProtectedStudyConfig(enabled=False))

    lang = LanguageDialog.ask_language()
    win = MainWindow(language=lang or "en")
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
