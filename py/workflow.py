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
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
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
    print(completion_prompt)

    completion_text = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=[resized_image, completion_prompt],
        config=types.GenerateContentConfig(
            temperature=0.5,
            thinking_config=types.ThinkingConfig(thinking_budget=512),
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
Mission: group functionally similar objects together.

Return JSON exactly as {"goal": <goal>, "objects": [{"label": <label>, "box_2d": [ymin, xmin, ymax, xmax]}, ...], "steps": [{"text": <instruction>, "object_label": <object_label>, "trajectory": [{"point": [y, x]}, ...]}, ...]}.

- goal: always set to "Group functionally similar objects together."
- objects: list every relevant item with a unique label and normalized integer box [ymin, xmin, ymax, xmax] spanning 0–1000.
- steps: write a short imperative that moves one object toward its matching group, referencing the label verbatim. Only the first step may include up to 5 normalized [y, x] waypoint pairs as trajectory moving towards destination.
"""


def _build_completion_prompt(existing: OutputSchema) -> str:
    return f"""\
You previously generated a plan for a robot and are now checking progress.
Goal (repeat verbatim in the output): {existing.goal}

Objects reference list:
{summarize_objects(existing.objects)}

Prior ordered steps:
{summarize_steps(existing.steps)}

Review the new image and update the plan while keeping the same mission.

Objects:
- Follow the reference order above.
- Give each label a normalized [ymin, xmin, ymax, xmax] box (0–1000 integers) or null if hidden.

Steps:
- Keep every object_label exactly the same as before.
- Completed steps: prefix with "[DONE] " and keep the remaining text short.
- Preserve ordering and append new steps only if more actions are still needed, using existing labels only.
- Provide trajectory waypoints only for the first step that is not prefixed with "[DONE]"; use up to 5 normalized [y, x] pairs. Set trajectory to [] for all other steps.

Return JSON structured exactly as {{"goal": <goal>, "objects": [{{"label": <label>, "box_2d": [ymin, xmin, ymax, xmax] or null}}, ...], "steps": [{{"text": <step>, "object_label": <label>, "trajectory": [{{"point": [y, x]}}, ...]}}, ...]}}.
The "goal" field MUST be exactly: {existing.goal}
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
