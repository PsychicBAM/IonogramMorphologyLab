"""Dismissible page introduction panels (progressive disclosure)."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class IntroPanel(QFrame):
    """Compact intro: purpose, when, what to do, after click, risks, help link."""

    def __init__(
        self,
        page_id: str,
        i18n,
        settings,
        *,
        purpose_en: str,
        purpose_ru: str,
        when_en: str,
        when_ru: str,
        action_en: str,
        action_ru: str,
        after_en: str,
        after_ru: str,
        risk_en: str,
        risk_ru: str,
        help_id: str = "quick_start",
        parent=None,
    ):
        super().__init__(parent)
        self.page_id = page_id
        self.i18n = i18n
        self.settings = settings
        self.help_id = help_id
        self._texts = {
            "purpose": (purpose_en, purpose_ru),
            "when": (when_en, when_ru),
            "action": (action_en, action_ru),
            "after": (after_en, after_ru),
            "risk": (risk_en, risk_ru),
        }
        self.setObjectName(f"intro_{page_id}")
        # Explicit colors so text stays readable under light and dark system themes.
        self.setStyleSheet(
            "QFrame#intro_%s { background:#eef3f9; border:1px solid #8fa3b8; border-radius:6px; }"
            "QFrame#intro_%s QLabel { color:#1a2330; }"
            "QFrame#intro_%s QPushButton { color:#1a2330; }"
            % (page_id, page_id, page_id)
        )
        lay = QVBoxLayout(self)
        head = QHBoxLayout()
        self.title = QLabel()
        self.title.setStyleSheet("font-weight:600;")
        head.addWidget(self.title, 1)
        self.btn_hide = QPushButton()
        self.btn_hide.clicked.connect(self.dismiss)
        head.addWidget(self.btn_hide)
        lay.addLayout(head)
        self.body = QLabel()
        self.body.setWordWrap(True)
        lay.addWidget(self.body)
        self.retranslate()
        dismissed = self.settings.get("ux", "dismissed_intros", {}) or {}
        if dismissed.get(page_id):
            self.hide()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.title.setText("О этой странице" if ru else "About this page")
        self.btn_hide.setText("Скрыть" if ru else "Hide")
        def t(key: str) -> str:
            en, r = self._texts[key]
            return r if ru else en
        self.body.setText(
            f"<b>{'Зачем' if ru else 'Purpose'}:</b> {t('purpose')}<br>"
            f"<b>{'Когда' if ru else 'When'}:</b> {t('when')}<br>"
            f"<b>{'Что сделать' if ru else 'What to do'}:</b> {t('action')}<br>"
            f"<b>{'После кнопки' if ru else 'After the main action'}:</b> {t('after')}<br>"
            f"<b>{'Что может пойти не так' if ru else 'What can go wrong'}:</b> {t('risk')}<br>"
            f"<b>{'Справка' if ru else 'Help'}:</b> {self.help_id}"
        )

    def dismiss(self) -> None:
        dismissed = dict(self.settings.get("ux", "dismissed_intros", {}) or {})
        dismissed[self.page_id] = True
        self.settings.set("ux", "dismissed_intros", dismissed)
        self.settings.save()
        self.hide()

    def restore(self) -> None:
        dismissed = dict(self.settings.get("ux", "dismissed_intros", {}) or {})
        dismissed.pop(self.page_id, None)
        self.settings.set("ux", "dismissed_intros", dismissed)
        self.settings.save()
        self.show()
        self.retranslate()
