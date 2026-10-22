import asyncio
import io

import pytest
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.config import AppSettings
from app.media import uploads


def upload_file(payload: bytes) -> StarletteUploadFile:
    return StarletteUploadFile(
        file=io.BytesIO(payload),
        filename="capture.mp4",
        headers=Headers({"content-type": "video/mp4"}),
    )


def valid_mp4_header() -> bytes:
    return b"\x00\x00\x00\x18ftypisom" + b"x" * 64


def test_streamed_video_is_hashed_and_staged_with_mock_decoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(uploads, "_inspect_video", lambda _path, _limit: (12.5, 1280, 720))

    async def run() -> uploads.StagedVideo:
        return await uploads.stage_video_upload(upload_file(valid_mp4_header()), AppSettings())

    staged = asyncio.run(run())
    try:
        assert staged.byte_size == len(valid_mp4_header())
        assert staged.mime_type == "video/mp4"
        assert staged.duration_seconds == 12.5
        assert staged.path.read_bytes() == valid_mp4_header()
    finally:
        staged.remove()


def test_upload_size_is_checked_while_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        uploads, "_inspect_video", lambda _path, _limit: pytest.fail("decoder called")
    )

    async def run() -> None:
        await uploads.stage_video_upload(
            upload_file(valid_mp4_header()), AppSettings(max_upload_bytes=16)
        )

    with pytest.raises(uploads.UploadTooLarge):
        asyncio.run(run())


def test_mismatched_content_signature_is_rejected_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        uploads, "_inspect_video", lambda _path, _limit: pytest.fail("decoder called")
    )

    async def run() -> None:
        await uploads.stage_video_upload(upload_file(b"not a video container"), AppSettings())

    with pytest.raises(uploads.UploadValidationError):
        asyncio.run(run())


def test_client_path_in_filename_is_never_used_for_staging_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(uploads, "_inspect_video", lambda _path, _limit: (1.0, 16, 16))
    file = upload_file(valid_mp4_header())
    file.filename = "../../outside.mp4"

    async def run() -> uploads.StagedVideo:
        return await uploads.stage_video_upload(file, AppSettings())

    staged = asyncio.run(run())
    try:
        assert staged.path.name.startswith("safecity-upload-")
        assert staged.path.read_bytes() == valid_mp4_header()
    finally:
        staged.remove()
