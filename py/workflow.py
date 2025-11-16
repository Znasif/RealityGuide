from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from google.genai import types
from PIL import Image

from shared import (
    CONTINUATION_HIGHLIGHT_PATH,
    FIRST_STEP_HIGHLIGHT_PATH,
    ObjectItem,
    OutputSchema,
    StepItem,
    banana,
    client,
    highlight_first_step,
    resize_image,
)


@dataclass
class WorkflowArtifacts:
    """Represents the structured output plus any generated imagery paths."""

    output: OutputSchema
    highlight_path: Optional[Path]
    banana_path: Optional[Path]


def generate_plan_from_image(image: Image.Image) -> WorkflowArtifacts:
    original_image = image.copy()
    resized_image = resize_image(original_image)

    plan_text = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=[resized_image, PLAN_PROMPT],
        config=types.GenerateContentConfig(
            temperature=0.5,
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            response_mime_type="application/json",
            response_json_schema=OutputSchema.model_json_schema(),
        ),
    ).text

    if plan_text is None:
        raise RuntimeError("Plan model did not return any content.")

    plan = OutputSchema.model_validate_json(plan_text)

    highlight_path = highlight_first_step(
        original_image, plan.objects, plan.steps, FIRST_STEP_HIGHLIGHT_PATH
    )

    return WorkflowArtifacts(
        output=plan, highlight_path=highlight_path, banana_path=highlight_path
    )


def refresh_plan_from_image(
    image: Image.Image, existing: OutputSchema
) -> WorkflowArtifacts:
    current_image = image.copy()
    resized_image = resize_image(current_image)

    completion_prompt = _build_completion_prompt(existing)

    completion_text = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=[resized_image, completion_prompt],
        config=types.GenerateContentConfig(
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            response_mime_type="application/json",
            response_json_schema=OutputSchema.model_json_schema(),
        ),
    ).text

    if completion_text is None:
        raise RuntimeError("Completion model did not return any content.")

    completion = OutputSchema.model_validate_json(completion_text)

    merged_objects = merge_objects_by_label(existing.objects, completion.objects)

    updated_output = OutputSchema(
        goal=existing.goal,
        objects=merged_objects,
        steps=completion.steps,
    )

    remaining_steps = actionable_steps(updated_output.steps)
    highlight_path = highlight_first_step(
        current_image,
        updated_output.objects,
        remaining_steps,
        CONTINUATION_HIGHLIGHT_PATH,
    )

    return WorkflowArtifacts(
        output=updated_output, highlight_path=highlight_path, banana_path=highlight_path
    )


def actionable_steps(steps: List[StepItem]) -> List[StepItem]:
    result: List[StepItem] = []
    for step in steps:
        text = step.text.lstrip()
        if text.upper().startswith("[DONE]"):
            continue
        result.append(step)
    return result


def summarize_objects(objects: Sequence[ObjectItem]) -> str:
    if not objects:
        return "No objects were provided."

    return "\n".join(f"{idx}. {obj.label}" for idx, obj in enumerate(objects, start=1))


def summarize_steps(steps: Sequence[StepItem]) -> str:
    if not steps:
        return "(No previous steps. You may generate a fresh ordered list.)"

    return "\n".join(
        f"{idx}. {step.text} (object_label: {step.object_label})"
        for idx, step in enumerate(steps, start=1)
    )


def merge_objects_by_label(
    reference_objects: Sequence[ObjectItem],
    updated_objects: Sequence[ObjectItem],
) -> List[ObjectItem]:
    lookup: Dict[str, ObjectItem] = {}
    for obj in updated_objects:
        key = obj.label.strip().lower()
        if not key:
            continue
        lookup.setdefault(key, obj)

    merged: List[ObjectItem] = []
    for obj in reference_objects:
        key = obj.label.strip().lower()
        match = lookup.get(key)
        merged.append(
            ObjectItem(
                label=obj.label,
                box_2d=match.box_2d if match else None,
            )
        )

    return merged


PLAN_PROMPT = """\
Inspect the provided image and infer a single high-level goal that describes reorganizing the scene by grouping visually or functionally similar objects together. The robot should move matching items closer so that related things form tidy clusters.

Goal instructions:
- Express the goal as a short imperative sentence that explicitly mentions organizing or grouping similar items based solely on the visual evidence.

Objects instructions:
- Identify every object that matters for forming the groups and assign each one a unique label.
- Represent bounding boxes using normalized integer coordinates spanning 0–1000 in [ymin, xmin, ymax, xmax] format.

Steps instructions:
- Produce an ordered list of clear, imperative manipulation steps that move objects into proximity with the similar items they belong with.
- Reference objects directly in each step and set object_label to one of the previously listed labels verbatim.
- For every step, include "trajectory": [{"point": [y, x]}, ...] describing up to 10 normalized waypoint pairs (0–1000 integers) charting the motion path toward the destination cluster. Use an empty array when no motion is required.

Return JSON structured exactly as {"goal": <goal>, "objects": [{"label": <label>, "box_2d": [ymin, xmin, ymax, xmax]}, ...], "steps": [{"text": <instruction>, "object_label": <object_label>, "trajectory": [{"point": [y, x]}, ...]}, ...]}.
"""


def _build_completion_prompt(existing: OutputSchema) -> str:
    return f"""\
You previously generated a plan for a robot and are now checking progress.
Goal (repeat verbatim in the output): {existing.goal}

Objects reference list:
{summarize_objects(existing.objects)}

Prior ordered steps:
{summarize_steps(existing.steps)}

Look at the updated scene image (attachment) and determine which steps have been completed.
Keep the reorganizing task focused on consolidating similar objects into tidy clusters by moving matching items closer together.
Objects instructions:
- For each label above (and in the same order), inspect the latest image and provide its bounding box as normalized integers in [ymin, xmin, ymax, xmax] format spanning 0–1000.
- Do not introduce new labels or reorder them. When an object is not visible, set its box_2d to null.

Steps instructions:
- For each existing step, keep its object_label identical.
- When a step is fully satisfied, prefix its text with "[DONE] " but keep the rest of the wording.
- For steps that still require work, rewrite the text so it reflects what remains.
- Maintain the execution order from top to bottom so the robot knows what to do next.
- Add new steps at the end only if more actions are required to finish the unchanged goal. Use an object_label from the reference list; never invent new labels.
- Provide "trajectory": [{{"point": [y, x]}}, ...] for every step, using up to 10 normalized waypoint pairs (0–1000 integers) that describe how to move the object toward its intended group. Use an empty array when a step is already satisfied or requires no additional motion.

Return JSON structured exactly as {{"goal": <goal>, "objects": [{{"label": <label>, "box_2d": [ymin, xmin, ymax, xmax] or null}}, ...], "steps": [{{"text": <step>, "object_label": <label>, "trajectory": [{{"point": [y, x]}}, ...]}}, ...]}} with the goal field appearing before objects.
The "goal" field MUST be exactly: {existing.goal}

If no steps were provided previously, create a fresh ordered list that the robot can follow from the current state to finish the goal.
"""


def _generate_banana_asset(
    steps: Sequence[StepItem],
    highlight_path: Optional[Path],
    output_path: Path,
) -> Optional[Path]:
    first_step = steps[0] if steps else None
    if highlight_path and first_step:
        return banana(
            step_text=first_step.text,
            annotated_image_path=highlight_path,
            output_path=output_path,
        )
    return None
