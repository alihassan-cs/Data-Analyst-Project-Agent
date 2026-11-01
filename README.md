# Data Analyst Agent

Ask questions about CSV or database data in plain English. The agent writes read-only SQL, runs it, and
answers from the results. It shows the SQL it used and ships with a 30-question accuracy eval.

Works with Groq and Gemini (free tiers, for development) and Claude (paid, for final results).

## Setup
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env  -> then add your key(s)
```
Unzip the Kaggle "Brazilian E-Commerce Public Dataset by Olist" CSVs into `data/`.
(`olist_geolocation_dataset.csv` and `olist_order_reviews_dataset.csv` are skipped automatically.)

## Run
```bash
python test.py "How many orders are there?"          # one question
python test.py --provider gemini                     # interactive chat
streamlit run app.py                                 # web app
python evals/run_evals.py --provider groq --tag v1 --sleep 3
```

## Improve using the evals
1. Run the evals and note the score in `evals/history.csv` (tag `v1`).
2. Open the newest file in `evals/runs/` and read every FAIL: wrong join, wrong column, date logic, rounding?
3. Fix the cause: add facts to `data/notes.txt`, add examples to the prompt in `agent.py`, then re-run with `--tag v2`.
4. Run the final numbers on the model you ship (`--provider claude`).

## Safety design
- In-memory SQLite database with `PRAGMA query_only = ON` (the agent cannot write)
- Only a single SELECT / WITH query is accepted, 10 second timeout, results capped at 30 rows sent to the model
- Uploaded files are deleted from disk right after loading; logs contain questions, SQL and token counts, never data or answers
- Text inside data is treated as untrusted (prompt-injection rule in the system prompt)

## Deploy
- **Streamlit Community Cloud (free):** push to GitHub, deploy `app.py`. Do NOT add your own API keys to the
  deployment's secrets for a public demo, otherwise strangers spend your credit. Users paste their own key in the sidebar.
- **Docker:** `docker build -t data-agent .` then `docker run -p 8501:8501 data-agent`.
- Never send client data through a free-tier key.

## Results (fill in after your runs)
| Version | What changed | Provider / model | Accuracy | Cost per question |
|---|---|---|---|---|
| v1 | baseline | | | |
| v2 | | | | |
| v3 | | | | |

## Known failures (be honest here)

https://github.com/user-attachments/assets/b7c3d0f6-383e-49fe-97d0-9e345eda665c





-
