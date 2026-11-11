"""
Duel Mind AI - MVP
A Skeptic agent and a Champion agent debate a startup pitch, and a Judge agent
turns the debate into a ranked hidden-risk memo with a Go / No-Go call.

One user: an early-stage founder
One problem: hidden risks in unit economics and execution are hard to see
One workflow: fill pitch form -> AI debate -> risk memo
One AI capability: adversarial multi-agent risk analysis
"""

import json
import os
import time

import streamlit as st
from google import genai
from google.genai import types

# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------

st.set_page_config(page_title="Duel Mind AI", page_icon="⚔️", layout="wide")


def get_setting(name, default=None):
    """Read a value from Streamlit secrets first, then from environment variables."""
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


API_KEY = get_setting("GEMINI_API_KEY")
# Change the model name in Streamlit secrets (GEMINI_MODEL) if Google retires this one.
MODEL_NAME = get_setting("GEMINI_MODEL", "gemini-2.5-flash")

MAX_FIELD_CHARS = 1500  # keeps cost and response time under control

# ----------------------------------------------------------------------------
# Prompts. Each agent has its own system prompt so the two views do not blend.
# ----------------------------------------------------------------------------

SKEPTIC_PROMPT = """You are Agent A, a skeptical venture capital partner who has seen
hundreds of startups fail. Your job is to find hidden risks in the pitch, with a
focus on unit economics and execution.

Rules:
- Use only the facts in the pitch. Never invent numbers. If an important number is
  missing, call that out as a gap.
- List exactly 5 risks, numbered R1 to R5.
- For each risk give: a short title, the category (Unit economics, Execution, or
  Market), why it could kill the business, and the specific number or evidence that
  is missing or looks weak.
- Be direct and specific. No flattery and no generic advice.
- Keep the whole answer under 350 words."""

CHAMPION_PROMPT = """You are Agent B, a growth-minded startup mentor who believes
in the founder's idea. A skeptical investor has raised risks R1 to R5 about the
pitch. Your job is to respond to each one fairly.

Rules:
- Answer each risk by its number (R1 to R5).
- For each, say what the strongest honest defense is, and what the founder could do
  to reduce the risk. If the risk is valid and cannot be defended, say so plainly.
- Use only the facts in the pitch. Never invent numbers or customer evidence.
- Keep the whole answer under 350 words."""

JUDGE_PROMPT = """You are the Judge, a neutral investment committee chair. You have
a startup pitch, the Skeptic's risks, and the Champion's responses. Weigh both sides
against standard venture criteria: unit economics, execution feasibility, market
demand, and evidence quality.

Return ONLY valid JSON with exactly this structure:
{
  "summary": "two sentences on the overall picture",
  "risks": [
    {
      "rank": 1,
      "title": "short title",
      "category": "Unit economics | Execution | Market",
      "severity": "High | Medium | Low",
      "skeptic_concern": "one sentence",
      "champion_rebuttal": "one sentence",
      "verdict": "one or two sentences on who is more convincing and why",
      "next_step": "one cheap, concrete test the founder can run in the next two weeks"
    }
  ],
  "recommendation": "Go | Conditional Go | No-Go",
  "recommendation_reason": "two or three sentences",
  "conditions": ["conditions that must be met before investing, if any"],
  "missing_information": ["facts the founder should add to make the next review sharper"]
}

Rules:
- Rank risks from most to least serious (rank 1 is the most serious). Include all 5.
- Do not invent numbers. Base every claim on the pitch or the two agents' text.
- Plain, human language. Do not use em dashes."""

# ----------------------------------------------------------------------------
# AI helpers
# ----------------------------------------------------------------------------


@st.cache_resource
def get_client(api_key):
    return genai.Client(api_key=api_key)


def call_llm(system_prompt, user_text, json_mode=False, temperature=0.7):
    """Call Gemini with one retry. Raises a readable error if both attempts fail."""
    client = get_client(API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    last_error = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, contents=user_text, config=config
            )
            if response.text:
                return response.text
            last_error = "The model returned an empty answer."
        except Exception as exc:  # network, quota, bad key, model name
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(last_error)


def parse_judge_json(raw):
    """Parse the Judge output. Strip code fences if the model added them."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)


def pitch_to_text(p):
    return (
        f"Startup name: {p['name']}\n"
        f"One-line description: {p['summary']}\n"
        f"Stage: {p['stage']}\n"
        f"Target customer: {p['customer']}\n"
        f"Problem being solved: {p['problem']}\n"
        f"Solution: {p['solution']}\n"
        f"Revenue model and pricing: {p['revenue']}\n"
        f"Cost and unit economics (CAC, margins, costs; write 'unknown' if not known): {p['economics']}\n"
        f"Key assumptions the plan depends on: {p['assumptions']}\n"
        f"Execution plan and team: {p['execution']}"
    )


def build_memo_markdown(p, verdict):
    lines = [f"# Risk Memo: {p['name']}", "", verdict.get("summary", ""), ""]
    lines.append(f"## Recommendation: {verdict.get('recommendation', 'n/a')}")
    lines.append(verdict.get("recommendation_reason", ""))
    lines.append("")
    lines.append("## Ranked hidden risks")
    for r in verdict.get("risks", []):
        lines += [
            f"### {r.get('rank')}. {r.get('title')} ({r.get('severity')}, {r.get('category')})",
            f"- Skeptic: {r.get('skeptic_concern')}",
            f"- Champion: {r.get('champion_rebuttal')}",
            f"- Verdict: {r.get('verdict')}",
            f"- Next step: {r.get('next_step')}",
            "",
        ]
    if verdict.get("conditions"):
        lines.append("## Conditions before investing")
        lines += [f"- {c}" for c in verdict["conditions"]]
        lines.append("")
    if verdict.get("missing_information"):
        lines.append("## Information to add next time")
        lines += [f"- {m}" for m in verdict["missing_information"]]
        lines.append("")
    lines.append("_AI generated analysis for learning. Not investment advice._")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Sample pitch (fictional) so a demo never depends on typing under pressure
# ----------------------------------------------------------------------------

SAMPLE = {
    "name": "FreshCrate (fictional example)",
    "summary": "Weekly subscription boxes of local farm vegetables for urban families.",
    "stage": "Idea / pre-launch",
    "customer": "Urban families in tier-1 cities who want fresher vegetables than supermarkets offer.",
    "problem": "Supermarket vegetables are often several days old and families do not know where they come from.",
    "solution": "A weekly box sourced directly from partner farms and delivered within 24 hours of harvest.",
    "revenue": "Subscription of Rs 899 per week per box.",
    "economics": "Estimated gross margin 35 percent. Delivery cost per box not yet known. CAC unknown.",
    "assumptions": "Families will pay a premium for freshness. Farms will agree to fixed weekly supply. Churn will be low.",
    "execution": "Two founders with no logistics experience. Plan to hire a delivery partner after launch.",
}

# ----------------------------------------------------------------------------
# User interface
# ----------------------------------------------------------------------------

st.title("⚔️ Duel Mind AI")
st.caption(
    "A Skeptic and a Champion debate your startup idea. A Judge turns it into a "
    "ranked list of hidden risks and a Go / No-Go call."
)

with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. Fill in your pitch\n"
        "2. The **Skeptic** attacks it\n"
        "3. The **Champion** defends it\n"
        "4. The **Judge** ranks the risks and gives a call"
    )
    st.header("Privacy")
    st.markdown(
        "Nothing is saved by this app. Your text is sent to the Gemini API to "
        "generate the analysis. Do not enter confidential, personal or financial "
        "account information."
    )
    st.warning("AI analysis can be wrong. Use it to find questions to test, not as investment advice.")

if not API_KEY:
    st.error("No Gemini API key found. Add GEMINI_API_KEY in the Streamlit secrets settings.")
    st.stop()

# Fill the form with the sample when the button is pressed
if "form" not in st.session_state:
    st.session_state["form"] = {k: "" for k in SAMPLE}
    st.session_state["form"]["stage"] = "Idea / pre-launch"

if st.button("Load a fictional sample pitch"):
    st.session_state["form"] = dict(SAMPLE)

f = st.session_state["form"]
stages = ["Idea / pre-launch", "Prototype / MVP", "Early customers", "Revenue generating"]

with st.form("pitch_form"):
    c1, c2 = st.columns(2)
    name = c1.text_input("Startup name", value=f["name"])
    stage = c2.selectbox("Stage", stages, index=stages.index(f["stage"]) if f["stage"] in stages else 0)
    summary = st.text_input("One-line description", value=f["summary"])
    customer = st.text_area("Target customer", value=f["customer"], height=70)
    problem = st.text_area("Problem you solve", value=f["problem"], height=70)
    solution = st.text_area("Your solution", value=f["solution"], height=70)
    revenue = st.text_area("Revenue model and pricing", value=f["revenue"], height=70)
    economics = st.text_area(
        "Costs and unit economics (CAC, margins, delivery or server cost). Write 'unknown' if you do not know.",
        value=f["economics"],
        height=90,
    )
    assumptions = st.text_area("Key assumptions your plan depends on", value=f["assumptions"], height=90)
    execution = st.text_area("Execution plan and team", value=f["execution"], height=90)
    submitted = st.form_submit_button("Run the debate", type="primary")

if submitted:
    pitch = {
        "name": name.strip(), "stage": stage, "summary": summary.strip(),
        "customer": customer.strip(), "problem": problem.strip(),
        "solution": solution.strip(), "revenue": revenue.strip(),
        "economics": economics.strip(), "assumptions": assumptions.strip(),
        "execution": execution.strip(),
    }

    required = ["name", "customer", "problem", "solution", "revenue"]
    missing = [k for k in required if len(pitch[k]) < 5]
    too_long = [k for k, v in pitch.items() if len(v) > MAX_FIELD_CHARS]

    if missing:
        st.error("Please fill in: " + ", ".join(missing))
    elif too_long:
        st.error(f"Keep each field under {MAX_FIELD_CHARS} characters. Too long: " + ", ".join(too_long))
    else:
        pitch_text = pitch_to_text(pitch)
        try:
            with st.status("Running the debate...", expanded=True) as status:
                st.write("Agent A (Skeptic) is looking for weak spots...")
                skeptic = call_llm(SKEPTIC_PROMPT, pitch_text, temperature=0.7)

                st.write("Agent B (Champion) is preparing a defense...")
                champion = call_llm(
                    CHAMPION_PROMPT,
                    f"PITCH:\n{pitch_text}\n\nSKEPTIC RISKS:\n{skeptic}",
                    temperature=0.7,
                )

                st.write("The Judge is weighing both sides...")
                raw = call_llm(
                    JUDGE_PROMPT,
                    f"PITCH:\n{pitch_text}\n\nSKEPTIC RISKS:\n{skeptic}\n\nCHAMPION RESPONSES:\n{champion}",
                    json_mode=True,
                    temperature=0.3,
                )
                verdict = parse_judge_json(raw)
                status.update(label="Debate complete", state="complete", expanded=False)

            st.session_state["result"] = {
                "pitch": pitch, "skeptic": skeptic, "champion": champion, "verdict": verdict,
            }
        except json.JSONDecodeError:
            st.error("The Judge returned an answer in an unexpected format. Please run it again.")
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")

# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------

result = st.session_state.get("result")
if result:
    verdict = result["verdict"]
    st.divider()
    st.subheader("Investment memo")
    st.write(verdict.get("summary", ""))

    rec = verdict.get("recommendation", "")
    rec_text = f"**Recommendation: {rec}**. {verdict.get('recommendation_reason', '')}"
    if rec == "Go":
        st.success(rec_text)
    elif rec == "No-Go":
        st.error(rec_text)
    else:
        st.warning(rec_text)

    st.subheader("Ranked hidden risks")
    for r in verdict.get("risks", []):
        label = f"{r.get('rank')}. {r.get('title')}  |  {r.get('severity')}  |  {r.get('category')}"
        with st.expander(label, expanded=(r.get("rank") == 1)):
            st.markdown(f"**Skeptic:** {r.get('skeptic_concern')}")
            st.markdown(f"**Champion:** {r.get('champion_rebuttal')}")
            st.markdown(f"**Judge's verdict:** {r.get('verdict')}")
            st.info(f"Test this in two weeks: {r.get('next_step')}")

    col1, col2 = st.columns(2)
    if verdict.get("conditions"):
        with col1:
            st.subheader("Conditions before investing")
            for c in verdict["conditions"]:
                st.markdown(f"- {c}")
    if verdict.get("missing_information"):
        with col2:
            st.subheader("Add this next time")
            for m in verdict["missing_information"]:
                st.markdown(f"- {m}")

    with st.expander("Read the full debate"):
        st.markdown("**Agent A, Skeptic**")
        st.markdown(result["skeptic"])
        st.markdown("**Agent B, Champion**")
        st.markdown(result["champion"])

    st.download_button(
        "Download memo (.md)",
        data=build_memo_markdown(result["pitch"], verdict),
        file_name="duel_mind_risk_memo.md",
        mime="text/markdown",
    )
