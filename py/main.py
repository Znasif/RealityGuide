import argparse
from pathlib import Path

from PIL import Image

from shared import OutputSchema
from workflow import WorkflowArtifacts, generate_plan_from_image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a manipulation plan and auxiliary images from a scene."
    )
    parser.add_argument(
        "image_path", type=Path, help="Path to the source scene image to analyze."
    )
    args = parser.parse_args()

    json = plan(args.image_path)
    print(json.model_dump_json(indent=2))


def plan(image_path: Path) -> OutputSchema:
    image = _load_image(image_path)
    artifacts = generate_plan_from_image(image)
    _log_plan_artifacts(artifacts)
    return artifacts.output


def _load_image(image_path: Path) -> Image.Image:
    path = Path(image_path)
    with Image.open(path) as image:
        return image.copy()


def _log_plan_artifacts(artifacts: WorkflowArtifacts) -> None:
    if artifacts.highlight_path:
        print(
            f"Saved first-step bounding box visualization to {artifacts.highlight_path}"
        )
    else:
        print(
            "Skipped first-step bounding box visualization because no matching object was found for the first step."
        )

    steps = artifacts.output.steps
    first_step = steps[0] if steps else None
    if artifacts.highlight_path and first_step:
        if artifacts.banana_path:
            print(
                f"Generated banana image for the first step at {artifacts.banana_path}"
            )
        else:
            print("Banana image generation failed.")
    elif first_step is None:
        print("Banana image generation skipped because no steps were returned.")
    else:
        print(
            "Banana image generation skipped because the first-step bounding box image was unavailable."
        )


if __name__ == "__main__":
    main()
