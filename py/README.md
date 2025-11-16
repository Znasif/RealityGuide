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

## HTTP API

RealityGuide can also run as a FastAPI service that mirrors the CLI behavior.

1. Ensure `.env` contains `GEMINI_API_KEY`, then start the server:
   ```
   uv run --env-file .env fastapi dev server.py
   ```
2. Send requests by POSTing base64-encoded images to the API. The helper script wraps this for you:
   ```
   uv run python api_client.py sample/1.jpg
   ```
   Re-run the script with `--goal-id <returned_id>` to call the continuation flow (HTTP `PUT`).

### Endpoints

- `POST /goals`
  - Body: `{ "image_base64": "..." }`
  - Action: runs the initial planning workflow, stores the resulting JSON in `goals/{id}.json`, and returns `{ id, plan, highlight_image_base64, banana_image_base64 }`.
- `PUT /goals/{id}`
  - Body: `{ "image_base64": "..." }`
  - Action: loads the saved plan for `id`, evaluates progress against the new photo, updates the stored JSON, and returns the same response structure.

`highlight_image_base64` and `banana_image_base64` may be `null` when no artifact was produced. All image payloads may optionally use the `data:image/...;base64,` prefix.

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

**Next Command**:
```
uv run --env-file .env check_completion.py new-state-image.jpg current.json
```

**Next Output Image**:

<img src="https://github.com/user-attachments/assets/cebbd5a4-7203-4bc4-8532-fd58d5869b4d" width="400" />
