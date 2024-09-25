## Getting Started

This is based upon the bootstrapped version of [LlamaIndex](https://www.llamaindex.ai/) using [FastAPI](https://fastapi.tiangolo.com/) with a locally run LLM via Ollama.

First , go to `backend` and create an `.env` file with your environment variables, a sample setup can be found in `backend/.env-sample`.

Next, setup the environment with poetry:

```
poetry install
poetry shell
```

Put your data sources in the `backend/data` folder

Second, generate the embeddings of the documents in the `./data` directory:

```
poetry run generate
```

Third, run the development server:

```
python main.py
```

The example provides the API endpoint:

`/api/chat/request` - a non-streaming chat endpoint

You can use it via, e.g.:

```
curl --location 'localhost:8000/api/chat/request' \
--header 'Content-Type: application/json' \
--data '{ "messages": [{ "role": "user", "content": "Hello" }] }'
```

