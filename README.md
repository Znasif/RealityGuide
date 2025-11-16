# RealityGuide

RealityGuide is a visual coach for real-world tasks. Snap a photo through a Quest 3 and it shows what action to take next, illustrating it with easy-to-follow visuals instead of text.

TODO: Add an image or video here

## Why RealityGuide
- **Visual-first assistance:** Overlays show the very next move, so anyone can follow along without reading lengthy manuals.
- **Always up to date:** Snap a new photo after you make progress and the guide checks off what you finished while refreshing the next steps.
- **Flexible guidance:** The AI adapts to many kinds of tasks, turning whatever it sees into clear, step-by-step instructions.

## How It Works
1. **Capture:** A Unity app running on Quest 3/3S streams passthrough images (requires Horizon OS v74+, headset camera permission, and an MR-enabled scene).
2. **Understand:** `py/main.py` sends the frame to Gemini to infer the goal, enumerate key objects, and generate the ordered action list plus supporting imagery.
3. **Guide:** The FastAPI service returns JSON with next steps, per-object crops, highlight overlays, and the AI-generated visualization that can be surfaced in-headset or on a companion device.
4. **Refresh:** Each follow-up API call ingests the next image, marks completed work, and updates the plan while preserving visual context.

## Repository at a Glance
- `py/` – Python CLI, workflows, and HTTP API (see [py/README.md](./py/README.md) and `py/AGENTS.md`).
- `Assets/` + `ProjectSettings/` – Unity project configured for Quest passthrough capture.
- `Media/` – Sample outputs and reference assets.

## Getting Started
### 1. Capture Passthrough Images on Quest 3
- **Unity:** 6000.0.38f1 or newer.
- **Packages:** [Meta MRUK](https://assetstore.unity.com/packages/tools/integration/meta-mr-utility-kit-272450) v81+, [Unity Sentis](https://unity.com/sentis) v2.1.3 for the MultiObjectDetection sample.
- **Hardware:** Quest 3 / Quest 3S running Horizon OS v74 or higher.
- **Permissions:** `horizonos.permission.HEADSET_CAMERA` with Passthrough enabled.
- **Workflow:**
  1. Clone this repo and open it in the matching Unity version.
  2. Load a scene from `Assets/PassthroughCameraApiSamples/`.
  3. Run **Meta → Tools → Project Setup Tool** to resolve configuration issues.
  4. Build & deploy to a physical headset (XR Simulator / Horizon Link cannot preview passthrough).

### 2. Deploy the RealityGuide Web API

See [py/README.md](./py/README.md) for details.

## License

The [`Oculus License`](./LICENSE.txt) applies to the SDK and supporting material. The [`MIT License`](./Assets/PassthroughCameraApiSamples/LICENSE.txt) applies to only certain, clearly marked documents. If an individual file does not indicate which license it is subject to, then the Oculus License applies.

However,
* Files from [`Assets/PassthroughCameraApiSamples/MultiObjectDetection/SentisInference/Model`](./Assets/PassthroughCameraApiSamples/MultiObjectDetection/SentisInference/Model) are licensed under [`MIT`](https://github.com/MultimediaTechLab/YOLO/blob/main/LICENSE).

See the [`CONTRIBUTING`](./CONTRIBUTING.md) file for how to help out.
