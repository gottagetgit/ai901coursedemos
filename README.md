# ai901coursedemos

Demos for my AI-901 course on Udemy. Each lesson has its own subdirectory with a `chatclient.py`, a `requirements.txt`, and a `config.env.example`. To run any demo:

1. `cd` into the lesson directory.
2. `pip install -r requirements.txt`
3. Copy `config.env.example` to `config.env` and fill in your values.
4. `python chatclient.py`

`config.env` is gitignored — your keys and endpoints stay local.

## [lesson4-2](lesson4-2/) — Chat client for a Foundry model

A simple interactive chat client that talks to a model deployed in Azure AI Foundry (e.g. DeepSeek-V3.2) via the OpenAI-compatible inference endpoint. The conversation history is kept locally and replayed on every turn, so the model sees the full context. Runs until you press Ctrl+C.

Config values: `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, `AZURE_FOUNDRY_MODEL`, optional `SYSTEM_PROMPT`.

## [lesson4-4](lesson4-4/) — Chat client for a Foundry agent

Same interactive chat experience, but instead of calling a raw model it invokes a published Azure AI Foundry **agent** (with its instructions, tools, and personality baked in). Uses `azure-ai-projects` to resolve the agent by name + version, then the OpenAI Responses API with `agent_reference` and `previous_response_id` to maintain conversation state on the service side. Authenticates via `DefaultAzureCredential` (your `az login` session).

Config values: `AZURE_FOUNDRY_ENDPOINT` (project endpoint), `AZURE_FOUNDRY_AGENT_NAME`, `AZURE_FOUNDRY_AGENT_VERSION`.

## [lesson5-3](lesson5-3/) — Live speech transcription

Captures audio from your default microphone and streams it to the Azure AI Foundry Speech service, printing both interim partial results and finalized phrases to the console in real time. Press Enter to stop.

Config values: `AZURE_SPEECH_ENDPOINT`, `AZURE_SPEECH_KEY`.
