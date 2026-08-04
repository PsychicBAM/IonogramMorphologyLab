"""Rule Testing Lab — run rules on features / synthetic labeled rows."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.rule_builder.packs import validate_pack
from ionogram_morphology_lab.rule_builder.store import RuleStore
from ionogram_morphology_lab.rule_builder.testing import (
    confusion_vs_labels,
    run_rule_on_features,
    threshold_sweep,
)
from ionogram_morphology_lab.utils.paths import app_root


class RuleTestingPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.store = RuleStore()
        self._build()
        self.refresh()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        try:
            self.title.setText(self.i18n.t("rules.testing_title"))
        except Exception:
            self.title.setText("Лаборатория проверки правил" if ru else "Rule Testing Lab")
        self.note.setText(
            "Синтетические/разработческие проверки не являются научной валидацией. "
            "Разделяйте данные по дате, если в метках есть поле date."
            if ru
            else "Synthetic/development tests are not scientific validation. "
            "Split by date where labels include a date field."
        )
        for button, key in getattr(self, "_buttons", []):
            button.setText(self.i18n.t(key))

    def _build(self) -> None:
        root = QVBoxLayout(self)
        self.title = QLabel()
        self.note = QLabel()
        self.note.setWordWrap(True)
        root.addWidget(self.title)
        root.addWidget(self.note)
        self.retranslate()
        row = QHBoxLayout()
        self.rules = QListWidget()
        self.rules.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        row.addWidget(self.rules, 1)
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        row.addWidget(self.out, 2)
        root.addLayout(row, 1)
        btns = QHBoxLayout()
        self._buttons = []
        for key, slot in [
            ("test.refresh", self.refresh),
            ("test.run_selected", self._run),
            ("test.threshold_sweep", self._sweep),
            ("test.confusion", self._confusion),
            ("test.load_packs", self._load_packs),
        ]:
            b = QPushButton()
            b.clicked.connect(slot)
            self._buttons.append((b, key))
            btns.addWidget(b)
        root.addLayout(btns)
        self.retranslate()

    def refresh(self) -> None:
        self.rules.clear()
        for r in self.store.list_rules():
            self.rules.addItem(f"{r.rule_id} [{r.status}]")
        # also show pack rule ids for convenience
        packs = app_root() / "rule_packs"
        if packs.exists():
            for d in sorted(packs.iterdir()):
                if d.is_dir():
                    res = validate_pack(d)
                    if res.ok:
                        for r in res.rules:
                            self.rules.addItem(f"pack:{d.name}/{r.rule_id} [{r.status}]")

    def _selected_rules(self):
        from ionogram_morphology_lab.rule_builder.model import ScientificRule

        selected = []
        user = {r.rule_id: r for r in self.store.list_rules()}
        for item in self.rules.selectedItems():
            text = item.text()
            if text.startswith("pack:"):
                # pack:iml-core-spread-f/R001
                body = text.split(" ", 1)[0].removeprefix("pack:")
                pack_id, rid = body.split("/", 1)
                res = validate_pack(app_root() / "rule_packs" / pack_id)
                for r in res.rules:
                    if r.rule_id == rid:
                        selected.append(r)
            else:
                rid = text.split(" ")[0]
                if rid in user:
                    selected.append(user[rid])
        return selected

    def _demo_rows(self) -> list[dict]:
        return [
            {
                "date": "d1",
                "label": "frequency",
                "median_horizontal_width": 6.0,
                "horizontal_broadening_persistence": 0.4,
                "median_vertical_width": 2.0,
                "vertical_broadening_persistence": 0.1,
                "mixed_width_score": 0.2,
                "mixed_coverage": 0.1,
                "interference_dominance": 0.1,
            },
            {
                "date": "d2",
                "label": "range",
                "median_horizontal_width": 2.0,
                "horizontal_broadening_persistence": 0.1,
                "median_vertical_width": 10.0,
                "vertical_broadening_persistence": 0.5,
                "mixed_width_score": 0.2,
                "mixed_coverage": 0.1,
                "interference_dominance": 0.1,
            },
            {
                "date": "d3",
                "label": "none",
                "median_horizontal_width": 1.0,
                "horizontal_broadening_persistence": 0.05,
                "median_vertical_width": 1.0,
                "vertical_broadening_persistence": 0.05,
                "mixed_width_score": 0.1,
                "mixed_coverage": 0.05,
                "interference_dominance": 0.2,
            },
        ]

    def _run(self) -> None:
        rules = self._selected_rules()
        if not rules:
            QMessageBox.information(self, "Rule Testing", "Select one or more rules.")
            return
        rows = self._demo_rows()
        report = []
        for rule in rules:
            fired = [run_rule_on_features(rule, r) for r in rows]
            report.append({"rule_id": rule.rule_id, "status": rule.status, "fired": fired})
        self.out.setPlainText(json.dumps(report, indent=2, ensure_ascii=False))

    def _sweep(self) -> None:
        rules = self._selected_rules()
        if not rules:
            return
        rule = rules[0]
        feat = rule.feature_names[0] if rule.feature_names else (
            rule.conditions[0]["feature"] if rule.conditions else "median_horizontal_width"
        )
        values = [float(x) for x in range(0, 12)]
        res = threshold_sweep(rule, self._demo_rows(), feat, values)
        self.out.setPlainText(json.dumps({"feature": feat, "sweep": res}, indent=2))

    def _confusion(self) -> None:
        rules = self._selected_rules()
        if not rules:
            return
        cm = confusion_vs_labels(rules[0], self._demo_rows(), "label")
        self.out.setPlainText(json.dumps(cm, indent=2))

    def _load_packs(self) -> None:
        from ionogram_morphology_lab.rule_builder.packs import install_pack

        packs = app_root() / "rule_packs"
        msgs = []
        for d in sorted(packs.iterdir()) if packs.exists() else []:
            if d.is_dir():
                res = install_pack(d)
                msgs.append(f"{d.name}: ok={res.ok} errors={res.errors}")
        self.out.setPlainText("\n".join(msgs) or "No packs")
        self.refresh()
