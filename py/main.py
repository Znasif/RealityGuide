from google import genai


def main():
    client = genai.Client()

    print(
        client.models.generate_content(
            model="gemini-robotics-er-1.5-preview", contents="Are you there?"
        ).text
    )


if __name__ == "__main__":
    main()
