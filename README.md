# RealityGuide

## Project Overview

TODO

## Quest 3 (Unity)

### Requirements

- **Unity:** 6000.0.38f1 or newer
- **Packages:**
  - [Meta MRUK](https://assetstore.unity.com/packages/tools/integration/meta-mr-utility-kit-272450) (v81 or higher)
  - [Unity Sentis](https://unity.com/sentis) (v2.1.3 for MultiObjectDetection sample)
- **Hardware:** Quest 3 / Quest 3S with Horizon OS v74 or higher
- **Permissions:** `horizonos.permission.HEADSET_CAMERA`
- **Passthrough:** Must be enabled in your project

> [!NOTE]
> You must use a physical headset to preview the passthrough camera. XR Simulator and Meta Horizon Link do not currently support passthrough cameras.

### Getting Started

1. Clone the GitHub project
2. Open the project with **Unity 6000.0.38f1** or newer
3. Open a sample scene from the **[`PassthroughCameraApiSamples`](./Assets/PassthroughCameraApiSamples/)** folder
4. Use **Meta > Tools > Project Setup Tool** to fix any configuration issues
5. Build and deploy to your Quest 3/3S device

## Backend

### Requirements

- Python
- uv

Learn more at ...(/py dir)

TODO


## License

The [`Oculus License`](./LICENSE.txt) applies to the SDK and supporting material. The [`MIT License`](./Assets/PassthroughCameraApiSamples/LICENSE.txt) applies to only certain, clearly marked documents. If an individual file does not indicate which license it is subject to, then the Oculus License applies.

However,
* Files from [`Assets/PassthroughCameraApiSamples/MultiObjectDetection/SentisInference/Model`](./Assets/PassthroughCameraApiSamples/MultiObjectDetection/SentisInference/Model) are licensed under [`MIT`](https://github.com/MultimediaTechLab/YOLO/blob/main/LICENSE).

See the [`CONTRIBUTING`](./CONTRIBUTING.md) file for how to help out.
