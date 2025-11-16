## Overview

This project helps a person understand what to do from a single photo. It describes the goal, lists the objects that matter, shows the first action with an AI-generated supporting visual, and produces a simple checklist. After that person makes progress, it reviews a new photo, marks what's done, updates the remaining steps, and highlights what should happen next.

## How to use

- Install dependencies: `uv sync`
- Create a `.env` file:

```
GEMINI_API_KEY='FIXME'
```

- Run the program (specify an image path): `uv run --env-file .env main.py sample/1.jpg`

Learn more about the project: [AGENTS.md](AGENTS.md)

## Example result

**Command**:
```
uv run --env-file .env main.py sample/1.jpg
```

**Input Image**:

<img src="sample/1.jpg" width="400" />

**Output Image**:

<img src="https://github.com/user-attachments/assets/91be5d22-854a-48fe-b203-d73249ab1370" width="400" />

**Output JSON**:

```json
{
  "goal": "Prepare and heat the food package in the microwave.",
  "objects": [
    {
      "label": "food package",
      "box_2d": [
        454,
        477,
        740,
        659
      ]
    },
    {
      "label": "microwave",
      "box_2d": [
        147,
        199,
        628,
        750
      ]
    },
    {
      "label": "hand",
      "box_2d": [
        596,
        508,
        996,
        999
      ]
    }
  ],
  "steps": [
    {
      "text": "Tear the food package pouch at the top to vent as instructed.",
      "object_label": "food package"
    },
    {
      "text": "Open the microwave door.",
      "object_label": "microwave"
    },
    {
      "text": "Place the food package inside the microwave.",
      "object_label": "food package"
    },
    {
      "text": "Close the microwave door.",
      "object_label": "microwave"
    },
    {
      "text": "Set the microwave to heat for 1 minute.",
      "object_label": "microwave"
    },
    {
      "text": "Press start to begin heating.",
      "object_label": "microwave"
    }
  ]
}
```
