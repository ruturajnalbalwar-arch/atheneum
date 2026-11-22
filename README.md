# Atheneum: a council of AI agents that debate before answering

You ask one question. Five Llama 3.3 70B agents work through it in five stages, and a chairman agent writes the final answer.

| Stage | What happens |
|---|---|
| 1. Independent opinions | The Logician, Scout, Maverick and Scholar answer separately, at temperatures 0.3, 0.5, 0.95 and 0.7 |
| 2. Cross-attack | Each agent critiques the other three answers |
| 3. Defence | Each agent defends and rewrites its own answer |
| 4. Blind peer ranking | All four rank the final answers under anonymised labels |
| 5. Chairman | An agent that took no part in the debate writes the answer and a confidence score from the rankings |

Each question takes 17 model calls. Agents within a stage run concurrently with `asyncio`, so a question takes about as long as five calls in a row. The calls are split between **Groq** and **Cerebras**, which both serve the same weights, so the agents differ by instruction and temperature, not by model. A failed call is retried 3 times, and the agent is then marked failed instead of crashing the run.

## Files

- [`app_complete.py`](app_complete.py): the general council, as a Gradio chat app with saved threads.
- [`paideia_app.py`](paideia_app.py): **Paideia**, a variant whose agents are educators and whose chairman is "The Mentor".
- [`website/`](website/index.html): the landing page, which links to the hosted councils on Hugging Face Spaces: [Hall of LLMs](https://klauz101-hall-of-llms.hf.space/), [Lex](https://klauz101-lex.hf.space/), [Medica](https://klauz101-medica.hf.space/) and [Paideia](https://klauz101-paideia.hf.space/).
- The evaluation harness, which tests whether the debate beats one model given the same compute, is in a separate repo: [LLM-Council-](https://github.com/ruturajnalbalwar-arch/LLM-Council-).

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env        # add GROQ_API_KEY and CEREBRAS_API_KEY (both have free tiers)
python app_complete.py
```

Setup details are in [`SETUP.md`](SETUP.md) and contribution notes in [`CONTRIBUTING.md`](CONTRIBUTING.md).
