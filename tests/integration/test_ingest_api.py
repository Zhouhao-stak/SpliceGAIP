"""Integration tests for /api/ingest preview and apply."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from splicegaip.api.app import create_app

VENDOR_CSV = """Gene Name,Gene ID,Event Type,PSI Control,PSI Treatment,Delta PSI,p-value,q-value
GeneA,ENSG000001,Exon Skipping,80,35,-45,0.0001,0.0002
GeneB,ENSG000002,Retained Intron,20,75,55,<0.001,0.002
"""


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SPLICEGAIP_INGEST_ALLOW_EXTERNAL", "1")
    return TestClient(create_app())


def test_preview_then_apply(tmp_path, client):
    (tmp_path / "vendor.csv").write_text(VENDOR_CSV, encoding="utf-8")

    preview = client.post(
        "/api/ingest/preview", json={"input_dir": str(tmp_path), "use_llm": False}
    )
    assert preview.status_code == 200
    data = preview.json()
    assert data["status"] in {"mapped", "needs_review"}
    assert data["preview"]["valid_events"] == 2

    applied = client.post(
        "/api/ingest/apply",
        json={"input_dir": str(tmp_path), "mapping": data["mapping"]},
    )
    assert applied.status_code == 200
    result = applied.json()
    assert result["preview"]["valid_events"] == 2
    assert (tmp_path / "standardized" / "AS_event_master.csv").is_file()


def test_empty_mapping_is_rejected(tmp_path, client):
    (tmp_path / "vendor.csv").write_text(VENDOR_CSV, encoding="utf-8")

    response = client.post(
        "/api/ingest/apply", json={"input_dir": str(tmp_path), "mapping": {}}
    )

    assert response.status_code == 400


def test_external_directory_is_blocked_without_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("SPLICEGAIP_INGEST_ALLOW_EXTERNAL", raising=False)
    (tmp_path / "vendor.csv").write_text(VENDOR_CSV, encoding="utf-8")
    client = TestClient(create_app())

    response = client.post(
        "/api/ingest/preview", json={"input_dir": str(tmp_path), "use_llm": False}
    )

    assert response.status_code == 400
    assert "inside the runtime" in response.json()["detail"]
