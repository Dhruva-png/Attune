from __future__ import annotations

from pathlib import Path

import pytest
from attune.vision.model_assets import MODEL_URLS, ensure_model


def test_unknown_model_name_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ensure_model("not_a_real_model.task", tmp_path)


def test_skips_download_when_file_already_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = tmp_path / "pose_landmarker_lite.task"
    existing.write_bytes(b"already-here")

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not download when the file already exists")

    monkeypatch.setattr("attune.vision.model_assets.httpx.stream", fail_if_called)

    result = ensure_model("pose_landmarker_lite.task", tmp_path)

    assert result == existing
    assert result.read_bytes() == b"already-here"


def test_downloads_and_writes_file_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def iter_bytes(self) -> list[bytes]:
            return [b"chunk-1", b"chunk-2"]

    class FakeStreamContext:
        def __enter__(self) -> FakeResponse:
            return FakeResponse()

        def __exit__(self, *exc_info: object) -> bool:
            return False

    calls: list[tuple[str, str]] = []

    def fake_stream(method: str, url: str, **kwargs: object) -> FakeStreamContext:
        calls.append((method, url))
        return FakeStreamContext()

    monkeypatch.setattr("attune.vision.model_assets.httpx.stream", fake_stream)

    result = ensure_model("hand_landmarker.task", tmp_path)

    assert result == tmp_path / "hand_landmarker.task"
    assert result.read_bytes() == b"chunk-1chunk-2"
    assert calls == [("GET", MODEL_URLS["hand_landmarker.task"])]
    assert not (tmp_path / "hand_landmarker.task.part").exists()
