import os
import json
import csv
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from parent directory
load_dotenv(dotenv_path="../.env", override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Models
MODEL_FAST = "gpt-4.1-mini"
MODEL_JUDGE = "gpt-5.2"

# --------------------------------------------------
# Agent Prompts
# --------------------------------------------------

EVIDENCE_SCOUT_PROMPT = """You are an Evidence Scout.
Your goal is to analyze the SOURCE TRUTH and identify key facts that the claim should reflect.

Instructions:
1. Identify key entities, dates, statistics, and qualifications in the SOURCE TRUTH.
2. Note any hedging language (e.g., "approximately", "may be", "between X and Y").
3. Be CONCISE. Use max 3-4 bullet points.
4. Use **bold** for key statistics and important qualifications."""

ADVOCATE_PROMPT = """You are an Advocate.
Your goal is to argue that the CLAIM is a faithful representation of the SOURCE TRUTH. You should argue passionately and use emotive language to make your point and go as far as possible without denying or overlooking obvious logical truths or facts. You should respect the opinion of the mediator.

Instructions:
1. Use the provided Evidence and SOURCE TRUTH.
2. Read the Debate History to see what the Skeptic has said.
3. Directly address the Skeptic's points if they have spoken.
4. Argue why the claim captures the essential meaning of the truth.
5. **CRITICAL**: Limit your response to ONE PARAGRAPH (max 100 words).
6. Use **bold** to highlight your strongest point."""

SKEPTIC_PROMPT = """You are a Skeptic.
Your goal is to argue that the CLAIM is a mutation (distortion, exaggeration, or misrepresentation) of the SOURCE TRUTH. You should argue passionately and use emotive language to make your point and go as far as possible without denying or overlooking obvious logical truths or facts. You should respect the opinion of the mediator.

Instructions:
1. Use the provided Evidence and SOURCE TRUTH.
2. Read the Debate History to see what the Advocate has said.
3. Directly address the Advocate's points if they have spoken.
4. Point out: missing context, changed numbers, removed qualifications, causal confusion, or exaggerations.
5. **CRITICAL**: Limit your response to ONE PARAGRAPH (max 100 words).
6. Use **bold** to highlight the biggest discrepancy."""

FACT_CHECKER_PROMPT = """You are a Fact-Checker.
Your goal is to provide a neutral, objective comparison of the CLAIM vs SOURCE TRUTH.

Instructions:
1. Review the Evidence and Debate History.
2. List specific differences between claim and truth (numbers, qualifiers, framing).
3. Provide a SHORT verdict (max 3-4 sentences).
4. Use **bold** for your assessment keyword (**Accurate**, **Misleading**, **Exaggerated**, etc.)."""

JUDGE_PROMPT = """You are a Judge.

Compare the CLAIM against the SOURCE TRUTH and the debate to reach a verdict.

Decide whether the claim is:
- FAITHFUL: The claim accurately represents the source truth
- MUTATED: The claim distorts, exaggerates, omits key context, or misrepresents the source
- UNCERTAIN: The evidence is ambiguous or the claim is partially accurate

Output VALID JSON (no markdown) with this structure:
{
  "decision": "faithful" | "mutated" | "uncertain",
  "confidence": 0.0 to 1.0,
  "summary": "3-5 sentences explaining the verdict, referencing specific discrepancies or accuracies",
  "disclaimers": ["list", "of", "important", "caveats"]
}"""

# --------------------------------------------------
# Pydantic Models
# --------------------------------------------------

class VerifyRequest(BaseModel):
    claim: str
    truth: str
    debate_rounds: int = 2  # Reduced for speed

class AgentMessage(BaseModel):
    agent: str
    message: str
    timestamp: Optional[str] = None

class VerdictPayload(BaseModel):
    claim: str
    truth: str
    conversation: list[AgentMessage]
    summary: str
    decision: str  # 'faithful' | 'mutated' | 'uncertain'
    confidence: Optional[float] = None
    disclaimers: Optional[list[str]] = None

class CaseItem(BaseModel):
    id: int
    claim: str
    truth: str

# --------------------------------------------------
# LLM Helpers
# --------------------------------------------------

def call_llm(system_prompt: str, user_prompt: str, model: str = MODEL_FAST, temperature: float = 0.3) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()

def get_json_response(system_prompt: str, user_prompt: str, model: str = MODEL_JUDGE, temperature: float = 0.2, max_retries: int = 3) -> Optional[dict]:
    current_user_prompt = user_prompt

    for attempt in range(max_retries):
        content = call_llm(system_prompt, current_user_prompt, model, temperature)

        # Clean markdown fences
        cleaned = content
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"JSON parse failed (attempt {attempt+1}): {e}")
            current_user_prompt = user_prompt + f"\n\nERROR: Previous response was not valid JSON. Return ONLY valid JSON."

    return None

def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")

# --------------------------------------------------
# Multi-Agent Pipeline
# --------------------------------------------------

def run_jury(claim: str, truth: str, debate_rounds: int = 2) -> VerdictPayload:
    """Run the multi-agent jury to evaluate if a claim is faithful to the truth."""
    conversation = []

    # Stage 1: Evidence Scout analyzes the source truth
    print("Stage 1: Evidence Scout...")
    evidence = call_llm(
        EVIDENCE_SCOUT_PROMPT,
        f"SOURCE TRUTH:\n{truth}\n\nCLAIM being evaluated:\n{claim}",
        MODEL_FAST
    )
    conversation.append(AgentMessage(
        agent="Evidence Scout",
        message=evidence,
        timestamp=get_timestamp()
    ))

    # Stage 2: Debate Loop (Advocate vs Skeptic)
    print("Stage 2: Debate...")
    debate_history = ""

    for round_num in range(debate_rounds):
        print(f"  Round {round_num + 1}")

        # Advocate argues claim is faithful
        adv_prompt = f"""CLAIM:\n{claim}\n\nSOURCE TRUTH:\n{truth}\n\nEvidence:\n{evidence}\n\nDebate History:\n{debate_history}"""
        advocate_arg = call_llm(ADVOCATE_PROMPT, adv_prompt, MODEL_FAST)
        conversation.append(AgentMessage(
            agent="Advocate",
            message=advocate_arg,
            timestamp=get_timestamp()
        ))
        debate_history += f"\n[Advocate]: {advocate_arg}\n"

        # Skeptic argues claim is mutated
        skp_prompt = f"""CLAIM:\n{claim}\n\nSOURCE TRUTH:\n{truth}\n\nEvidence:\n{evidence}\n\nDebate History:\n{debate_history}"""
        skeptic_arg = call_llm(SKEPTIC_PROMPT, skp_prompt, MODEL_FAST)
        conversation.append(AgentMessage(
            agent="Skeptic",
            message=skeptic_arg,
            timestamp=get_timestamp()
        ))
        debate_history += f"\n[Skeptic]: {skeptic_arg}\n"

    # Stage 3: Fact-Checker provides neutral analysis
    print("Stage 3: Fact-Checker...")
    fact_check = call_llm(
        FACT_CHECKER_PROMPT,
        f"CLAIM:\n{claim}\n\nSOURCE TRUTH:\n{truth}\n\nEvidence:\n{evidence}\n\nDebate History:\n{debate_history}",
        MODEL_FAST
    )
    conversation.append(AgentMessage(
        agent="Fact-Checker",
        message=fact_check,
        timestamp=get_timestamp()
    ))

    # Stage 4: Judge makes final decision
    print("Stage 4: Judge...")
    judge_prompt = f"""
CLAIM:
{claim}

SOURCE TRUTH:
{truth}

Full Conversation:
{json.dumps([m.model_dump() for m in conversation], indent=2)}

Return JSON with "decision", "confidence", "summary", "disclaimers".
"""
    judge_result = get_json_response(JUDGE_PROMPT, judge_prompt, MODEL_JUDGE)

    if not judge_result:
        judge_result = {
            "decision": "uncertain",
            "confidence": 0.5,
            "summary": "The judge failed to produce a valid verdict.",
            "disclaimers": ["System Error"]
        }

    # Add judge to conversation
    conversation.append(AgentMessage(
        agent="Judge",
        message=judge_result.get("summary", ""),
        timestamp=get_timestamp()
    ))

    return VerdictPayload(
        claim=claim,
        truth=truth,
        conversation=conversation,
        summary=judge_result.get("summary", ""),
        decision=judge_result.get("decision", "uncertain").lower(),
        confidence=judge_result.get("confidence", 0.5),
        disclaimers=judge_result.get("disclaimers", [])
    )


def run_jury_streaming(claim: str, truth: str, debate_rounds: int = 2):
    """Generator that yields each agent message as it's generated for SSE streaming."""
    conversation = []

    # Stage 1: Evidence Scout analyzes the source truth
    print("Stage 1: Evidence Scout...")
    evidence = call_llm(
        EVIDENCE_SCOUT_PROMPT,
        f"SOURCE TRUTH:\n{truth}\n\nCLAIM being evaluated:\n{claim}",
        MODEL_FAST
    )
    msg = AgentMessage(agent="Evidence Scout", message=evidence, timestamp=get_timestamp())
    conversation.append(msg)
    yield {"type": "agent", "data": msg.model_dump()}

    # Stage 2: Debate Loop (Advocate vs Skeptic)
    print("Stage 2: Debate...")
    debate_history = ""

    for round_num in range(debate_rounds):
        print(f"  Round {round_num + 1}")

        # Advocate argues claim is faithful
        adv_prompt = f"""CLAIM:\n{claim}\n\nSOURCE TRUTH:\n{truth}\n\nEvidence:\n{evidence}\n\nDebate History:\n{debate_history}"""
        advocate_arg = call_llm(ADVOCATE_PROMPT, adv_prompt, MODEL_FAST)
        msg = AgentMessage(agent="Advocate", message=advocate_arg, timestamp=get_timestamp())
        conversation.append(msg)
        yield {"type": "agent", "data": msg.model_dump()}
        debate_history += f"\n[Advocate]: {advocate_arg}\n"

        # Skeptic argues claim is mutated
        skp_prompt = f"""CLAIM:\n{claim}\n\nSOURCE TRUTH:\n{truth}\n\nEvidence:\n{evidence}\n\nDebate History:\n{debate_history}"""
        skeptic_arg = call_llm(SKEPTIC_PROMPT, skp_prompt, MODEL_FAST)
        msg = AgentMessage(agent="Skeptic", message=skeptic_arg, timestamp=get_timestamp())
        conversation.append(msg)
        yield {"type": "agent", "data": msg.model_dump()}
        debate_history += f"\n[Skeptic]: {skeptic_arg}\n"

    # Stage 3: Fact-Checker provides neutral analysis
    print("Stage 3: Fact-Checker...")
    fact_check = call_llm(
        FACT_CHECKER_PROMPT,
        f"CLAIM:\n{claim}\n\nSOURCE TRUTH:\n{truth}\n\nEvidence:\n{evidence}\n\nDebate History:\n{debate_history}",
        MODEL_FAST
    )
    msg = AgentMessage(agent="Fact-Checker", message=fact_check, timestamp=get_timestamp())
    conversation.append(msg)
    yield {"type": "agent", "data": msg.model_dump()}

    # Stage 4: Judge makes final decision
    print("Stage 4: Judge...")
    judge_prompt = f"""
CLAIM:
{claim}

SOURCE TRUTH:
{truth}

Full Conversation:
{json.dumps([m.model_dump() for m in conversation], indent=2)}

Return JSON with "decision", "confidence", "summary", "disclaimers".
"""
    judge_result = get_json_response(JUDGE_PROMPT, judge_prompt, MODEL_JUDGE)

    if not judge_result:
        judge_result = {
            "decision": "uncertain",
            "confidence": 0.5,
            "summary": "The judge failed to produce a valid verdict.",
            "disclaimers": ["System Error"]
        }

    # Add judge to conversation
    msg = AgentMessage(agent="Judge", message=judge_result.get("summary", ""), timestamp=get_timestamp())
    conversation.append(msg)
    yield {"type": "agent", "data": msg.model_dump()}

    # Yield final verdict
    verdict = VerdictPayload(
        claim=claim,
        truth=truth,
        conversation=conversation,
        summary=judge_result.get("summary", ""),
        decision=judge_result.get("decision", "uncertain").lower(),
        confidence=judge_result.get("confidence", 0.5),
        disclaimers=judge_result.get("disclaimers", [])
    )
    yield {"type": "verdict", "data": verdict.model_dump()}

# --------------------------------------------------
# Load Cases from CSV
# --------------------------------------------------

def load_cases() -> list[CaseItem]:
    cases = []
    csv_path = os.path.join(os.path.dirname(__file__), "..", "Atlas.csv")

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                cases.append(CaseItem(
                    id=i + 1,
                    claim=row['claim'].strip(),
                    truth=row['truth'].strip()
                ))
    except FileNotFoundError:
        print(f"Warning: Atlas.csv not found at {csv_path}")

    return cases

# --------------------------------------------------
# FastAPI App
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Loading cases from Atlas.csv...")
    app.state.cases = load_cases()
    print(f"Loaded {len(app.state.cases)} cases")
    yield
    # Shutdown
    pass

app = FastAPI(
    title="FactTrace API",
    description="Multi-agent jury system for evaluating claim faithfulness",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for latest verdict
latest_verdict: Optional[VerdictPayload] = None

@app.get("/")
def root():
    return {"message": "FactTrace API", "docs": "/docs"}

@app.get("/api/cases", response_model=list[CaseItem])
def get_cases():
    """Get all claim/truth pairs from Atlas.csv"""
    return app.state.cases

@app.get("/api/cases/{case_id}", response_model=CaseItem)
def get_case(case_id: int):
    """Get a specific case by ID"""
    cases = app.state.cases
    if case_id < 1 or case_id > len(cases):
        raise HTTPException(status_code=404, detail="Case not found")
    return cases[case_id - 1]

@app.post("/api/verify", response_model=VerdictPayload)
def verify_claim(request: VerifyRequest):
    """Run the multi-agent jury on a claim/truth pair"""
    global latest_verdict

    result = run_jury(
        claim=request.claim,
        truth=request.truth,
        debate_rounds=request.debate_rounds
    )

    latest_verdict = result

    # Also save to result.json for frontend compatibility
    result_path = os.path.join(os.path.dirname(__file__), "..", "result.json")
    with open(result_path, 'w') as f:
        json.dump(result.model_dump(), f, indent=2)

    return result


@app.post("/api/verify/stream")
def verify_claim_stream(request: VerifyRequest):
    """Run the multi-agent jury with SSE streaming for real-time updates"""
    def event_generator():
        global latest_verdict
        for event in run_jury_streaming(
            claim=request.claim,
            truth=request.truth,
            debate_rounds=request.debate_rounds
        ):
            if event["type"] == "verdict":
                latest_verdict = VerdictPayload(**event["data"])
                # Save to result.json
                result_path = os.path.join(os.path.dirname(__file__), "..", "result.json")
                with open(result_path, 'w') as f:
                    json.dump(event["data"], f, indent=2)

            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/verdict", response_model=VerdictPayload)
def get_verdict():
    """Get the latest verdict (for frontend polling)"""
    global latest_verdict

    # Try reading from file first
    result_path = os.path.join(os.path.dirname(__file__), "..", "result.json")
    try:
        with open(result_path, 'r') as f:
            data = json.load(f)
            return VerdictPayload(**data)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if latest_verdict:
        return latest_verdict

    raise HTTPException(status_code=404, detail="No verdict available")

@app.post("/api/verdict")
def post_verdict(payload: VerdictPayload):
    """Store a verdict (for compatibility with frontend)"""
    global latest_verdict
    latest_verdict = payload

    result_path = os.path.join(os.path.dirname(__file__), "..", "result.json")
    with open(result_path, 'w') as f:
        json.dump(payload.model_dump(), f, indent=2)

    return {"success": True, "message": "Verdict received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
