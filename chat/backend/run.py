import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("CHAT_HOST", "0.0.0.0"),
        port=int(os.environ.get("CHAT_PORT", "5002")),
    )
