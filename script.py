import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

# --------------------------------------------------
# Setup
# --------------------------------------------------

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_FAST = "gpt-4.1-mini"
MODEL_JUDGE = "gpt-5.2"

# --------------------------------------------------
# LLM helper
# --------------------------------------------------

def call_llm(system_prompt, user_prompt, model, temperature=0.3):
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()

def get_json_response(system_prompt, user_prompt, model, temperature=0.2, max_retries=3):
    """
    Tries to get a valid JSON response from the LLM.
    Retries with an added instruction if parsing fails.
    """
    current_user_prompt = user_prompt
    
    for attempt in range(max_retries):
        content = call_llm(system_prompt, current_user_prompt, model, temperature)
        
        # Try to clean up markdown fences if present
        cleaned_content = content
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        
        cleaned_content = cleaned_content.strip()
        
        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"JSON extract failed (attempt {attempt+1}): {e}")
            # Add a nudge to the user prompt for the next attempt
            current_user_prompt = user_prompt + f"\n\nERROR: The previous response was not valid JSON. Please return ONLY a valid JSON object. Do not wrap in markdown blocks.\nPrevious invalid output:\n{content[:200]}..."
            time.sleep(1)
            
    # Fallback if all retries fail
    print("Failed to get valid JSON after retries.")
    return None

# --------------------------------------------------
# Agent system prompts
# --------------------------------------------------

META_CONTROLLER_PROMPT = """
You are a Meta-Controller agent.

Your job is to classify the type of claim and assign trust weights
to agent roles based on epistemic usefulness.

Rules:
- Advocate and Skeptic MUST have equal weight.
- Total weights should sum to approx 1.0 (normalization will happen later, but try to be close).
- Prefer Evidence Scout and Fact-Checker for scientific claims.
- Prefer Context Analyst for political or social claims.

Make sure to output VALID JSON with keys: "claim_type", "weights", "rationale".
Do NOT output markdown formatting like ```json ... ```. Just the raw JSON string.
"""

EVIDENCE_SCOUT_PROMPT = """
You are an Evidence Scout.
Your goal is to gather facts, statistics, and context about the claim.

Instructions:
1. Identify key entities, dates, and statistics in the claim.
2. Search for or simulate retrieving evidence from reputable sources.
3. Classify evidence as:
   - Supporting
   - Conflicting
   - Neutral
4. Be CONCISE. Use max 3-4 bullet points per section.
5. Use **bold** for key statistics, source names, and important entities.
6. Provide a "Context/Nuance" section if the claim misses important details.
"""

CLAIM_ANALYSIS_PROMPT = """
You are a Claim Analyst.
Your goal is to analyze the claim IN ISOLATION.

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
Your goal is to analyze the Source Truth IN ISOLATION.

Instructions:
1. Identify the key facts available in the evidence/truth text.
2. Highlight any qualifiers (e.g., "over", "approximately", "at least").
3. Note specific dates, numbers, and entities.
4. Do NOT compare it to the claim yet. Just extract the core truth.
5. Be CONCISE (max 3-4 bullet points).
6. Use **bold** for key terms.
"""

ADVOCATE_PROMPT = """
You are an Advocate.
Your goal is to argue that the claim is faithful to the truth.

Instructions:
1. Use the provided Evidence and the Pre-Analysis (Claim vs Truth).
2. Read the Debate History to see what the Skeptic has said.
3. Directly address the Skeptic's points if they have spoken.
4. Strengthen your case for why the claim is true or faithful.
5. **CRITICAL**: Limit your response to ONE PARAGRAPH (max 100 words).
6. Use **bold** to highlight your strongest point or key evidence.
7. Be persuasive but grounded in the facts.
"""

SKEPTIC_PROMPT = """
You are a Skeptic.
Your goal is to argue that the claim is misleading, mutated, or false.

Instructions:
1. Use the provided Evidence and the Pre-Analysis (Claim vs Truth).
2. Read the Debate History to see what the Advocate has said.
3. Directly address the Advocate's points if they have spoken.
4. Point out logical leaps, missing context, or specific contradictions in the claim.
5. **CRITICAL**: Limit your response to ONE PARAGRAPH (max 100 words).
6. Use **bold** to highlight the biggest flaw or contradiction.
7. Be critical but fair based on the evidence.
"""

FACT_CHECKER_PROMPT = """
You are a Fact-Checker.
Your goal is to provide a neutral, objective verification of the claim based on the evidence and debate.

Instructions:
1. Review the Evidence and the Debate History.
2. Assess the Source Quality (are the sources credible and diverse?).
3. Evaluate Measurement Validity (do the metrics actually support the claim?).
4. Provide a SHORT summary verification (max 3-4 sentences).
5. Use **bold** for your final verdict keyword (e.g. **Supported**, **Misleading**, **Unproven**) and key findings.
"""

CONTEXT_ANALYST_PROMPT = """
You are a Context Analyst.
Evaluate whether context, framing, or historical background
changes how the claim should be interpreted.
"""

JUDGE_PROMPT = """
You are a Judge.

Use the conversation, the Pre-Analysis, and the evidence to reach a verdict.

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
# Main pipeline
# --------------------------------------------------

def verify_claim(claim: str) -> dict:
    conversation = []

    # ---- Stage 0: Meta-controller
    print("Stage 0: Meta-Controller...")
    meta_user_msg = f"""
        Claim:
        {claim}

        Return JSON of the form:
        {{
        "claim_type": "...",
        "weights": {{
            "evidence_scout": 0.xx,
            "fact_checker": 0.xx,
            "advocate": 0.xx,
            "skeptic": 0.xx,
            "context_analyst": 0.xx
        }},
        "rationale": "..."
        }}
    """
    meta = get_json_response(META_CONTROLLER_PROMPT, meta_user_msg, MODEL_FAST)
    if not meta:
        # Fallback default
        meta = {
             "claim_type": "General", 
             "weights": {"evidence_scout": 0.2, "fact_checker": 0.2, "advocate": 0.2, "skeptic": 0.2, "context_analyst": 0.2}, 
             "rationale": "Fallback due to JSON error."
        }

    # Enforce advocate/skeptic equality (safety)
    if "weights" in meta:
        w = meta["weights"]
        adv = w.get("advocate", 0.2)
        skp = w.get("skeptic", 0.2)
        avg = (adv + skp) / 2
        w["advocate"] = avg
        w["skeptic"] = avg
    else:
        # Fallback weights if key missing
        meta["weights"] = {"evidence_scout": 0.2, "fact_checker": 0.2, "advocate": 0.2, "skeptic": 0.2, "context_analyst": 0.2}
        w = meta["weights"]

    # Formatting conversation for frontend: AgentMessage
    # We will store raw info in `conversation` list and transform it at the end, 
    # but we can also append formatted dicts if we want. 
    # Let's keep the internal structure simple and map it later, 
    # but strictly speaking the user wants "conversation" in result.
    
    # We'll just append dicts that look like the frontend expects OR contain enough info.
    # Frontend expects: { agent, message, timestamp? }
    
    import datetime
    def get_time():
        return datetime.datetime.now().strftime("%H:%M:%S")

    # Let's exclude Meta from the visible conversation or add it as "System".
    # conversation.append({"agent": "Meta Controller", "message": f"Assigned weights: {json.dumps(w)}", "timestamp": get_time()})

    # ---- Stage 1: Evidence Scout
    print("Stage 1: Evidence Scout...")
    evidence = call_llm(EVIDENCE_SCOUT_PROMPT, f"Claim: {claim}\nGather evidence to verify this.", MODEL_FAST)
    # Use the evidence as the "Truth/Facts" for this debate
    truth_text = evidence 
    
    # ---- New Stage: Pre-Analysis ----
    print("Stage 0.5: Pre-Analysis...")
    
    claim_analysis = call_llm(
        CLAIM_ANALYSIS_PROMPT,
        f"Claim to Analyze:\n{claim}",
        MODEL_FAST
    )
    
    truth_analysis = call_llm(
        TRUTH_ANALYSIS_PROMPT,
        f"Source Truth to Analyze:\n{truth_text}",
        MODEL_FAST
    )

    # ---- Stage 2: Debate Loop ----
    conversation = []
    conversation.append({"agent": "Evidence Scout", "message": evidence, "timestamp": datetime.datetime.now().strftime("%H:%M:%S")})
    
    # Updated context includes the Analysis
    common_context = f"""
    Claim: {claim}
    Evidence/Truth: {truth_text}
    
    PRE-ANALYSIS (Use this to guide your arguments):
    [Claim Analysis]:
    {claim_analysis}
    
    [Truth Analysis]:
    {truth_analysis}
    
    Debate History:
    """
    debate_rounds = 4
    debate_history = ""
    
    for i in range(debate_rounds):
        round_name = f"Round {i+1}"
        print(f"  - {round_name}")
        
        # Advocate Turn
        adv_prompt = f"{common_context}\n{debate_history}"
        advocate_arg = call_llm(ADVOCATE_PROMPT, adv_prompt, MODEL_FAST)
        
        conversation.append({"agent": "Advocate", "message": advocate_arg, "timestamp": get_time()})
        debate_history += f"\n[Advocate]: {advocate_arg}\n"

        # Skeptic Turn
        skp_prompt = f"{common_context}\n{debate_history}"
        skeptic_arg = call_llm(SKEPTIC_PROMPT, skp_prompt, MODEL_FAST)
        
        conversation.append({"agent": "Skeptic", "message": skeptic_arg, "timestamp": get_time()})
        debate_history += f"\n[Skeptic]: {skeptic_arg}\n"

    # ---- Stage 3: Fact-checker
    print("Stage 3: Fact-Checker...")
    fact_checker = call_llm(
        FACT_CHECKER_PROMPT,
        f"Claim:\n{claim}\n\nEvidence:\n{evidence}",
        MODEL_FAST,
    )
    conversation.append({"agent": "Fact-Checker", "message": fact_checker, "timestamp": get_time()})

    # ---- Stage 4: Context (optional but cheap)
    print("Stage 4: Context Analyst...")
    context = call_llm(
        CONTEXT_ANALYST_PROMPT,
        f"Claim:\n{claim}",
        MODEL_FAST,
    )
    conversation.append({"agent": "Context Analyst", "message": context, "timestamp": get_time()})

    # ---- Stage 5: Judge
    print("Stage 5: Judge...")
    judge_prompt_user = f"""
        Claim:
        {claim}

        Trust Weights:
        {json.dumps(w, indent=2)}

        Pre-Analysis:
        [Claim Analysis]:
        {claim_analysis}
        [Truth Analysis]:
        {truth_analysis}

        Full Conversation:
        {json.dumps(conversation, indent=2)}

        Return JSON with "decision", "confidence", "summary", "disclaimers".
    """
    judge = get_json_response(JUDGE_PROMPT, judge_prompt_user, MODEL_JUDGE)
    if not judge:
        judge = {
            "decision": "uncertain",
            "confidence": 0.0,
            "summary": "The judge failed to produce a valid verdict.",
            "disclaimers": ["System Error"]
        }
    
    # Append Judge verdict to conversation as well, as seen in sample
    conversation.append({"agent": "Judge", "message": judge.get("summary", ""), "timestamp": get_time()})

    # ---- Final output matching VerdictPayload interface
    # interface VerdictPayload {
    #   claim: string;
    #   truth: string;     # Note: The frontend uses 'truth' field for the "Official Truth" or "Facts". 
    #                      # But here we only have the evidence. We can map "evidence" to "truth" or just leave it empty if we don't have a ground truth string.
    #                      # In the sample, "truth" looks like a factual blurb. Let's use the summary of evidence or just the claim explanation.
    #                      # Actually, let's use the "Evidence Scout" output as the "truth" / "facts" basis? Or just "N/A" if unknown.
    #                      # The user prompt had "claim, truth" in csv. Maybe we should read truth from input?
    #                      # For now, let's just put the Evidence Scout summary as "truth" approx.
    #   conversation: AgentMessage[];
    #   summary: string;
    #   decision: 'faithful' | 'mutated' | 'uncertain';
    #   confidence?: number;
    # }

    return {
        "claim": claim,
        "truth": evidence, # Using evidence as the "Truth/Facts" context
        "analysis": {
            "claim_analysis": claim_analysis,
            "truth_analysis": truth_analysis
        },
        "conversation": conversation,
        "summary": judge.get("summary", ""),
        "decision": judge.get("decision", "uncertain").lower(),
        "confidence": judge.get("confidence", 0.5),
        "disclaimers": judge.get("disclaimers", [])
    }
# --------------------------------------------------
# Example
# --------------------------------------------------

if __name__ == "__main__":
    CLAIM = "Remote work increases productivity by over 10%."
    print(f"Verifying Claim: {CLAIM}")
    result = verify_claim(CLAIM)
    
    print("\nFINAL JSON OUTPUT:")
    print(json.dumps(result, indent=2))
    
    # Save to result.json
    with open("result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nSaved to result.json")
