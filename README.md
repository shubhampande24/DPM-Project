# Duel Mind AI (MVP)

A Skeptic agent and a Champion agent debate a startup pitch. A Judge agent turns the debate into a ranked list of hidden unit economics and execution risks, with a Go / Conditional Go / No-Go call.

Built for the Digital Product Management course, Group 5.

## Scope of this MVP

- One user: an early-stage founder
- One problem: hidden risks in unit economics and execution
- One workflow: fill the pitch form, run the debate, read the risk memo
- One AI capability: adversarial multi-agent risk analysis
- No login, no database, nothing is stored

## Files

- `app.py` : the whole app
- `requirements.txt` : the two libraries it needs

## Step 1: Get a free Gemini API key

1. Open https://aistudio.google.com and sign in with a Google account.
2. Click "Get API key", then "Create API key".
3. Copy the key and keep it private. Never paste it into a file on GitHub.

## Step 2: Put the code on GitHub (no installs needed)

1. Create a free account at https://github.com.
2. Click the "+" at the top right, then "New repository". Name it `duel-mind-ai`, set it to Public, and click "Create repository".
3. Click "uploading an existing file", drag in `app.py`, `requirements.txt` and `README.md`, then click "Commit changes".

## Step 3: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click "Create app", then choose your `duel-mind-ai` repository.
3. Set the branch to `main` and the main file path to `app.py`.
4. Open "Advanced settings". In the Secrets box paste this, with your real key:

```
GEMINI_API_KEY = "paste-your-key-here"
```

5. Click "Deploy". After a minute or two you get a public link ending in `.streamlit.app`. Put this link in the slides.

## Optional: run it locally in VS Code

```
pip install -r requirements.txt
```

Create a folder named `.streamlit` next to `app.py`, and inside it a file named `secrets.toml` containing the same GEMINI_API_KEY line as above. Then run:

```
streamlit run app.py
```

## If something breaks

- "No Gemini API key found": the secret was not saved. Re-open Settings, then Secrets, and paste it again.
- A model not found error: Google may have renamed the model. Add `GEMINI_MODEL = "gemini-3.8-flash"` to the secrets, replacing the name with a current one listed in Google AI Studio. The error message from Google usually names the model it wants you to use.
- A quota or rate limit error: wait a minute and run it again. The free tier has limits.
- The Judge returns a format error: click "Run the debate" again.

## Privacy

The app stores nothing. Pitch text is sent to the Gemini API to generate the analysis. Do not enter confidential or personal information. Do not commit your API key to GitHub.
