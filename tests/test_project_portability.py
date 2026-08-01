from __future__ import annotations

import json
import zipfile

from ionogram_morphology_lab.projects.portability import (
    export_project_package,
    import_project_package,
)


def test_portable_package_excludes_source_mat_and_can_relink(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "project.json").write_text(
        json.dumps({"name": "demo", "source_paths": ["E:/data/source.mat"]}),
        encoding="utf-8",
    )
    (project / "config").mkdir()
    (project / "config" / "settings.json").write_text("{}", encoding="utf-8")
    (project / "scripts").mkdir()
    (project / "scripts" / "demo.m").write_text("x = 1;", encoding="utf-8")
    (project / "models").mkdir()
    (project / "models" / "metadata.json").write_text("{}", encoding="utf-8")
    (project / "results").mkdir()
    (project / "results" / "result.json").write_text("{}", encoding="utf-8")
    (project / "source.mat").write_bytes(b"not included")

    package = export_project_package(project, tmp_path / "project.imlzip")
    with zipfile.ZipFile(package) as archive:
        assert "source.mat" not in archive.namelist()
        assert "project.json" in archive.namelist()
        assert "scripts/demo.m" in archive.namelist()

    imported = import_project_package(
        package, tmp_path / "imported", relink_source_paths=["D:/relinked.mat"]
    )
    assert imported["relinked_source_paths"] is True
    assert imported["source_paths"] == ["D:/relinked.mat"]
