# ApplyForMe

ApplyForMe is an AI-powered Chrome extension and FastAPI backend for storing applicant profiles, matching job application fields, and generating contextual answers.

## Requirements

- Windows 10/11
- Python 3.11 or newer
- Node.js 18 or newer
- npm
- Google Chrome or Microsoft Edge
- MongoDB, optional for local development; the backend falls back to an in-memory database when MongoDB is unavailable

Optional for AI answers:

- Groq API access, or
- Ollama running locally with the `qwen2.5:3b` model

## 1. Configure the backend

Open PowerShell in the project root and create a Python virtual environment:

```powershell
cd "d:\chrome extension\Apply_for_me"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

Create the backend environment file if it does not already exist:

```powershell
Copy-Item backend\.env.example backend\.env
```

The default configuration works locally without MongoDB and uses an in-memory database. To persist data, run MongoDB locally or set a MongoDB Atlas URI in `backend/.env`:

```dotenv
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=applyforme
```

For Groq AI answers, add an API key to `backend/.env`:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b
```

For local Ollama instead:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

Install and start Ollama separately, then pull the model:

```powershell
ollama pull qwen2.5:3b
ollama serve
```

## 2. Start the backend

From the project root with the virtual environment active:

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`.

Useful URLs:

- Health check: http://localhost:8000/health
- Swagger docs: http://localhost:8000/docs
- Local test form: http://localhost:8000/test-form

## 3. Build and load the Chrome extension

In a second PowerShell window:

```powershell
cd "d:\chrome extension\Apply_for_me\extension"
npm install
npm run build
```

Then:

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the extension's `dist` folder:
   `d:\chrome extension\Apply_for_me\extension\dist`

Keep the backend running while using the extension. The extension uses `http://localhost:8000/api` by default.

## Development mode

For React dashboard and popup development with Vite:

```powershell
cd extension
npm run dev
```

The content script and Chrome service worker are primarily verified through a production build loaded in Chrome.

## Docker backend

The backend can also run in Docker:

```powershell
docker build -t applyforme-backend backend
docker run --rm -p 8000:8000 --env-file backend\.env applyforme-backend
```

MongoDB is not included by the Docker command above. Either provide an Atlas/local accessible URI in `backend/.env`, or run MongoDB separately.

## Run tests

With the virtual environment active:

```powershell
cd backend
pytest -q
```

To check the built extension for TypeScript and bundling issues:

```powershell
cd extension
npm run build
```

## Common configuration

Backend settings are read from `backend/.env`. The main options are:

| Setting | Purpose | Default |
| --- | --- | --- |
| `APP_ENV` | Application environment | `development` |
| `MONGODB_URL` | MongoDB or Atlas connection URI | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | MongoDB database name | `applyforme` |
| `LLM_PROVIDER` | `groq` or `ollama` | `groq` |
| `GROQ_API_KEY` | Groq authentication key | Empty |
| `OLLAMA_BASE_URL` | Local Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `qwen2.5:3b` |
| `JWT_SECRET_KEY` | Backend authentication signing key | Development key |

For production, replace the JWT secret, restrict CORS origins, and use a persistent MongoDB connection.
