import argparse
from pathlib import Path

from PIL import Image

from shared import OutputSchema
from workflow import WorkflowArtifacts, actionable_steps, refresh_plan_from_image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check which steps from a previous plan are complete using a new scene image."
    )
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the updated scene image to analyze.",
    )
    parser.add_argument(
        "progress_json",
        type=Path,
        help="Path to the JSON file produced by main.py that captures the previous plan.",
    )
    args = parser.parse_args()

    output = check_completion(args.image_path, args.progress_json)
    print(output.model_dump_json(indent=2))


def check_completion(image_path: Path, progress_json_path: Path) -> OutputSchema:
    progress_json_path = Path(progress_json_path)
    existing = OutputSchema.model_validate_json(progress_json_path.read_text())

    image = _load_image(image_path)
    artifacts = refresh_plan_from_image(image, existing)
    _log_continuation_artifacts(artifacts)
    return artifacts.output


def _load_image(image_path: Path) -> Image.Image:
    path = Path(image_path)
    with Image.open(path) as image:
        return image.copy()


def _log_continuation_artifacts(artifacts: WorkflowArtifacts) -> None:
    if artifacts.highlight_path:
        print(
            "Saved continuation first-step bounding box visualization to "
            f"{artifacts.highlight_path}"
        )
    else:
        print(
            "Skipped continuation first-step bounding box visualization because no matching object was found for the first step."
        )

    remaining_steps = actionable_steps(artifacts.output.steps)
    first_step = remaining_steps[0] if remaining_steps else None
    if artifacts.highlight_path and first_step:
        if artifacts.banana_path:
            print(
                "Generated continuation banana image for the first step at "
                f"{artifacts.banana_path}"
            )
        else:
            print("Continuation banana image generation failed.")
    elif first_step is None:
        print(
            "Continuation banana image generation skipped because no steps were returned."
        )
    else:
        print(
            "Continuation banana image generation skipped because the first-step bounding box image was unavailable."
        )


if __name__ == "__main__":
    main()
