"""Primary executable entry: IonogramMorphologyLab.exe"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--smoke-test" in argv:
        from ionogram_morphology_lab import __app_name__, __version__

        print(f"{__app_name__} {__version__} smoke OK")
        return 0

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

    app = QApplication(argv)
    app.setApplicationName("Ionogram Morphology Lab")
    app.setOrganizationName("IonogramMorphologyLab")
    settings = SettingsStore()
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
