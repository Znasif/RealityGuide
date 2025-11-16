import re
from pathlib import Path
from typing import List, Optional, Tuple

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw


client = genai.Client()

OBJECT_CROP_DIR = Path("data/object_crops")
FIRST_STEP_HIGHLIGHT_PATH = Path("data/first_step_highlight.png")
BANANA_OUTPUT_PATH = Path("data/first_step_banana.png")
CONTINUATION_HIGHLIGHT_PATH = Path("data/continuation_first_step_highlight.png")
CONTINUATION_BANANA_PATH = Path("data/continuation_first_step_banana.png")


class ObjectItem(BaseModel):
    label: str = Field(description="A unique identifying label.")
    box_2d: Optional[Tuple[int, int, int, int]] = Field(
        description="Normalized [ymin, xmin, ymax, xmax] bounding box coordinates in the 0–1000 range, or null when the object is not visible."
    )


class AnalysisSchema(BaseModel):
    goal: str = Field(
        description="High-level natural language goal inferred from the image."
    )
    objects: List[ObjectItem] = Field(description="List of detected objects.")


class TrajectoryPoint(BaseModel):
    point: Tuple[int, int] = Field(
        description="Normalized [y, x] waypoint in the 0–1000 range."
    )


class StepItem(BaseModel):
    text: str = Field(description="Detailed manipulation instruction.")
    object_label: str = Field(
        description="Label of the primary object mentioned in this step."
    )
    trajectory: Optional[List[TrajectoryPoint]] = Field(
        default=None,
        max_length=10,
        description="Optional path for moving the object, expressed as up to 10 normalized [y, x] points.",
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


def resize_image(image: Image.Image, target_width: int = 1600) -> Image.Image:
    target_height = int(target_width * image.size[1] / image.size[0])
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def resize_images(
    images: List[Image.Image], target_width: int = 1000
) -> List[Image.Image]:
    return [resize_image(image, target_width) for image in images]


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


def normalized_box_to_pixel_box(
    box_2d: Tuple[int, int, int, int], width: int, height: int
) -> Tuple[int, int, int, int]:
    x_min_px, y_min_px, x_max_px, y_max_px = normalized_box_to_pixels(
        box_2d, width, height
    )
    return y_min_px, x_min_px, y_max_px, x_max_px


def normalized_point_to_pixels(
    point: Tuple[int, int], width: int, height: int
) -> Tuple[int, int]:
    y_normalized, x_normalized = point
    y_px = clamp(normalized_to_pixels(y_normalized, height), 0, height)
    x_px = clamp(normalized_to_pixels(x_normalized, width), 0, width)
    return x_px, y_px


def objects_with_pixel_boxes(
    objects: List[ObjectItem], width: int, height: int
) -> List[ObjectItem]:
    return [
        ObjectItem(
            label=obj.label,
            box_2d=(
                normalized_box_to_pixel_box(obj.box_2d, width, height)
                if obj.box_2d is not None
                else None
            ),
        )
        for obj in objects
    ]


def output_with_pixel_boxes(
    output: OutputSchema, width: int, height: int
) -> OutputSchema:
    pixel_objects = objects_with_pixel_boxes(output.objects, width, height)
    pixel_steps = [step.model_copy(deep=True) for step in output.steps]
    return OutputSchema(goal=output.goal, objects=pixel_objects, steps=pixel_steps)


def crop_and_save_objects(
    image: Image.Image, objects: List[ObjectItem], dest_dir: Path
) -> List[Tuple[ObjectItem, Image.Image, Path]]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    width, height = image.size
    assets: List[Tuple[ObjectItem, Image.Image, Path]] = []

    crop_index = 0
    for obj in objects:
        if obj.box_2d is None:
            continue
        crop_index += 1
        x_min_px, y_min_px, x_max_px, y_max_px = normalized_box_to_pixels(
            obj.box_2d, width, height
        )

        crop = image.crop((x_min_px, y_min_px, x_max_px, y_max_px))
        crop_path = dest_dir / f"object_{crop_index}_{slugify_label(obj.label)}.png"
        crop.save(crop_path)
        assets.append((obj, crop, crop_path))

    return assets


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
    if target_object is None or target_object.box_2d is None:
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

    trajectory_points = []
    if first_step.trajectory:
        for point in first_step.trajectory[:10]:
            if point.point is None:
                continue
            x_px, y_px = normalized_point_to_pixels(point.point, width, height)
            trajectory_points.append((x_px, y_px))

    if trajectory_points:
        draw.line(trajectory_points, fill="yellow", width=stroke_width)
        marker_radius = max(2, stroke_width)
        for idx, (x, y) in enumerate(trajectory_points):
            marker_color = "yellow" if idx == len(trajectory_points) - 1 else "orange"
            draw.ellipse(
                (
                    x - marker_radius,
                    y - marker_radius,
                    x + marker_radius,
                    y + marker_radius,
                ),
                outline="black",
                fill=marker_color,
                width=1,
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(output_path)
    return output_path


def banana(
    step_text: str, annotated_image_path: Path, output_path: Path
) -> Optional[Path]:
    prompt = f"""\
Using the provided image, apply the following: {step_text}."""

    with Image.open(annotated_image_path) as annotated_image:
        image = resize_image(annotated_image)

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt, image],
        config=types.GenerateContentConfig(response_modalities=["Image"]),
    )

    if response.parts is None:
        return None

    for part in response.parts:
        if part.inline_data is None:
            continue
        generated = part.as_image()
        if generated is None:
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generated.save(str(output_path))
        return output_path

    return None
