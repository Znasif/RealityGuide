from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Optional, Tuple
import re
from PIL import Image, ImageDraw


client = genai.Client()
OBJECT_CROP_DIR = Path("data/object_crops")
FIRST_STEP_HIGHLIGHT_PATH = Path("data/first_step_highlight.png")


class ObjectItem(BaseModel):
    label: str = Field(description="A unique identifying label.")
    box_2d: Tuple[int, int, int, int] = Field(
        description="Normalized [ymin, xmin, ymax, xmax] bounding box coordinates in the 0–1000 range."
    )


class AnalysisSchema(BaseModel):
    goal: str = Field(
        description="High-level natural language goal inferred from the image."
    )
    objects: List[ObjectItem] = Field(description="List of detected objects.")


class StepItem(BaseModel):
    text: str = Field(description="Detailed manipulation instruction.")
    object_label: str = Field(
        description="Label of the primary object mentioned in this step."
    )


class StepsSchema(BaseModel):
    goal: str = Field(
        description="Refined goal after reviewing the scene and cropped objects."
    )
    steps: List[StepItem] = Field(
        description="List of manipulation steps paired with object references."
    )


class OutputSchema(BaseModel):
    goal: str = Field(
        description="High-level natural language goal inferred from the image."
    )
    objects: List[ObjectItem] = Field(
        description="List of detected objects with bounding boxes."
    )
    steps: List[StepItem] = Field(
        description="List of steps paired with object references."
    )


def main():
    json = plan()
    print(json.model_dump_json(indent=2))
    # banana()


def plan():
    image_path = "data/2.jpg"
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

    print(steps_prompt)

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

    return OutputSchema(goal=steps.goal, objects=analysis.objects, steps=steps.steps)


def crop_and_save_objects(
    image: Image.Image, objects: List[ObjectItem], dest_dir: Path
) -> List[Tuple[ObjectItem, Image.Image, Path]]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    width, height = image.size
    assets: List[Tuple[ObjectItem, Image.Image, Path]] = []

    for idx, obj in enumerate(objects, start=1):
        x_min_px, y_min_px, x_max_px, y_max_px = normalized_box_to_pixels(
            obj.box_2d, width, height
        )

        crop = image.crop((x_min_px, y_min_px, x_max_px, y_max_px))
        crop_path = dest_dir / f"object_{idx}_{slugify_label(obj.label)}.png"
        crop.save(crop_path)
        assets.append((obj, crop, crop_path))

    return assets


def normalized_to_pixels(value: float, size: int) -> int:
    normalized = max(0.0, min(1000.0, float(value)))
    return int(round((normalized / 1000.0) * size))


def clamp(value: int, lower: int, upper: int) -> int:
    if lower > upper:
        return lower
    return max(lower, min(value, upper))


def slugify_label(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower())
    slug = slug.strip("_")
    return slug or "object"


def banana():
    prompt = """\
Using the provided image, apply the following action to the scene: "Move the regular glasses next to the sunglasses."

Modify only what is necessary to perform this action. Keep all other elements of the image exactly the same."""

    image = get_image_resized("data/1.png")

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt, image],
        config=types.GenerateContentConfig(response_modalities=["Image"]),
    )

    assert response.parts is not None

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            assert image is not None
            image.save("data/generated.png")


def get_image_resized(img_path: str):
    image = Image.open(img_path)
    return resize_image(image)


def resize_image(image: Image.Image, target_width: int = 1000) -> Image.Image:
    target_height = int(target_width * image.size[1] / image.size[0])
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def resize_images(
    images: List[Image.Image], target_width: int = 1000
) -> List[Image.Image]:
    return [resize_image(image, target_width) for image in images]


def normalized_box_to_pixels(
    box_2d: Tuple[int, int, int, int], width: int, height: int
) -> Tuple[int, int, int, int]:
    ymin, xmin, ymax, xmax = box_2d

    y_min_px = clamp(normalized_to_pixels(ymin, height), 0, max(height - 1, 0))
    y_max_px = clamp(normalized_to_pixels(ymax, height), 0, height)
    x_min_px = clamp(normalized_to_pixels(xmin, width), 0, max(width - 1, 0))
    x_max_px = clamp(normalized_to_pixels(xmax, width), 0, width)

    if y_max_px <= y_min_px:
        y_max_px = clamp(y_min_px + 1, 0, height)
    if x_max_px <= x_min_px:
        x_max_px = clamp(x_min_px + 1, 0, width)

    return x_min_px, y_min_px, x_max_px, y_max_px


def find_object_by_label(label: str, objects: List[ObjectItem]) -> Optional[ObjectItem]:
    normalized_target = label.strip().lower()
    if not normalized_target:
        return None

    for obj in objects:
        if obj.label.strip().lower() == normalized_target:
            return obj

    return None


def highlight_first_step(
    image: Image.Image,
    objects: List[ObjectItem],
    steps: List[StepItem],
    output_path: Path,
) -> Optional[Path]:
    if not steps:
        return None

    first_step = steps[0]
    target_object = find_object_by_label(first_step.object_label, objects)
    if target_object is None:
        return None

    annotated = image.copy()
    width, height = annotated.size
    x_min_px, y_min_px, x_max_px, y_max_px = normalized_box_to_pixels(
        target_object.box_2d, width, height
    )

    draw = ImageDraw.Draw(annotated)
    stroke_width = max(2, int(min(width, height) * 0.005))
    draw.rectangle(
        (x_min_px, y_min_px, x_max_px, y_max_px), outline="red", width=stroke_width
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(output_path)
    return output_path


if __name__ == "__main__":
    main()
