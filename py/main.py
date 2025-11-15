from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Tuple
import textwrap
from PIL import Image


client = genai.Client()


def main():
    # json = plan()
    # print(json.model_dump_json(indent=2))
    banana()


def plan():
    class PointItem(BaseModel):
        point: Tuple[int, int] = Field(
            description="The normalized [y, x] coordinates, integers in the range 0–1000."
        )
        label: str = Field(description="A unique identifying label.")

    class OutputSchema(BaseModel):
        points: List[PointItem] = Field(description="List of detected objects.")
        steps: List[str] = Field(description="List of steps.")

    image = get_image_resized("data/1.png")

    prompt = textwrap.dedent("""\
        Our goal is to move objects (umbrellas, water bottles, glasses) in order to group similar items together.

        Identify and point to relevant objects located near the center of the image.
        Each detected object must be assigned a unique identifying label, such as "green umbrella". The answer should follow the json format: [{"point": <point>, "label": <label1>}, ...]. The points are in [y, x] format normalized to 0-1000.

        Next, generate steps that describe the actions needed to achieve the goal.
        For example: "Move the sunglasses to the right side". The answer should follow the json format: [<step>, ...].""")

    text = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=[
            image,
            prompt,
        ],
        config=types.GenerateContentConfig(
            temperature=0.5,
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1
            ),  # dynamic thinking
            response_mime_type="application/json",
            response_json_schema=OutputSchema.model_json_schema(),
        ),
    ).text

    assert text is not None

    json = OutputSchema.model_validate_json(text)

    return json


def banana():
    prompt = textwrap.dedent("""\
        Using the provided image, apply the following action to the scene: "Move the regular glasses next to the sunglasses."

        Modify only what is necessary to perform this action. Keep all other elements of the image exactly the same.""")

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
    image = image.resize(
        (800, int(800 * image.size[1] / image.size[0])), Image.Resampling.LANCZOS
    )
    return image


if __name__ == "__main__":
    main()
