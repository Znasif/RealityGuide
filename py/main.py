from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Tuple


class PointItem(BaseModel):
    point: Tuple[int, int] = Field(
        description="The normalized [y, x] coordinates, integers in the range 0–1000."
    )
    label: str = Field(description="A unique identifying label.")


class OutputSchema(BaseModel):
    points: List[PointItem] = Field(description="List of detected objects.")
    steps: List[str] = Field(description="List of steps.")


def main():
    client = genai.Client()

    with open("data/1.png", "rb") as f:
        image_bytes = f.read()

    prompt = """
Our goal is to move objects (umbrellas, water bottles, glasses) in order to group similar items together.

Identify and point to relevant objects located near the center of the image.
Each detected object must be assigned a unique identifying label, such as "green umbrella". The answer should follow the json format: [{"point": <point>, "label": <label1>}, ...]. The points are in [y, x] format normalized to 0-1000.

Next, generate steps that describe the actions needed to achieve the goal.
For example: "Move the sunglasses to the right side". The answer should follow the json format: [<step>, ...].
"""

    response = client.models.generate_content(
        model="gemini-robotics-er-1.5-preview",
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png",
            ),
            prompt,
        ],
        config=types.GenerateContentConfig(
            temperature=0.5,
            response_mime_type="application/json",
            response_json_schema=OutputSchema.model_json_schema(),
        ),
    ).text

    print(response)


if __name__ == "__main__":
    main()
