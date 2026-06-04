import os, re, json, time, asyncio
from datetime import datetime
from collections import Counter, defaultdict
from groq import AsyncGroq, Groq
from openai import AsyncOpenAI, OpenAI
import gradio as gr
import nest_asyncio
nest_asyncio.apply()

# ── API KEYS ──────────────────────────────────────────────────────────────────
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
if GROQ_API_KEY:     os.environ["GROQ_API_KEY"]     = GROQ_API_KEY
if CEREBRAS_API_KEY: os.environ["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

# ── MODEL NAMES ───────────────────────────────────────────────────────────────
MODEL_70B      = "llama-3.3-70b-versatile"
MODEL_CEREBRAS = "llama-3.3-70b"

# ── COUNCIL CONFIGURATION ─────────────────────────────────────────────────────
COUNCIL = [
    {
        "id": "logician",
        "name": "The Logician",
        "emoji": "🧠",
        "provider": "groq",
        "model": MODEL_70B,
        "temperature": 0.3,
        "personality": (
            "You are The Logician. Ruthlessly precise and analytical. "
            "Build arguments from first principles. Take clear bold positions. "
            "When others are wrong say so directly and explain why. Never hedge."
        )
    },
    {
        "id": "scout",
        "name": "The Scout",
        "emoji": "🔍",
        "provider": "groq",
        "model": MODEL_70B,
        "temperature": 0.5,
        "personality": (
            "You are The Scout. Grounded in real-world facts and practical outcomes. "
            "Distrust theory that does not hold in practice. "
            "Cite specific examples. Call out oversimplification directly."
        )
    },
    {
        "id": "maverick",
        "name": "The Maverick",
        "emoji": "🔥",
        "provider": "cerebras",
        "model": MODEL_CEREBRAS,
        "temperature": 0.95,
        "personality": (
            "You are The Maverick. A bold contrarian who challenges all consensus. "
            "Find what everyone else misses. "
            "If others agree you MUST find a strong reason to disagree. "
            "Be provocative and direct."
        )
    },
    {
        "id": "scholar",
        "name": "The Scholar",
        "emoji": "📚",
        "provider": "cerebras",
        "model": MODEL_CEREBRAS,
        "temperature": 0.7,
        "personality": (
            "You are The Scholar. Encyclopedic and cross-disciplinary. "
            "Bring perspectives others miss. "
            "Find the counterexample that destroys a seemingly solid argument. "
            "Never let incorrect claims stand."
        )
    },
]

CHAIRMAN = {
    "id": "chairman",
    "name": "The Chairman",
    "emoji": "⚖️",
    "provider": "groq",
    "model": MODEL_70B,
    "temperature": 0.4,
    "personality": (
        "You are the Chairman of an elite council. "
        "Impartial, wise, analytical. "
        "Synthesize the strongest insights. "
        "Give clear complete well-structured answers that are directly useful."
    )
}

# ── API CALLERS ───────────────────────────────────────────────────────────────

async def call_groq(model, system, user, temperature, max_tokens):
    client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content


async def call_cerebras(model, system, user, temperature, max_tokens):
    client = AsyncOpenAI(
        api_key=os.environ["CEREBRAS_API_KEY"],
        base_url="https://api.cerebras.ai/v1"
    )
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content


async def call_model(member, system, user, max_tokens=350):
    temperature = member.get("temperature", 0.7)
    for attempt in range(3):
        try:
            if member["provider"] == "groq":
                return await call_groq(member["model"], system, user, temperature, max_tokens)
            else:
                return await call_cerebras(member["model"], system, user, temperature, max_tokens)
        except Exception as e:
            err = str(e).lower()
            if "rate limit" in err or "429" in err:
                wait = (attempt + 1) * 8
                await asyncio.sleep(wait)
            else:
                return f"[{member['name']} failed: {str(e)[:80]}]"
    return f"[{member['name']} failed after 3 attempts]"


def stream_chairman(system, user, max_tokens=2000):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    stream = client.chat.completions.create(
        model=CHAIRMAN["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        temperature=CHAIRMAN["temperature"],
        max_tokens=max_tokens,
        stream=True
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield token

# ── STAGE 1 — INDEPENDENT OPINIONS ───────────────────────────────────────────

async def stage1(question):
    prompt = (
        f"Question: {question}\n\n"
        "Give your best answer. Take a clear position. "
        "Be specific. LIMIT: 150 words."
    )
    tasks = [call_model(m, m["personality"], prompt, 250) for m in COUNCIL]
    responses = await asyncio.gather(*tasks)
    return [
        {
            "id":       COUNCIL[i]["id"],
            "name":     COUNCIL[i]["name"],
            "emoji":    COUNCIL[i]["emoji"],
            "response": responses[i]
        }
        for i in range(len(COUNCIL))
    ]

# ── STAGE 2 — CROSS ATTACK ────────────────────────────────────────────────────

async def stage2(question, s1):
    def build_prompt(mid):
        my     = next(r["response"] for r in s1 if r["id"] == mid)
        others = "\n\n".join([
            f"{r['emoji']} {r['name']}:\n{r['response']}"
            for r in s1 if r["id"] != mid
        ])
        return (
            f"Question: {question}\n\n"
            f"Your answer:\n{my}\n\n"
            f"Others said:\n{others}\n\n"
            "Attack the other answers. Find specific flaws. "
            "Explain why your position is stronger. LIMIT: 150 words."
        )

    debate_sys = lambda m: (
        m["personality"] +
        " You are in a debate. Disagree with at least 2 others specifically."
    )
    tasks = [call_model(m, debate_sys(m), build_prompt(m["id"]), 250) for m in COUNCIL]
    responses = await asyncio.gather(*tasks)
    return [
        {
            "id":       COUNCIL[i]["id"],
            "name":     COUNCIL[i]["name"],
            "emoji":    COUNCIL[i]["emoji"],
            "response": responses[i]
        }
        for i in range(len(COUNCIL))
    ]

# ── STAGE 3 — DEFENSE ─────────────────────────────────────────────────────────

async def stage3(question, s1, s2):
    def build_prompt(mid):
        my      = next(r["response"] for r in s1 if r["id"] == mid)
        attacks = "\n\n".join([
            f"{r['emoji']} {r['name']} attacked you:\n{r['response']}"
            for r in s2 if r["id"] != mid
        ])
        return (
            f"Question: {question}\n\n"
            f"Your original answer:\n{my}\n\n"
            f"Attacks against you:\n{attacks}\n\n"
            "Defend what holds. Concede valid points. "
            "Write your FINAL answer. LIMIT: 150 words."
        )

    tasks = [call_model(m, m["personality"], build_prompt(m["id"]), 250) for m in COUNCIL]
    responses = await asyncio.gather(*tasks)
    return [
        {
            "id":       COUNCIL[i]["id"],
            "name":     COUNCIL[i]["name"],
            "emoji":    COUNCIL[i]["emoji"],
            "response": responses[i]
        }
        for i in range(len(COUNCIL))
    ]

# ── STAGE 4 — PEER RANKINGS ───────────────────────────────────────────────────

async def stage4(question, s3):
    labels        = [chr(65 + i) for i in range(len(s3))]
    label_to_model = {f"Response {lbl}": s3[i]["name"] for i, lbl in enumerate(labels)}
    block         = "\n\n".join([
        f"Response {lbl}:\n{s3[i]['response']}"
        for i, lbl in enumerate(labels)
    ])
    prompt = (
        f"Question: {question}\n\n"
        f"Final positions:\n{block}\n\n"
        "Evaluate each. Then write:\n"
        "FINAL RANKING:\n"
        "1. Response X\n"
        "2. Response Y\n"
        "3. Response Z\n"
        "4. Response W"
    )
    tasks     = [call_model(m, m["personality"], prompt, 350) for m in COUNCIL]
    responses = await asyncio.gather(*tasks)
    results   = []
    for i, resp in enumerate(responses):
        if "FINAL RANKING:" in resp:
            parsed = re.findall(r"Response\s+[A-Z]", resp.split("FINAL RANKING:")[-1])
        else:
            parsed = re.findall(r"Response\s+[A-Z]", resp)
        results.append({
            "id":             COUNCIL[i]["id"],
            "name":           COUNCIL[i]["name"],
            "emoji":          COUNCIL[i]["emoji"],
            "full_review":    resp,
            "parsed_ranking": parsed
        })
    return results, label_to_model

# ── STAGE 5 — CHAIRMAN PROMPT BUILDER ────────────────────────────────────────

def build_chairman_prompt(question, s1, s2, s3, s4, label_to_model):
    transcript = ""
    for m in COUNCIL:
        mid = m["id"]
        r1  = next((r["response"] for r in s1 if r["id"] == mid), "")
        r2  = next((r["response"] for r in s2 if r["id"] == mid), "")
        r3  = next((r["response"] for r in s3 if r["id"] == mid), "")
        transcript += (
            f"\n\n=== {m['emoji']} {m['name']} ===\n"
            f"[Initial]\n{r1}\n"
            f"[Attack]\n{r2}\n"
            f"[Final]\n{r3}"
        )

    positions = defaultdict(list)
    for review in s4:
        for pos, label in enumerate(review["parsed_ranking"], 1):
            if label in label_to_model:
                positions[label_to_model[label]].append(pos)

    ranking = " | ".join([
        f"{n}: avg {round(sum(p)/len(p), 1)}"
        for n, p in sorted(positions.items(), key=lambda x: sum(x[1]) / len(x[1]))
    ]) if positions else "N/A"

    labels_key = " | ".join([f"{k}={v}" for k, v in label_to_model.items()])

    user = (
        f"QUESTION: {question}\n\n"
        f"=== FULL DEBATE TRANSCRIPT ==={transcript}\n\n"
        f"=== PEER RANKINGS ===\n{ranking}\n"
        f"Label key: {labels_key}\n\n"
        "=== YOUR TASK ===\n"
        "You are the Chairman. Synthesize the single best possible answer.\n\n"
        "**Key Insights** — 2-3 strongest points that emerged from the debate\n"
        "**Points of Disagreement** — where valid opposing views still exist\n"
        "**Final Answer** — the most complete accurate answer to the question\n\n"
        "Write the Final Answer as a standalone response. Be thorough and specific."
    )
    return CHAIRMAN["personality"], user

# ── CONFIDENCE SCORE ──────────────────────────────────────────────────────────

def confidence(s4, label_to_model):
    picks = [
        label_to_model[r["parsed_ranking"][0]]
        for r in s4
        if r["parsed_ranking"] and r["parsed_ranking"][0] in label_to_model
    ]
    if not picks:
        return "Unknown agreement"
    winner, count = Counter(picks).most_common(1)[0]
    ratio = count / len(picks)
    if ratio >= 0.75:
        return f"Strong consensus — {winner} ranked best"
    elif ratio >= 0.5:
        return f"Good agreement — {winner} ranked highest"
    else:
        return "Contested topic — multiple valid perspectives"

# ── MAIN COUNCIL FUNCTION ─────────────────────────────────────────────────────

def do_council(message, history, groq_key, cerebras_key, threads_state):
    if groq_key.strip():
        os.environ["GROQ_API_KEY"]     = groq_key.strip()
    if cerebras_key.strip():
        os.environ["CEREBRAS_API_KEY"] = cerebras_key.strip()

    if not message.strip():
        yield history, "", threads_state, gr.update()
        return

    history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": "Working on it..."}
    ]
    loop = asyncio.get_event_loop()

    try:
        yield history, "🧠 Stage 1: Forming independent positions...", threads_state, gr.update()
        r1 = loop.run_until_complete(stage1(message))

        yield history, "⚔️ Stage 2: Models attacking each other...", threads_state, gr.update()
        r2 = loop.run_until_complete(stage2(message, r1))

        yield history, "🛡️ Stage 3: Defense and final positions...", threads_state, gr.update()
        r3 = loop.run_until_complete(stage3(message, r1, r2))

        yield history, "🏆 Stage 4: Peer rankings...", threads_state, gr.update()
        r4, ltm = loop.run_until_complete(stage4(message, r3))

        csys, cuser = build_chairman_prompt(message, r1, r2, r3, r4, ltm)

        streamed = ""
        yield history, "⚖️ Chairman writing final answer...", threads_state, gr.update()
        for token in stream_chairman(csys, cuser, max_tokens=2000):
            streamed += token
            history[-1] = {"role": "assistant", "content": streamed}
            yield history, "⚖️ Chairman writing...", threads_state, gr.update()

        history[-1] = {
            "role": "assistant",
            "content": streamed + f"\n\n---\n*{confidence(r4, ltm)}*"
        }

        title   = message[:45] + "..." if len(message) > 45 else message
        thread  = {
            "id":        str(int(time.time())),
            "title":     title,
            "timestamp": datetime.now().strftime("%b %d, %H:%M"),
            "history":   history
        }
        updated = [thread] + (threads_state or [])
        choices = [f"{t['timestamp']}  {t['title']}" for t in updated]
        yield history, "✅ Done!", updated, gr.update(choices=choices, value=choices[0])

    except Exception as e:
        history[-1] = {
            "role": "assistant",
            "content": f"**Error:** {str(e)[:300]}\n\nCheck your API keys in Settings."
        }
        yield history, "", threads_state, gr.update()

# ── THREAD HELPERS ────────────────────────────────────────────────────────────

def load_thread(choice, threads_state):
    if not choice or not threads_state:
        return [], gr.update()
    thread = next(
        (t for t in threads_state if f"{t['timestamp']}  {t['title']}" == choice),
        None
    )
    return (thread.get("history", []), gr.update()) if thread else ([], gr.update())


def new_chat(threads_state):
    return [], "", threads_state, gr.update(value=None)

# ── GRADIO UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="Atheneum") as demo:

    threads_state = gr.State([])

    with gr.Row():

        # SIDEBAR
        with gr.Column(scale=1, min_width=200):
            gr.Markdown("## 🏛️ Atheneum")
            new_btn = gr.Button("✏️ New Chat")
            gr.Markdown("---")
            gr.Markdown("**Recent**")
            thread_radio = gr.Radio(choices=[], label="", interactive=True)

        # MAIN CHAT AREA
        with gr.Column(scale=4):

            with gr.Accordion("⚙️ Settings — paste API keys here", open=False):
                with gr.Row():
                    groq_key_in     = gr.Textbox(
                        label="Groq API Key",
                        type="password",
                        placeholder="gsk_..."
                    )
                    cerebras_key_in = gr.Textbox(
                        label="Cerebras API Key",
                        type="password",
                        placeholder="csk_..."
                    )
                gr.Markdown(
                    "Free Groq key: [console.groq.com](https://console.groq.com)  "
                    "Free Cerebras key: [cloud.cerebras.ai](https://cloud.cerebras.ai)"
                )

            chatbox = gr.Chatbot(
                value=[],
                label="",
                height=520,
                show_label=False,
                render_markdown=True,
                type="messages",
                placeholder="### How can I help you today?\n\nAsk me anything."
            )

            status = gr.Markdown("")

            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="Message Atheneum...",
                    show_label=False,
                    lines=1,
                    max_lines=5,
                    scale=5
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")

    # ── EVENT WIRING ──────────────────────────────────────────────────────────
    ins  = [msg_input, chatbox, groq_key_in, cerebras_key_in, threads_state]
    outs = [chatbox, status, threads_state, thread_radio]

    send_btn.click(
        fn=do_council, inputs=ins, outputs=outs
    ).then(fn=lambda: "", outputs=[msg_input])

    msg_input.submit(
        fn=do_council, inputs=ins, outputs=outs
    ).then(fn=lambda: "", outputs=[msg_input])

    thread_radio.change(
        fn=load_thread,
        inputs=[thread_radio, threads_state],
        outputs=[chatbox, status]
    )

    new_btn.click(
        fn=new_chat,
        inputs=[threads_state],
        outputs=[chatbox, msg_input, threads_state, thread_radio]
    )

# ── LAUNCH ────────────────────────────────────────────────────────────────────
demo.launch()
