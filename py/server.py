import base64
import binascii
import re
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError

from shared import OutputSchema, output_with_pixel_boxes
from workflow import (
    WorkflowArtifacts,
    actionable_steps,
    generate_plan_from_image,
    refresh_plan_from_image,
)


app = FastAPI(title="RealityGuide API")

GOALS_DIR = Path("goals")
DATA_DIR = Path("data")
LATEST_TMP_IMAGE_PATH = DATA_DIR / "latest_root_request.png"
LATEST_GOALS_IMAGE_PATH = DATA_DIR / "latest_goals_request.png"
LATEST_GOALS_UPDATE_IMAGE_PATH = DATA_DIR / "latest_goals_update_request.png"
GOAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class GoalImageRequest(BaseModel):
    image_base64: str


class GoalResponse(BaseModel):
    id: str
    plan: OutputSchema
    highlight_image_base64: Optional[str]
    banana_image_base64: Optional[str]


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


# FIXME: copied from create_goal()
@app.post("/", response_model=GoalResponse)
def tmp(payload: GoalImageRequest) -> GoalResponse:
    image = _decode_base64_image(payload.image_base64)
    _save_latest_image(image, LATEST_TMP_IMAGE_PATH)
    artifacts = generate_plan_from_image(image)
    goal_id = uuid4().hex
    print(goal_id)
    _persist_goal(goal_id, artifacts.output)
    return _build_response(goal_id, artifacts, image.size)


@app.post("/goals", response_model=GoalResponse)
def create_goal(payload: GoalImageRequest) -> GoalResponse:
    image = _decode_base64_image(payload.image_base64)
    _save_latest_image(image, LATEST_GOALS_IMAGE_PATH)
    artifacts = generate_plan_from_image(image)
    goal_id = uuid4().hex
    print(goal_id)
    _persist_goal(goal_id, artifacts.output)
    return _build_response(goal_id, artifacts, image.size)


@app.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: str, payload: GoalImageRequest) -> GoalResponse:
    goal_path = _goal_path(goal_id)
    if not goal_path.exists():
        raise HTTPException(status_code=404, detail="Goal not found.")

    existing = OutputSchema.model_validate_json(goal_path.read_text())
    image = _decode_base64_image(payload.image_base64)
    _save_latest_image(image, LATEST_GOALS_UPDATE_IMAGE_PATH)
    artifacts = refresh_plan_from_image(image, existing)
    _persist_goal(goal_id, artifacts.output)
    return _build_response(goal_id, artifacts, image.size)


def _decode_base64_image(data: str) -> Image.Image:
    raw = _strip_data_url_prefix(data.strip())
    try:
        binary = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Invalid base64 image data."
        ) from exc

    try:
        with Image.open(BytesIO(binary)) as image:
            return image.convert("RGB").copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image payload.") from exc


def _strip_data_url_prefix(data: str) -> str:
    if data.lower().startswith("data:") and "," in data:
        return data.split(",", 1)[1]
    return data


def _persist_goal(goal_id: str, plan: OutputSchema) -> Path:
    path = _goal_path(goal_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2))
    return path


def _goal_path(goal_id: str) -> Path:
    sanitized = goal_id.strip()
    if not GOAL_ID_PATTERN.fullmatch(sanitized):
        raise HTTPException(status_code=400, detail="Invalid goal id format.")
    return GOALS_DIR / f"{sanitized}.json"


def _build_response(
    goal_id: str, artifacts: WorkflowArtifacts, image_size: tuple[int, int]
) -> GoalResponse:
    width, height = image_size
    pixel_aligned_output = output_with_pixel_boxes(
        artifacts.output, width=width, height=height
    )
    actionable_plan = OutputSchema(
        goal=pixel_aligned_output.goal,
        objects=pixel_aligned_output.objects,
        steps=actionable_steps(pixel_aligned_output.steps),
    )
    return GoalResponse(
        id=goal_id,
        plan=actionable_plan,
        highlight_image_base64=_encode_file_as_base64(artifacts.highlight_path),
        banana_image_base64=_encode_file_as_base64(artifacts.banana_path),
    )


def _encode_file_as_base64(path: Optional[Path]) -> Optional[str]:
    if not path or not path.is_file():
        return None
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _save_latest_image(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")
