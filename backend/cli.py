import os
from typing import List
from pydantic import BaseModel

import httpx
import typer
from rich.markdown import Markdown
from rich import print as rprint
from rich.live import Live


from dotenv import load_dotenv

load_dotenv()

app = typer.Typer()

class Message(BaseModel):
    role: str
    content: str

class MessageList(BaseModel):
    messages: List[Message]


def ask_question(messages: MessageList):
    url = f"http://localhost:{os.getenv("APP_PORT")}/api/chat"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "messages": messages
    }
    timeout = int(os.getenv("OLLAMA_REQUEST_TIMEOUT"))
    full_response = ""  # Store the full response text here

    try:
        with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
            with Live(auto_refresh=True) as live:  # Auto refresh updates terminal output dynamically
                for chunk in response.iter_text():
                    if chunk:
                        try:
                            if chunk[0] == "0": # Don't print out data response
                                data = chunk.strip().split(':')
                                if len(data) > 1:
                                    word = data[1].strip('"')
                                    # Decode unicode escape sequences
                                    decoded_word = word.encode().decode('unicode_escape')
                                    full_response += decoded_word  # Append the word to the full response
                                    # Print the decoded word with newlines handled properly
                                    markdown_content = Markdown(full_response)
                                    live.update(markdown_content)  # Update the live display with the new content
                        except ValueError:
                            pass
        print()
    except httpx.ReadTimeout:
        print('ReadTimeout: The server took too long to respond. Try increasing the REQUEST_TIMEOUT')
    except httpx.RequestError as exc:
        typer.echo(f"An error occurred while requesting: {exc}")


@app.command()
def chat():
    """Interactive session to ask multiple questions"""
    rprint("""✨ [bold]Hi, I'm your chat assistant allowing you to gain knowledge from your personal data.[/bold] ✨

Interactive chat session started. Type 'exit' or 'quit' to end.\n""")

    questions: MessageList = []

    while True:
        question = typer.prompt("✨ Ask your question")

        # If the user wants to exit
        if question.lower() in ["exit", "quit"]:
            typer.echo("Exiting chat session.")
            break

        questions.append({ "role": "user", "content": question })

        # Ask the question and stream the response
        ask_question(questions)

if __name__ == "__main__":
    app()
