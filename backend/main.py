import os
import json
import csv
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Majority vote configuration
NUM_JUDGES = 10

# --------------------------------------------------
# Agent Prompts
# --------------------------------------------------

CLAIM_ANALYSIS_PROMPT = """
You are a Claim Analyst.
Your goal is to analyze the claim IN ISOLATION.
This means that if any information is ambiguous or unnamed, you should point it out.
For example "the video" or "it is", without actually having named an object, is ambiguous.

Instructions:
1. Identify what is explicitly stated vs. what is implied.
2. Highlight any specific numbers, dates, or entities.
3. Note if the claim is missing context (e.g., "The video" - which video?).
4. Do NOT verify the truth. Just analyze the claim's content and structure.
5. Be CONCISE (max 3-4 bullet points).
6. Use **bold** for key terms.
"""

TRUTH_ANALYSIS_PROMPT = """
You are a Truth Analyst.
Your goal is to analyze the Reference Statement (Source Truth) IN ISOLATION.
This means that if any information is ambiguous or unnamed, you should point it out.
For example "the video" or "it is", without actually having named an object, is ambiguous.

Instructions:
1. Identify what is explicitly stated vs. what is implied in the statement.
2. Highlight any specific numbers, dates, qualifiers (e.g. "over", "approximately"), or entities.
3. Analyze the statement's structure and scope.
4. Do NOT verify if it is correct vs external reality. Just analyze the text provided.
5. Be CONCISE (max 3-4 bullet points).
6. Use **bold** for key terms.
"""

ADVOCATE_PROMPT = """
You are an Advocate.
Your goal is to argue that the claim is faithful to the truth.

Instructions:
1. Use the provided Source Truth and the Pre-Analysis.
2. Read the Debate History to see what the Skeptic has said.
3. Directly address the Skeptic's points if they have spoken.
4. Strengthen your case for why the claim is true or faithful.
5. **CRITICAL**: Limit your response to ONE PARAGRAPH (max 100 words).
6. Use **bold** to highlight your strongest point or key evidence.
"""

SKEPTIC_PROMPT = """
You are a Skeptic.
Your goal is to argue that the claim is misleading, mutated, or false.

Instructions:
1. Use the provided Source Truth and the Pre-Analysis.
2. Read the Debate History to see what the Advocate has said.
3. Directly address the Advocate's points if they have spoken.
4. Point out logical leaps, missing context, or specific contradictions.
5. **CRITICAL**: Limit your response to ONE PARAGRAPH (max 100 words).
6. Use **bold** to highlight the biggest flaw or contradiction.
"""

MEDIATOR_PROMPT = """
You are a Mediator.
Your goal is to keep the debate focused and constructive.

Instructions:
1. Review the Advocate and Skeptic arguments.
2. If they are getting stuck on minor semantics (e.g. "which video?"), intervene.
3. Suggest a reasonable assumption to move forward (e.g. "Let's assume we are discussing the primary video").
4. If the debate is healthy, just provide a neutral 1-sentence synthesis.
5. **CRITICAL**: Max 1-2 sentences. Fact-check their logic if needed.
"""

FACT_CHECKER_PROMPT = """
You are a Fact-Checker.
Your goal is to provide a neutral, objective verification of the claim based on the truth and debate.

Instructions:
1. Review the Source Truth and the Debate History.
2. Assess whether the claim matches the specific facts in the truth text.
3. Provide a SHORT summary verification (max 3-4 sentences).
4. Use **bold** for your final verdict keyword (e.g. **Supported**, **Misleading**, **Unproven**).
"""

JUDGE_PROMPT = """
You are a Judge.

Use the conversation, the Pre-Analysis, and the Source Truth to reach a verdict.

Decide whether the claim is:
- FAITHFUL (The claim accurately represents the truth/facts. Minor simplifications are okay if the essence is preserved.)
- MUTATED (The claim distorts, exaggerates, omits key qualifiers, or misrepresents the facts.)
- UNCERTAIN (Only use this if there is NO relevant evidence or the truth is genuinely ambiguous.)

**CRITICAL INSTRUCTION**:
You MUST choose between FAITHFUL or MUTATED if possible. Avoid UNCERTAIN unless absolutely necessary.
If the claim changes "over 3.7 billion" to "3.7 billion", ask yourself: Does this materially mislead?
If the claim implies a false context, it is MUTATED.

Output VALID JSON (no markdown) with this structure:
{
  "decision": "faithful" | "mutated" | "uncertain",
  "confidence": 0.0 to 1.0,
  "summary": "5-7 sentences explaining the verdict...",
  "disclaimers": ["list", "of", "important", "caveats"]
}
"""

# --------------------------------------------------
# Pydantic Models
# --------------------------------------------------

class VerifyRequest(BaseModel):
    claim: str
    truth: str
    debate_rounds: int = 2

class AgentMessage(BaseModel):
    agent: str
    message: str
    timestamp: Optional[str] = None

class AnalysisResult(BaseModel):
    claim_analysis: str
    truth_analysis: str

class VerdictPayload(BaseModel):
    claim: str
    truth: str
    conversation: list[AgentMessage]
    summary: str
    decision: str
    confidence: Optional[float] = None
    disclaimers: Optional[list[str]] = None
    analysis: Optional[AnalysisResult] = None
    vote_breakdown: Optional[dict[str, int]] = None

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
# Majority Vote Judging
# --------------------------------------------------

def aggregate_verdicts(verdicts: list[dict]) -> dict:
    """Aggregate multiple judge verdicts into a majority vote decision."""
    votes = {"faithful": 0, "mutated": 0, "uncertain": 0}
    summaries_by_decision = {"faithful": [], "mutated": [], "uncertain": []}
    all_disclaimers = set()

    for v in verdicts:
        decision = v.get("decision", "uncertain").lower()
        if decision not in votes:
            decision = "uncertain"
        votes[decision] += 1
        summaries_by_decision[decision].append(v.get("summary", ""))
        for d in v.get("disclaimers", []):
            all_disclaimers.add(d)

    # Get majority decision
    majority_decision = max(votes, key=votes.get)
    majority_count = votes[majority_decision]

    # Use first summary from majority voters
    majority_summaries = summaries_by_decision[majority_decision]
    representative_summary = majority_summaries[0] if majority_summaries else "No summary available"

    return {
        "decision": majority_decision,
        "confidence": majority_count / len(verdicts),
        "summary": representative_summary,
        "disclaimers": list(all_disclaimers),
        "vote_breakdown": votes
    }


def run_majority_vote_judgment(claim: str, truth: str, conversation: list, common_context: str) -> dict:
    """Run 10 judges in parallel and aggregate by majority vote."""
    judge_prompt = f"""
    {common_context}

    Full Conversation:
    {json.dumps([m.model_dump() for m in conversation], indent=2)}

    Return JSON with "decision", "confidence", "summary", "disclaimers".
    """

    def call_single_judge(judge_id: int) -> dict:
        print(f"  Judge {judge_id + 1} voting...")
        result = get_json_response(JUDGE_PROMPT, judge_prompt, MODEL_FAST, temperature=0.95)
        if not result:
            return {"decision": "uncertain", "confidence": 0.5, "summary": "Judge failed", "disclaimers": []}
        return result

    # Run all judges in parallel
    verdicts = []
    with ThreadPoolExecutor(max_workers=NUM_JUDGES) as executor:
        futures = [executor.submit(call_single_judge, i) for i in range(NUM_JUDGES)]
        for future in as_completed(futures):
            verdicts.append(future.result())

    return aggregate_verdicts(verdicts)


# --------------------------------------------------
# Multi-Agent Pipeline
# --------------------------------------------------

def run_jury(claim: str, truth: str, debate_rounds: int = 3) -> VerdictPayload:
    """Run the multi-agent jury to evaluate if a claim is faithful to the truth."""
    conversation = []

    # Stage 0.5: Pre-Analysis
    print("Stage 0.5: Pre-Analysis...")

    # Analyze Claim
    claim_analysis = call_llm(
        CLAIM_ANALYSIS_PROMPT,
        f"Claim to Analyze:\n{claim}",
        MODEL_FAST
    )

    # Analyze Truth
    truth_analysis = call_llm(
        TRUTH_ANALYSIS_PROMPT,
        f"Source Truth to Analyze:\n{truth}",
        MODEL_FAST
    )

    # We add Evidence Scout message just to show the Truth has been "gathered" (passed in)
    conversation.append(AgentMessage(agent="Evidence Scout", message=truth_analysis, timestamp=get_timestamp()))

    # Stage 2: Debate Loop (Advocate vs Skeptic)
    print("Stage 2: Debate...")
    debate_history = ""

    common_context = f"""
    Claim: {claim}
    Source Truth: {truth}

    PRE-ANALYSIS:
    [Claim Analysis]:
    {claim_analysis}

    [Truth Analysis]:
    {truth_analysis}
    """

    for round_num in range(debate_rounds):
        print(f"  Round {round_num + 1}")

        # Advocate argues claim is faithful
        adv_prompt = f"{common_context}\n\nDebate History:\n{debate_history}"
        advocate_arg = call_llm(ADVOCATE_PROMPT, adv_prompt, MODEL_FAST)
        conversation.append(AgentMessage(
            agent="Advocate",
            message=advocate_arg,
            timestamp=get_timestamp()
        ))
        debate_history += f"\n[Advocate]: {advocate_arg}\n"

        # Skeptic argues claim is mutated
        skp_prompt = f"{common_context}\n\nDebate History:\n{debate_history}"
        skeptic_arg = call_llm(SKEPTIC_PROMPT, skp_prompt, MODEL_FAST)
        conversation.append(AgentMessage(
            agent="Skeptic",
            message=skeptic_arg,
            timestamp=get_timestamp()
        ))
        debate_history += f"\n[Skeptic]: {skeptic_arg}\n"

        # Mediator Interjects
        med_prompt = f"{common_context}\n\nDebate History:\n{debate_history}"
        mediator_arg = call_llm(MEDIATOR_PROMPT, med_prompt, MODEL_FAST)
        conversation.append(AgentMessage(
            agent="Mediator",
            message=mediator_arg,
            timestamp=get_timestamp()
        ))
        debate_history += f"\n[Mediator]: {mediator_arg}\n"

    # Stage 3: Fact-Checker provides neutral analysis
    print("Stage 3: Fact-Checker...")
    fact_check = call_llm(
        FACT_CHECKER_PROMPT,
        f"{common_context}\n\nDebate History:\n{debate_history}",
        MODEL_FAST
    )
    conversation.append(AgentMessage(
        agent="Fact-Checker",
        message=fact_check,
        timestamp=get_timestamp()
    ))

    # Stage 4: Jury Vote (10 judges)
    print("Stage 4: Jury Vote (10 judges)...")
    judge_result = run_majority_vote_judgment(claim, truth, conversation, common_context)

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
        disclaimers=judge_result.get("disclaimers", []),
        analysis={
            "claim_analysis": claim_analysis,
            "truth_analysis": truth_analysis
        },
        vote_breakdown=judge_result.get("vote_breakdown")
    )


def run_jury_streaming(claim: str, truth: str, debate_rounds: int = 2):
    """Generator that yields each agent message as it's generated for SSE streaming."""
    conversation = []

    # Stage 0.5: Pre-Analysis
    print("Stage 0.5: Pre-Analysis...")

    # Analyze Claim
    claim_analysis = call_llm(
        CLAIM_ANALYSIS_PROMPT,
        f"Claim to Analyze:\n{claim}",
        MODEL_FAST
    )

    # Analyze Truth
    truth_analysis = call_llm(
        TRUTH_ANALYSIS_PROMPT,
        f"Source Truth to Analyze:\n{truth}",
        MODEL_FAST
    )

    # Yield unique analysis event
    analysis_data = AnalysisResult(claim_analysis=claim_analysis, truth_analysis=truth_analysis)
    yield {"type": "analysis", "data": analysis_data.model_dump()}

    # Yield truth analysis as an evidence scout message to show progress
    msg = AgentMessage(agent="Evidence Scout", message=truth_analysis, timestamp=get_timestamp())
    conversation.append(msg)
    yield {"type": "agent", "data": msg.model_dump()}

    # Stage 2: Debate Loop (Advocate vs Skeptic)
    print("Stage 2: Debate...")
    debate_history = ""

    common_context = f"""
    Claim: {claim}
    Source Truth: {truth}

    PRE-ANALYSIS:
    [Claim Analysis]:
    {claim_analysis}

    [Truth Analysis]:
    {truth_analysis}
    """

    for round_num in range(debate_rounds):
        print(f"  Round {round_num + 1}")

        # Advocate
        adv_prompt = f"{common_context}\n\nDebate History:\n{debate_history}"
        advocate_arg = call_llm(ADVOCATE_PROMPT, adv_prompt, MODEL_FAST)
        msg = AgentMessage(agent="Advocate", message=advocate_arg, timestamp=get_timestamp())
        conversation.append(msg)
        yield {"type": "agent", "data": msg.model_dump()}
        debate_history += f"\n[Advocate]: {advocate_arg}\n"

        # Skeptic
        skp_prompt = f"{common_context}\n\nDebate History:\n{debate_history}"
        skeptic_arg = call_llm(SKEPTIC_PROMPT, skp_prompt, MODEL_FAST)
        msg = AgentMessage(agent="Skeptic", message=skeptic_arg, timestamp=get_timestamp())
        conversation.append(msg)
        yield {"type": "agent", "data": msg.model_dump()}
        debate_history += f"\n[Skeptic]: {skeptic_arg}\n"

        # Mediator
        med_prompt = f"{common_context}\n\nDebate History:\n{debate_history}"
        mediator_arg = call_llm(MEDIATOR_PROMPT, med_prompt, MODEL_FAST)
        msg = AgentMessage(agent="Mediator", message=mediator_arg, timestamp=get_timestamp())
        conversation.append(msg)
        yield {"type": "agent", "data": msg.model_dump()}
        debate_history += f"\n[Mediator]: {mediator_arg}\n"

    # Stage 3: Fact-Checker
    print("Stage 3: Fact-Checker...")
    fact_check = call_llm(
        FACT_CHECKER_PROMPT,
        f"{common_context}\n\nDebate History:\n{debate_history}",
        MODEL_FAST
    )
    msg = AgentMessage(agent="Fact-Checker", message=fact_check, timestamp=get_timestamp())
    conversation.append(msg)
    yield {"type": "agent", "data": msg.model_dump()}

    # Stage 4: Jury Vote (10 judges)
    print("Stage 4: Jury Vote (10 judges)...")
    judge_result = run_majority_vote_judgment(claim, truth, conversation, common_context)

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
        disclaimers=judge_result.get("disclaimers", []),
        analysis={
            "claim_analysis": claim_analysis,
            "truth_analysis": truth_analysis
        },
        vote_breakdown=judge_result.get("vote_breakdown")
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
