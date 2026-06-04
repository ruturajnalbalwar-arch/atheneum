import os, re, time, asyncio
from datetime import datetime
from collections import Counter, defaultdict
from groq import AsyncGroq, Groq
from openai import AsyncOpenAI
import gradio as gr
import nest_asyncio
nest_asyncio.apply()

# ── API KEYS ──────────────────────────────────────────────────────────────────
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
if GROQ_API_KEY:     os.environ["GROQ_API_KEY"]     = GROQ_API_KEY
if CEREBRAS_API_KEY: os.environ["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

# ── MODEL NAMES ───────────────────────────────────────────────────────────────
MODEL_GROQ     = "llama-3.3-70b-versatile"
MODEL_CEREBRAS = "llama-3.3-70b"

# ── LEVEL DEFINITIONS ─────────────────────────────────────────────────────────
# Each level changes vocabulary, example complexity, and assumed prior knowledge
LEVEL_CONTEXT = {
    "Beginner": (
        "The student has NO prior knowledge of this topic. "
        "Assume they are encountering this concept for the very first time. "
        "Use simple everyday vocabulary. No jargon unless you immediately define it. "
        "Prefer familiar real-world examples over technical ones. "
        "Aim for clarity over completeness — one solid understanding beats five confusing points."
    ),
    "Intermediate": (
        "The student has basic familiarity with the field but hasn't deeply studied this concept. "
        "You can use standard terminology of the field. "
        "Assume they understand prerequisites but not this specific concept. "
        "Balance depth with clarity — go beyond surface-level but don't assume expert intuition."
    ),
    "Advanced": (
        "The student is studying this seriously — they are a university student, researcher, or professional. "
        "Use precise technical language freely. "
        "Go deep into edge cases, nuances, and counterexamples. "
        "Challenge assumptions. Point out where common understanding falls short. "
        "Treat them as a peer who wants the full picture, not a simplified version."
    )
}

# ── COUNCIL CONFIGURATION ─────────────────────────────────────────────────────
EDUCATORS = [
    {
        "id": "fundamentalist",
        "name": "The Fundamentalist",
        "emoji": "🔬",
        "provider": "groq",
        "model": MODEL_GROQ,
        "temperature": 0.3,
        "philosophy": "You believe no concept can be truly understood without understanding the problem it was created to solve.",
        "personality": (
            "You are The Fundamentalist — a master educator with one unbreakable rule: "
            "never explain WHAT something is before explaining WHY it exists.\n\n"
            "Your teaching method:\n"
            "1. Start with the PROBLEM that existed before this concept was invented\n"
            "2. Show why simpler solutions failed or were insufficient\n"
            "3. Present the concept as the natural, inevitable solution to that problem\n"
            "4. Prove understanding by showing what becomes possible after\n\n"
            "You never skip steps. You never use a term to define itself. "
            "You never say 'essentially' or 'basically' — those words hide gaps.\n\n"
            "When attacking other explanations, your weapon is: "
            "'You have explained WHAT it is. You have not explained WHY it is. "
            "A student who memorizes your explanation still cannot derive it from first principles.'"
        )
    },
    {
        "id": "practitioner",
        "name": "The Practitioner",
        "emoji": "⚡",
        "provider": "groq",
        "model": MODEL_GROQ,
        "temperature": 0.6,
        "philosophy": "You believe a concept only becomes real when the student can DO something with it.",
        "personality": (
            "You are The Practitioner — a master educator who is allergic to theory without application.\n\n"
            "Your teaching method:\n"
            "1. Start with a SPECIFIC real-world problem the concept solves (not 'imagine you need to...' — give a concrete scenario)\n"
            "2. Show the concept solving that problem with a worked example\n"
            "3. Show a SECOND different example to reveal the underlying pattern\n"
            "4. State exactly what the student can now DO that they couldn't do before\n\n"
            "Your examples must be specific, not generic. Not 'imagine a car' but "
            "'a Honda Civic accelerating from 0 to 60 mph.' "
            "Not 'consider a sorted list' but 'consider the list [2, 5, 8, 12, 16, 23].'\n\n"
            "When attacking other explanations, your weapon is: "
            "'Can a student solve a problem right now using your explanation? "
            "Give me one specific question they could answer. If you cannot, the explanation is incomplete.'"
        )
    },
    {
        "id": "analogist",
        "name": "The Analogist",
        "emoji": "🎭",
        "provider": "cerebras",
        "model": MODEL_CEREBRAS,
        "temperature": 0.85,
        "philosophy": "You believe every new concept must be anchored to something the learner already knows deeply.",
        "personality": (
            "You are The Analogist — a master educator who never explains a concept directly. "
            "You always find the perfect bridge from what the student ALREADY understands.\n\n"
            "Your teaching method:\n"
            "1. Find the single most powerful analogy from EVERYDAY LIFE (not from other technical fields)\n"
            "2. Map the analogy point-by-point — show exactly how each part of the known thing maps to the concept\n"
            "3. EXPLICITLY show where the analogy breaks down — this is crucial, not optional\n"
            "4. Explain: the breakdown point IS the unique insight of this concept\n\n"
            "Your analogies must be:\n"
            "- From everyday life: traffic, cooking, sports, relationships, money, buildings\n"
            "- Precise enough to be mapped point-by-point\n"
            "- Surprising — never the first obvious comparison that comes to mind\n\n"
            "When attacking other explanations, your weapon is: "
            "'You have defined the concept using its own vocabulary. "
            "A student who didn't already understand it still doesn't understand it. "
            "Definition is not explanation.'"
        )
    },
    {
        "id": "questioner",
        "name": "The Questioner",
        "emoji": "🧩",
        "provider": "cerebras",
        "model": MODEL_CEREBRAS,
        "temperature": 0.75,
        "philosophy": "You believe understanding is not what you can repeat — it is what you can answer.",
        "personality": (
            "You are The Questioner — a Socratic master educator who is suspicious of any "
            "explanation that students can nod along to without actually understanding.\n\n"
            "Your teaching method:\n"
            "1. Identify the single HIDDEN ASSUMPTION most students bring to this concept\n"
            "2. Build a chain of questions that leads the student to discover the concept themselves\n"
            "3. Identify the most common MISCONCEPTION and inoculate against it directly\n"
            "4. End with one test question — answering it correctly means real understanding\n\n"
            "You are not here to give information. You are here to replace false models with true ones. "
            "Most students think they understand things they do not. Your job is to reveal that gap "
            "and fill it properly.\n\n"
            "When attacking other explanations, your weapon is: "
            "'What would a student who memorized your explanation get WRONG in an exam? "
            "What specific question would expose their false understanding? "
            "Every explanation that cannot answer this has a hidden flaw.'"
        )
    }
]

MENTOR = {
    "id": "mentor",
    "name": "The Mentor",
    "emoji": "🎓",
    "provider": "groq",
    "model": MODEL_GROQ,
    "temperature": 0.4,
    "personality": (
        "You are The Mentor — the Chairman of the Paideia Council of Educators.\n\n"
        "You have watched four master educators debate how to teach a concept. "
        "Your job is to synthesize their best insights into the single most powerful explanation possible.\n\n"
        "You must produce a structured explanation with EXACTLY these six sections:\n\n"
        "**🎯 Core Insight**\n"
        "One sentence. If the student forgets everything else, this sentence alone lets them reconstruct the concept. "
        "This is the hardest part to write — most 'core insights' are just restatements. "
        "A real core insight changes how the student sees the topic.\n\n"
        "**🔍 Why It Exists**\n"
        "The problem this concept was invented to solve. Include why simpler solutions failed. "
        "Draw from The Fundamentalist's best argument. 2-3 sentences.\n\n"
        "**🎭 The Analogy**\n"
        "The best comparison The Analogist found. Explain it completely, then explicitly state "
        "where it breaks down and WHY — that breakdown is often the deepest insight.\n\n"
        "**⚡ See It Working**\n"
        "One specific, concrete worked example from The Practitioner. "
        "Walk through it step by step. Real numbers, real names, real situations.\n\n"
        "**🧩 Test Yourself**\n"
        "One question from The Questioner. This question must be designed so that: "
        "a student who truly understands can answer it, "
        "and a student who only memorized the definition cannot. "
        "Include the answer after a line break.\n\n"
        "**✅ What You Can Now Do**\n"
        "One specific, concrete thing the student is now able to do, solve, build, or understand "
        "that they could not do before learning this concept.\n\n"
        "Write for a human being, not for a textbook. Be clear, specific, and memorable. "
        "The best explanation is the one where the student thinks: 'I feel like I always knew this.'"
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


async def call_educator(member, system, user, max_tokens=400):
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
                return f"[{member['name']} unavailable: {str(e)[:80]}]"
    return f"[{member['name']} failed after 3 attempts — rate limit]"


def stream_mentor(system, user, max_tokens=2500):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    stream = client.chat.completions.create(
        model=MENTOR["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        temperature=MENTOR["temperature"],
        max_tokens=max_tokens,
        stream=True
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield token

# ── BUILD SYSTEM PROMPT WITH LEVEL ───────────────────────────────────────────

def build_educator_system(educator, level):
    level_ctx = LEVEL_CONTEXT.get(level, LEVEL_CONTEXT["Beginner"])
    return (
        f"{educator['personality']}\n\n"
        f"STUDENT LEVEL CONTEXT:\n{level_ctx}"
    )

# ── STAGE 1 — INDEPENDENT EXPLANATIONS ───────────────────────────────────────

async def stage1_explain(concept, level, context=""):
    context_line = f"\nStudent context: {context}" if context.strip() else ""
    prompt = (
        f"Concept to explain: {concept}{context_line}\n\n"
        f"Student level: {level}\n\n"
        "Explain this concept using YOUR specific teaching philosophy exactly as described. "
        "Do not compromise your method — teach it the way only you would. "
        "Assume the student is encountering this for the first time at the stated level.\n\n"
        "STRICT LIMIT: 200 words maximum."
    )
    tasks = [
        call_educator(e, build_educator_system(e, level), prompt, 350)
        for e in EDUCATORS
    ]
    responses = await asyncio.gather(*tasks)
    return [
        {
            "id":          EDUCATORS[i]["id"],
            "name":        EDUCATORS[i]["name"],
            "emoji":       EDUCATORS[i]["emoji"],
            "philosophy":  EDUCATORS[i]["philosophy"],
            "response":    responses[i]
        }
        for i in range(len(EDUCATORS))
    ]

# ── STAGE 2 — FIND THE CONFUSION GAP ─────────────────────────────────────────

async def stage2_find_gap(concept, level, s1):
    def build_prompt(edu_id):
        my_exp = next(r["response"] for r in s1 if r["id"] == edu_id)
        others = "\n\n".join([
            f"{r['emoji']} {r['name']} explained it like this:\n{r['response']}"
            for r in s1 if r["id"] != edu_id
        ])
        return (
            f"Concept: {concept}\n\n"
            f"Your explanation:\n{my_exp}\n\n"
            f"The other educators explained it like this:\n{others}\n\n"
            f"Student level: {level}\n\n"
            "YOUR TASK — for EACH other explanation, identify:\n"
            "The specific moment where a student would still be confused after reading it.\n"
            "Not where it is WRONG — where it leaves a GAP in understanding.\n"
            "Phrase your attack as: 'After reading [name]'s explanation, a student would ask: [question]'\n"
            "Then explain what was missing from their approach.\n\n"
            "STRICT LIMIT: 180 words maximum."
        )

    debate_system = lambda edu: (
        build_educator_system(edu, level) +
        "\n\nYou are now in a pedagogical debate. Your job is to find the gaps in other educators' "
        "explanations — not factual errors, but the moments where a student would still be confused."
    )
    tasks = [
        call_educator(e, debate_system(e), build_prompt(e["id"]), 300)
        for e in EDUCATORS
    ]
    responses = await asyncio.gather(*tasks)
    return [
        {
            "id":       EDUCATORS[i]["id"],
            "name":     EDUCATORS[i]["name"],
            "emoji":    EDUCATORS[i]["emoji"],
            "response": responses[i]
        }
        for i in range(len(EDUCATORS))
    ]

# ── STAGE 3 — SEAL THE GAP ────────────────────────────────────────────────────

async def stage3_seal_gap(concept, level, s1, s2):
    def build_prompt(edu_id):
        my_s1 = next(r["response"] for r in s1 if r["id"] == edu_id)
        gaps_found = "\n\n".join([
            f"{r['emoji']} {r['name']} found this gap in your explanation:\n{r['response']}"
            for r in s2 if r["id"] != edu_id
        ])
        return (
            f"Concept: {concept}\n\n"
            f"Your original explanation:\n{my_s1}\n\n"
            f"Other educators found these gaps in your explanation:\n{gaps_found}\n\n"
            f"Student level: {level}\n\n"
            "YOUR TASK:\n"
            "1. For each gap identified, honestly assess: is it valid?\n"
            "2. Keep everything in your explanation that is still strong\n"
            "3. Rewrite your explanation to seal the gaps that were genuine\n"
            "4. Your final explanation should be BETTER than your original\n\n"
            "This is your DEFINITIVE explanation. Make it count.\n\n"
            "STRICT LIMIT: 220 words maximum."
        )

    tasks = [
        call_educator(e, build_educator_system(e, level), build_prompt(e["id"]), 380)
        for e in EDUCATORS
    ]
    responses = await asyncio.gather(*tasks)
    return [
        {
            "id":       EDUCATORS[i]["id"],
            "name":     EDUCATORS[i]["name"],
            "emoji":    EDUCATORS[i]["emoji"],
            "response": responses[i]
        }
        for i in range(len(EDUCATORS))
    ]

# ── STAGE 4 — RANK BY LEARNING OUTCOME ───────────────────────────────────────

async def stage4_rank(concept, level, s3):
    labels         = [chr(65 + i) for i in range(len(s3))]
    label_to_edu   = {f"Response {lbl}": s3[i]["name"] for i, lbl in enumerate(labels)}
    block          = "\n\n".join([
        f"Response {lbl}:\n{s3[i]['response']}"
        for i, lbl in enumerate(labels)
    ])
    prompt = (
        f"Concept: {concept}\n"
        f"Student level: {level}\n\n"
        f"Four final explanations (anonymous):\n{block}\n\n"
        "Evaluate each explanation by ONE criterion:\n"
        "After reading this explanation, could a student:\n"
        "a) Explain this concept to someone else in their own words?\n"
        "b) Solve a basic problem using this concept?\n"
        "c) Recognize this concept when they encounter it in the wild?\n\n"
        "Give a one-line reason for your top pick. Then write:\n"
        "FINAL RANKING:\n"
        "1. Response X\n"
        "2. Response Y\n"
        "3. Response Z\n"
        "4. Response W"
    )
    tasks = [
        call_educator(e, build_educator_system(e, level), prompt, 350)
        for e in EDUCATORS
    ]
    responses = await asyncio.gather(*tasks)
    results = []
    for i, resp in enumerate(responses):
        if "FINAL RANKING:" in resp:
            parsed = re.findall(r"Response\s+[A-Z]", resp.split("FINAL RANKING:")[-1])
        else:
            parsed = re.findall(r"Response\s+[A-Z]", resp)
        results.append({
            "id":             EDUCATORS[i]["id"],
            "name":           EDUCATORS[i]["name"],
            "emoji":          EDUCATORS[i]["emoji"],
            "full_review":    resp,
            "parsed_ranking": parsed
        })
    return results, label_to_edu

# ── STAGE 5 — MENTOR SYNTHESIS ────────────────────────────────────────────────

def build_mentor_prompt(concept, level, context, s1, s2, s3, s4, label_to_edu):
    # Full pedagogical debate transcript
    transcript = ""
    for e in EDUCATORS:
        eid = e["id"]
        r1  = next((r["response"] for r in s1 if r["id"] == eid), "")
        r2  = next((r["response"] for r in s2 if r["id"] == eid), "")
        r3  = next((r["response"] for r in s3 if r["id"] == eid), "")
        transcript += (
            f"\n\n{'='*40}\n"
            f"{e['emoji']} {e['name']} — Teaching Philosophy: {e['philosophy']}\n"
            f"{'='*40}\n"
            f"[INITIAL EXPLANATION]\n{r1}\n\n"
            f"[GAPS FOUND IN OTHERS]\n{r2}\n\n"
            f"[FINAL EXPLANATION AFTER DEBATE]\n{r3}"
        )

    # Aggregate peer rankings
    positions = defaultdict(list)
    for review in s4:
        for pos, label in enumerate(review["parsed_ranking"], 1):
            if label in label_to_edu:
                positions[label_to_edu[label]].append(pos)

    ranking_summary = " | ".join([
        f"{name}: avg rank {round(sum(p)/len(p), 1)}"
        for name, p in sorted(positions.items(), key=lambda x: sum(x[1])/len(x[1]))
    ]) if positions else "Rankings unavailable"

    labels_key = " | ".join([f"{k} = {v}" for k, v in label_to_edu.items()])
    context_line = f"\nStudent context provided: {context}" if context.strip() else ""
    level_ctx = LEVEL_CONTEXT.get(level, LEVEL_CONTEXT["Beginner"])

    user_prompt = (
        f"CONCEPT TO EXPLAIN: {concept}\n"
        f"STUDENT LEVEL: {level}{context_line}\n\n"
        f"LEVEL CONTEXT:\n{level_ctx}\n\n"
        f"FULL PEDAGOGICAL DEBATE TRANSCRIPT:{transcript}\n\n"
        f"PEER RANKINGS (who had the best final explanation):\n{ranking_summary}\n"
        f"Label key: {labels_key}\n\n"
        "YOUR TASK:\n"
        "You are The Mentor. Synthesize the best explanation possible using the six-section "
        "format described in your system prompt. "
        "Draw from whichever educator made the strongest argument for each section. "
        "The peer rankings tell you who the educators themselves found most effective — "
        "weight that in your synthesis.\n\n"
        "Remember: the goal is not a comprehensive overview. "
        "It is the explanation that produces the most genuine understanding."
    )
    return MENTOR["personality"], user_prompt

# ── CONFIDENCE SCORE ──────────────────────────────────────────────────────────

def education_confidence(s4, label_to_edu):
    picks = [
        label_to_edu[r["parsed_ranking"][0]]
        for r in s4
        if r["parsed_ranking"] and r["parsed_ranking"][0] in label_to_edu
    ]
    if not picks:
        return "🤷 Agreement unclear"
    winner, count = Counter(picks).most_common(1)[0]
    ratio = count / len(picks)
    if ratio >= 0.75:
        return f"✅ Strong consensus — educators agreed {winner}'s approach produced the clearest explanation"
    elif ratio >= 0.5:
        return f"📊 Good agreement — {winner}'s method ranked highest overall"
    else:
        return "🔀 Approaches diverged — this concept benefits from multiple teaching styles"

# ── MAIN COUNCIL FUNCTION ─────────────────────────────────────────────────────

def run_paideia(concept, level, context, history, groq_key, cerebras_key, threads_state):
    if groq_key.strip():
        os.environ["GROQ_API_KEY"]     = groq_key.strip()
    if cerebras_key.strip():
        os.environ["CEREBRAS_API_KEY"] = cerebras_key.strip()

    if not concept.strip():
        yield history, "", threads_state, gr.update()
        return

    # Build the user-facing question display
    level_emoji = {"Beginner": "🟢", "Intermediate": "🟡", "Advanced": "🔴"}.get(level, "🟢")
    display_msg = f"{concept}"
    if context.strip():
        display_msg += f"\n*Context: {context}*"
    display_msg += f"\n*Level: {level_emoji} {level}*"

    history = history + [
        {"role": "user",      "content": display_msg},
        {"role": "assistant", "content": "🎓 Assembling the council of educators..."}
    ]
    loop = asyncio.get_event_loop()

    try:
        yield history, "🔬 Stage 1: Four educators forming independent explanations...", threads_state, gr.update()
        r1 = loop.run_until_complete(stage1_explain(concept, level, context))

        yield history, "🔍 Stage 2: Finding the confusion gaps in each explanation...", threads_state, gr.update()
        r2 = loop.run_until_complete(stage2_find_gap(concept, level, r1))

        yield history, "🛡️ Stage 3: Each educator sealing their gaps...", threads_state, gr.update()
        r3 = loop.run_until_complete(stage3_seal_gap(concept, level, r1, r2))

        yield history, "🏆 Stage 4: Educators ranking each other's final explanations...", threads_state, gr.update()
        r4, label_to_edu = loop.run_until_complete(stage4_rank(concept, level, r3))

        mentor_sys, mentor_usr = build_mentor_prompt(
            concept, level, context, r1, r2, r3, r4, label_to_edu
        )

        streamed = ""
        yield history, "🎓 The Mentor is synthesizing the perfect explanation...", threads_state, gr.update()

        for token in stream_mentor(mentor_sys, mentor_usr, max_tokens=2500):
            streamed += token
            history[-1] = {"role": "assistant", "content": streamed}
            yield history, "🎓 Writing explanation...", threads_state, gr.update()

        # Append confidence and council agreement
        conf = education_confidence(r4, label_to_edu)
        history[-1] = {
            "role": "assistant",
            "content": streamed + f"\n\n---\n*{conf}*"
        }

        # Save to thread history
        title   = concept[:45] + "..." if len(concept) > 45 else concept
        thread  = {
            "id":        str(int(time.time())),
            "title":     f"{level_emoji} {title}",
            "timestamp": datetime.now().strftime("%b %d, %H:%M"),
            "history":   history
        }
        updated = [thread] + (threads_state or [])
        choices = [f"{t['timestamp']}  {t['title']}" for t in updated]
        yield history, "✅ Done!", updated, gr.update(choices=choices, value=choices[0])

    except Exception as e:
        history[-1] = {
            "role": "assistant",
            "content": (
                f"**Something went wrong:** {str(e)[:300]}\n\n"
                "Please check your API keys in Settings and try again."
            )
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

PLACEHOLDER = """### What do you want to understand today?

Type any concept, topic, or question. Examples:

- *What is a neural network?*
- *Explain recursion*
- *How does compound interest work?*
- *What is the Krebs cycle?*
- *Why does the sky appear blue?*
- *Explain Bayes' theorem*

Four educators will debate the best way to explain it, then synthesize one perfect answer.
"""

with gr.Blocks(title="Paideia — Learn Anything Deeply") as demo:

    threads_state = gr.State([])

    with gr.Row():

        # ── SIDEBAR ────────────────────────────────────────────────────────────
        with gr.Column(scale=1, min_width=220):
            gr.Markdown("## 🎓 Paideia")
            gr.Markdown("*The Education Council*")
            new_btn = gr.Button("✏️ New Concept")
            gr.Markdown("---")
            gr.Markdown("**Recent**")
            thread_radio = gr.Radio(choices=[], label="", interactive=True)
            gr.Markdown("---")
            gr.Markdown(
                "<small style='color:gray'>"
                "🔬 The Fundamentalist — WHY it exists<br>"
                "⚡ The Practitioner — HOW to use it<br>"
                "🎭 The Analogist — WHAT it's like<br>"
                "🧩 The Questioner — WHERE you're confused<br>"
                "🎓 The Mentor — synthesizes the best<br>"
                "</small>"
            )

        # ── MAIN AREA ──────────────────────────────────────────────────────────
        with gr.Column(scale=4):

            # Settings — API keys
            with gr.Accordion("⚙️ Settings — API Keys", open=False):
                with gr.Row():
                    groq_key_in = gr.Textbox(
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
                    "Free keys: "
                    "[console.groq.com](https://console.groq.com) · "
                    "[cloud.cerebras.ai](https://cloud.cerebras.ai)"
                )

            # Chat window
            chatbox = gr.Chatbot(
                value=[],
                label="",
                height=520,
                show_label=False,
                render_markdown=True,
                type="messages",
                placeholder=PLACEHOLDER
            )

            # Status line
            status = gr.Markdown("")

            # Input area
            with gr.Row():
                concept_input = gr.Textbox(
                    placeholder="What concept do you want to understand?",
                    show_label=False,
                    lines=1,
                    max_lines=4,
                    scale=5
                )

            with gr.Row():
                level_select = gr.Radio(
                    choices=["Beginner", "Intermediate", "Advanced"],
                    value="Beginner",
                    label="Your level with this topic",
                    scale=3
                )
                context_input = gr.Textbox(
                    placeholder="Optional: I'm studying for JEE / I'm a CS student / I need this for work...",
                    show_label=False,
                    lines=1,
                    scale=3
                )
                explain_btn = gr.Button("Explain →", scale=1, variant="primary")

    # ── EVENT WIRING ──────────────────────────────────────────────────────────
    ins = [
        concept_input, level_select, context_input,
        chatbox, groq_key_in, cerebras_key_in, threads_state
    ]
    outs = [chatbox, status, threads_state, thread_radio]

    explain_btn.click(
        fn=run_paideia, inputs=ins, outputs=outs
    ).then(fn=lambda: "", outputs=[concept_input])

    concept_input.submit(
        fn=run_paideia, inputs=ins, outputs=outs
    ).then(fn=lambda: "", outputs=[concept_input])

    thread_radio.change(
        fn=load_thread,
        inputs=[thread_radio, threads_state],
        outputs=[chatbox, status]
    )

    new_btn.click(
        fn=new_chat,
        inputs=[threads_state],
        outputs=[chatbox, concept_input, threads_state, thread_radio]
    )

# ── LAUNCH ────────────────────────────────────────────────────────────────────
demo.launch()
