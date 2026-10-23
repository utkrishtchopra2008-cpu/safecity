# Pinned local model artifacts

SafeCity can run two optional CPU-only OpenCV Zoo models for bounded frame observations. They are not event detectors. Neither model creates incident records, changes a review, or contributes an incident-reliability metric.

## Object classes: YOLOX-S, block-quantized INT8

- Artifact: `object_detection_yolox_2022nov_int8bq.onnx`, stored locally as `.data/models/yolox.onnx`.
- Immutable source revision: [`opencv/object_detection_yolox` at `78c368f74ce73ee28fc7a1be418a598c71b58b52`](https://huggingface.co/opencv/object_detection_yolox/tree/78c368f74ce73ee28fc7a1be418a598c71b58b52).
- SHA-256: `dcaae0aaa2fea4167f89235ee340eb869d3707b25712218d4c7ce921ac90e2ba` (9,744,418 bytes).
- Model and OpenCV Zoo code license: Apache-2.0, verified from the pinned [model license file](https://huggingface.co/opencv/object_detection_yolox/blob/78c368f74ce73ee28fc7a1be418a598c71b58b52/LICENSE). The [OpenCV Zoo model README](https://github.com/opencv/opencv_zoo/blob/main/models/object_detection_yolox/README.md) states all files in that model directory use Apache-2.0.
- Runtime: `opencv-python-headless==4.12.0.88` with `numpy==2.2.6`, OpenCV DNN backend on CPU.
- Contract: 640×640 RGB float32 letterboxed input in pixel range 0–255; 8,400 candidate rows with 85 values (box, objectness, and 80 COCO class scores). Decode/NMS follows the [OpenCV Zoo YOLOX reference implementation](https://github.com/opencv/opencv_zoo/blob/main/models/object_detection_yolox/yolox.py). The adapter bounds and normalizes boxes, rejects invalid scores/output shapes, and emits a maximum of 500 typed records per video, each with COCO class, uncalibrated model score, normalized coordinates, source frame index, reliable decoder timestamp or unknown status, model version, and evidence ID. Aggregate class counts/mean scores are also returned. A box is an object observation, not evidence of an incident.

## Face regions: YuNet

- Artifact: `face_detection_yunet_2023mar.onnx`, stored locally as `.data/models/yunet.onnx`.
- Immutable source revision: [`opencv/face_detection_yunet` at `3cc26e7f1014a5ee5d74a42acee58bafc9d0a310`](https://huggingface.co/opencv/face_detection_yunet/tree/3cc26e7f1014a5ee5d74a42acee58bafc9d0a310).
- SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` (232,589 bytes).
- Model license: MIT, verified from the pinned [model license file](https://huggingface.co/opencv/face_detection_yunet/blob/3cc26e7f1014a5ee5d74a42acee58bafc9d0a310/LICENSE) and stated in the [OpenCV Zoo YuNet README](https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/README.md).
- Runtime: OpenCV `FaceDetectorYN`, CPU target, frame dimensions passed as input size. The model returns face boxes and landmarks; SafeCity immediately discards them and persists only the number of detected regions. No recognition, embeddings, crops, identity attributes, or cross-frame association are implemented.

## Install and enable locally

Model weights are not committed. `.data/` is ignored by Git. From `backend/`, run:

```sh
python -m app.cli.download_models
```

The downloader uses fixed HTTPS revisions, streams to temporary files, enforces byte caps, checks SHA-256, then atomically installs owner-readable model and license files. Set the following in the ignored backend environment file and restart the worker:

```dotenv
DETECTOR_BACKEND=opencv_zoo
DETECTOR_VERSION=opencv-zoo-yolox-s-yunet-v1
DETECTOR_MODEL_DIR=../.data/models
```

Docker Compose mounts the local model directory read-only into the worker. If the files are absent or their bytes differ, the job fails with a safe model error; it does not silently fall back to simulated success. Keep `DETECTOR_BACKEND=simulated` to run quality-only processing without downloading models.

## Limits

Object samples are uniformly selected by source frame index and capped at 31 frames per clip; source timestamps are read from the decoder and never inferred from FPS. Quality sampling is capped at 181 frame indices. The pipeline shares the existing 120-second job deadline with quality sampling. This is a resource bound, not a measured throughput or reliability claim. COCO classes describe object categories only; they do not establish an event, offense, danger, or incident. A missing observation is not evidence that nothing happened. Optional quality thresholds default to unset; configured threshold breaches and sampled decode failures mark quality as uncertain. The face-region detector does not redact original videos; original evidence remains private and subject to the configured retention policy.
