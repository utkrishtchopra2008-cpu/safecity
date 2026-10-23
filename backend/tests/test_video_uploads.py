import asyncio
import io
import sys
from types import SimpleNamespace

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

    with pytest.raises(uploads.UploadTooLarge) as error:
        asyncio.run(run())
    assert error.value.code == "VIDEO_TOO_LARGE"


def test_empty_upload_has_a_typed_failure_and_is_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(uploads, "_inspect_video", lambda *_args: pytest.fail("decoder called"))

    async def run() -> None:
        await uploads.stage_video_upload(upload_file(b""), AppSettings())

    with pytest.raises(uploads.UploadValidationError) as error:
        asyncio.run(run())
    assert error.value.code == "VIDEO_EMPTY"


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


@pytest.mark.parametrize(
    ("opened", "fps", "frames", "width", "height", "decoded", "error"),
    [
        (False, 30.0, 300.0, 640, 480, True, "could not open"),
        (True, 0.0, 300.0, 640, 480, True, "invalid or unsupported"),
        (True, 30.0, 300.0, 640, 480, False, "no decodable frame"),
        (True, 30.0, 300.0, 6000, 5000, True, "invalid or unsupported"),
        (True, 1.0, 700.0, 640, 480, True, "duration is invalid or exceeds"),
    ],
)
def test_corrupt_or_unsupported_video_stream_is_rejected_and_released(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    opened: bool,
    fps: float,
    frames: float,
    width: int,
    height: int,
    decoded: bool,
    error: str,
) -> None:
    released = False

    class Capture:
        def isOpened(self) -> bool:
            return opened

        def get(self, property_id: int) -> float:
            values = {1: fps, 2: frames, 3: float(width), 4: float(height)}
            return values[property_id]

        def read(self) -> tuple[bool, object | None]:
            return decoded, object() if decoded else None

        def release(self) -> None:
            nonlocal released
            released = True

    capture = Capture()
    fake_cv2 = SimpleNamespace(
        VideoCapture=lambda _path: capture,
        CAP_PROP_FPS=1,
        CAP_PROP_FRAME_COUNT=2,
        CAP_PROP_FRAME_WIDTH=3,
        CAP_PROP_FRAME_HEIGHT=4,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    with pytest.raises(uploads.UploadValidationError, match=error):
        uploads._inspect_video(tmp_path / "corrupt.mp4", maximum_duration=600)

    assert released
