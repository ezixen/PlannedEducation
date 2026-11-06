# Local MediaPipe assets (F-019)

Runtime face + gaze detection uses Google MediaPipe Face Landmarker **entirely in the browser** (WASM). No cloud ML and no paid APIs.

Binaries are produced by:

```bash
npm run ensure-ml
```

(`predev` / `build:prepare` also run this.)

| Path | Source |
|------|--------|
| `wasm/` | Copied from `node_modules/@mediapipe/tasks-vision/wasm` |
| `face_landmarker.task` | Downloaded from Google's free MediaPipe model storage |

Do not commit the large `.wasm` / `.task` blobs; CI and local installs regenerate them.
