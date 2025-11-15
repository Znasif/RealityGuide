import argparse
from pathlib import Path
from typing import Optional

from google.genai import types
from PIL import Image

from shared import (
    AnalysisSchema,
    BANANA_OUTPUT_PATH,
    FIRST_STEP_HIGHLIGHT_PATH,
    OBJECT_CROP_DIR,
    OutputSchema,
    StepsSchema,
    banana,
    client,
    crop_and_save_objects,
    highlight_first_step,
    resize_image,
    resize_images,
)


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
    image_path = Path(image_path)
    original_image = Image.open(image_path)
    analysis_image = resize_image(original_image)

    analysis_prompt = """\
Inspect the provided image and infer a single high-level goal that represents the most reasonable outcome in the situation.
Express the goal as a short imperative sentence grounded solely in the visual evidence.

Identify the objects that are relevant to achieving the goal and provide their bounding boxes.
Each detected object must be assigned a unique identifying label.
Represent every bounding box using "box_2d": [ymin, xmin, ymax, xmax] with each coordinate normalized to the 0–1000 range (integers).

Return a JSON object structured as:
{
    "goal": <goal>,
    "objects": [{"label": <label>, "box_2d": [ymin, xmin, ymax, xmax]}, ...]
}"""

    analysis_text = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=[
            analysis_image,
            analysis_prompt,
        ],
        config=types.GenerateContentConfig(
            temperature=0.5,
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1
            ),  # dynamic thinking
            response_mime_type="application/json",
            response_json_schema=AnalysisSchema.model_json_schema(),
        ),
    ).text

    assert analysis_text is not None

    analysis = AnalysisSchema.model_validate_json(analysis_text)

    cropped_assets = crop_and_save_objects(
        original_image, analysis.objects, OBJECT_CROP_DIR
    )
    crop_images = [asset[1] for asset in cropped_assets]
    resized_crop_images = resize_images(crop_images)

    objects_summary = (
        "\n".join(
            f"{idx}. {obj.label} — box_2d {list(obj.box_2d)}"
            for idx, obj in enumerate(analysis.objects, start=1)
        )
        if analysis.objects
        else "No objects were detected in the first pass."
    )

    attachment_note = (
        " and cropped close-up images for each listed object (these attachments follow the scene image in the same order)."
        if crop_images
        else ". No cropped close-up images are available; rely solely on the scene image."
    )

    steps_prompt = f"""\
Initial goal: {analysis.goal}

You are given the original scene image (first attachment){attachment_note}
Use the initial goal, the object metadata, and any new evidence from the close-up crops to reason about the best final goal.

Objects:
{objects_summary}

If the initial goal already fits, repeat it verbatim. Otherwise, refine it to something more appropriate now that you have detailed context.
Produce an ordered list of detailed, clear, imperative manipulation steps that reference the object labels directly.
For each step set "object_label" to the single most relevant label taken verbatim from the list above.
Return JSON structured exactly as {{"goal": <final_goal>, "steps": [{{"text": <step_text>, "object_label": <object_label>}}, ...]}} with the goal field appearing before steps."""

    step_contents = [analysis_image, *resized_crop_images, steps_prompt]

    steps_text = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=step_contents,
        config=types.GenerateContentConfig(
            temperature=0.5,
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            response_mime_type="application/json",
            response_json_schema=StepsSchema.model_json_schema(),
        ),
    ).text

    assert steps_text is not None

    steps = StepsSchema.model_validate_json(steps_text)

    highlight_path = highlight_first_step(
        original_image, analysis.objects, steps.steps, FIRST_STEP_HIGHLIGHT_PATH
    )
    if highlight_path:
        print(f"Saved first-step bounding box visualization to {highlight_path}")
    else:
        print(
            "Skipped first-step bounding box visualization because no matching object was found for the first step."
        )

    banana_path: Optional[Path] = None
    first_step = steps.steps[0] if steps.steps else None
    if highlight_path and first_step:
        banana_path = banana(
            step_text=first_step.text,
            annotated_image_path=highlight_path,
            output_path=BANANA_OUTPUT_PATH,
        )
        if banana_path:
            print(f"Generated banana image for the first step at {banana_path}")
        else:
            print("Banana image generation failed.")
    elif first_step is None:
        print("Banana image generation skipped because no steps were returned.")
    else:
        print(
            "Banana image generation skipped because the first-step bounding box image was unavailable."
        )

    return OutputSchema(goal=steps.goal, objects=analysis.objects, steps=steps.steps)


if __name__ == "__main__":
    main()
