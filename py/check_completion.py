import argparse
from pathlib import Path
from typing import List, Optional

from google.genai import types
from PIL import Image

from shared import (
    ObjectItem,
    OutputSchema,
    StepItem,
    StepsSchema,
    banana,
    client,
    highlight_first_step,
    resize_image,
)


CONTINUATION_HIGHLIGHT_PATH = Path("data/continuation_first_step_highlight.png")
CONTINUATION_BANANA_PATH = Path("data/continuation_first_step_banana.png")


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

    image_path = Path(image_path)
    current_image = Image.open(image_path)
    resized_image = resize_image(current_image)

    objects_summary = summarize_objects(existing.objects)
    steps_summary = summarize_steps(existing.steps)

    completion_prompt = f"""\
You previously generated a plan for a robot and are now checking progress.
Goal (repeat verbatim in the output): {existing.goal}

Objects reference list:
{objects_summary}

Prior ordered steps:
{steps_summary}

Look at the updated scene image (attachment) and determine which steps have been completed.
Instructions:
- For each existing step, keep its object_label identical.
- When a step is fully satisfied, prefix its text with "[DONE] " but keep the rest of the wording.
- For steps that still require work, rewrite the text so it reflects what remains.
- Maintain the execution order from top to bottom so the robot knows what to do next.
- Add new steps at the end only if more actions are required to finish the unchanged goal. Use an object_label from the reference list; never invent new labels.
- Always output JSON matching {{"goal": <goal>, "steps": [{{"text": <step>, "object_label": <label>}}, ...]}}.
- The "goal" field MUST be exactly: {existing.goal}

If no steps were provided, create a fresh ordered list that the robot can follow from the current state to finish the goal.
"""

    completion_text = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=[resized_image, completion_prompt],
        config=types.GenerateContentConfig(
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            response_mime_type="application/json",
            response_json_schema=StepsSchema.model_json_schema(),
        ),
    ).text

    assert completion_text is not None

    completion = StepsSchema.model_validate_json(completion_text)

    updated_output = OutputSchema(
        goal=existing.goal,
        objects=existing.objects,
        steps=completion.steps,
    )

    highlight_path = highlight_first_step(
        current_image,
        updated_output.objects,
        updated_output.steps,
        CONTINUATION_HIGHLIGHT_PATH,
    )
    if highlight_path:
        print(
            f"Saved continuation first-step bounding box visualization to {highlight_path}"
        )
    else:
        print(
            "Skipped continuation first-step bounding box visualization because no matching object was found for the first step."
        )

    banana_path: Optional[Path] = None
    first_step = updated_output.steps[0] if updated_output.steps else None
    if highlight_path and first_step:
        banana_path = banana(
            step_text=first_step.text,
            annotated_image_path=highlight_path,
            output_path=CONTINUATION_BANANA_PATH,
        )
        if banana_path:
            print(
                f"Generated continuation banana image for the first step at {banana_path}"
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

    return updated_output


def summarize_objects(objects: List[ObjectItem]) -> str:
    if not objects:
        return "No objects were provided."

    return "\n".join(
        f"{idx}. {obj.label} — box_2d {list(obj.box_2d)}"
        for idx, obj in enumerate(objects, start=1)
    )


def summarize_steps(steps: List[StepItem]) -> str:
    if not steps:
        return "(No previous steps. You may generate a fresh ordered list.)"

    return "\n".join(
        f"{idx}. {step.text} (object_label: {step.object_label})"
        for idx, step in enumerate(steps, start=1)
    )


if __name__ == "__main__":
    main()
