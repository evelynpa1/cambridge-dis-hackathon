# FactTrace Hackathon @ University of Cambridge
## 🧠 Agentic AI Jury Hackathon
Welcome to the AI Jury Hackathon!

In this hackathon, you’ll design a jury of AI agents that evaluates whether a statement faithfully represents a given fact or mutates it.
This is a fast, hands-on challenge focused on reasoning, disagreement, and trust, not infrastructure or large-scale systems.


## Contents
- [Challenge](#challenge)
- [Judging Criteria](#judging-criteria)
- [Important Question](#important-question)
- [Possible Extension Direction](#possible-extension-direction)
- [Getting Started](#getting-started)
- [API Keys](#api-keys)


## Challenge
### 🚩 The Core Problem
You will be given pairs of statements:
1. Internal Fact
A factual statement (e.g. from a report, paper, dataset, or trusted source)

2. External Interpretation
A statement derived from that fact (e.g. a summary, headline, tweet, or claim)

#### Your task is to answer:
> **Is the external claim a faithful representation of the internal fact — or a mutation?**

This is harder than it sounds. Mutations can happen in many ways, including but not limited to:

Most cases are borderline by design.
People can disagree on whether the meaning has changed.

### What Counts as a “Mutation”?

Mutations can be **subtle**, including:

- **Shifts in certainty or commitment**  
- **Numerical rounding or threshold changes**  
- **Scope or population drift**  
- **Causality vs. correlation confusion**  
- **Changes in tone, strength, or implication**  
- **Missing qualifiers or conditions**

**Please note:**

- **Most cases are borderline by design.**  
  Reasonable people often disagree.
- **There is no single ground truth.**
- **Your agentic jury must reason — not just classify.**
--

## ⚖️ Build an AI Jury

You will design a **multi-agent system** — an AI jury.

A valid jury:

- Has multiple agents with **distinct roles**
- Allows agents to **analyze, disagree, and refine**

It must produce:

- A verdict  
- An explanation  
- A signal of uncertainty  

🚫 A single LLM call in a loop is not sufficient.


This is not about being **“right at all costs.”**  It is about reasoning **transparently and responsibly** to reach the verdict. 

---
### 🏁 Data Access

You do **not** need to use all the data.

All teams must use the **official FactTrace hackathon dataset**, which contains
high-ambiguity (fact, claim) pairs designed to test subtle semantic mutations.



Instead, teams must:

1. Select a specific subset of the dataset
2. Justify why that subset is interesting or difficult
3. Apply multi-agent reasoning to it
   
Recommended subset size
- 10-20 claim pairs
  
Example valid subsets
- One domain (e.g. clinical, business, policy)
- One mutation type (e.g. numerical rounding, modality shift)
- One high-ambiguity subset (explicitly labeled in the CSV)
  
📁 The dataset is pre-categorized by:
- Domain
- Mutation type
- Ambiguity level
- High-ambiguity subset
  
Use these categories strategically. The dataset can be accessed [here](HackathonData.tsv)

---
### 🏁 Expected Output

By the end of the hackathon, your team must be able to:

- Demo a working AI jury built using multiple agents  
- Show how agents reason, including where they agree or disagree  
- Evaluate up to 5 (fact, claim) pairs, producing for each:
  - A final verdict  
  - A concise, human-readable explanation  
- Demonstrate that the approach generalizes beyond the presented examples  
  (i.e., it is not hard-coded to specific cases)
- Explicitly communicate uncertainty whenever the evidence or agent reasoning is inconclusive  



### Demos can be:
- CLI output  
- Notebook  
- Minimal UI  

> *Simple is great - clarity matters more than polish.*

### The 5-Minute Demo Rule ⏱️

Your solution should be understandable in 5 minutes or less.

A strong demo typically shows:

1. **The chosen data subset**  
2. **Agent roles and interactions**  
3. **Up to five concrete claim evaluations**  
4. **Where agents agree, disagree, or defer**  
5. **How the system generalizes beyond the examples**

If it can’t be explained in **5 minutes**, it’s probably too complex.

---

## Judging Criteria

Projects will be judged on:

### Agent Design (30%) 🧠 
- Clear, purposeful agent roles
- Meaningful interaction (not just chaining)
- Evidence of added value vs single-agent baseline
### Reasoning & Explanation (30%) 🧾
- Clear, honest explanations
- Explicit handling of uncertainty
- Insight into why a case is hard
### Data Understanding (20%) 🔍
- Thoughtful subset selection
- Correct identification of mutation types
- Awareness of ambiguity
### Demo Clarity (20%) 🎤
- Clear structure
- Easy to follow
- Teaches the judges something

We care more about **good reasoning** than perfect answers.

### A golden solution is:
- Clearly better than a single-agent baseline  
- Understandable in a 5-minute demo  
- Teaches you something about multi-agent value  
- Handles uncertainty responsibly  

---

## Important Question

During your demo, be prepared to answer:

> **What did using multiple agents add compared to a single AI call?**

There is no “correct” answer — **thoughtful reflections are highly valued**.

---

## Possible Extension Direction

Beyond defining agent roles, one way to extend your jury’s capabilities is by giving agents access to **tools** — either by creating simple custom tools or by integrating existing ones.

If you choose to explore this path, you may find the **Model Context Protocol (MCP)** useful.

That said, tooling is optional. Extensions can take many forms, and you are encouraged to explore any idea that can improve your jury system.

---

## ⏱️ Timebox & Mindset

This is a short, intense hackathon.

Aim for:

- A working prototype  
- One strong idea  
- A clear demo  

---

## Getting Started

Ready to build? Here is everything you need to set up your environment, choose your tools, and manage your API usage.

---

### 1. The Repository

Everything you need to begin—including the required datasets, skeleton files, and setup instructions—is in the official hackathon repository.

👉 **Fork the Repository on GitHub**

All teams are expected to build on top of this repository to ensure a consistent baseline for evaluation.

---

### 2. Multi-Agent Frameworks

You are free to use any **Multi-Agent System (MAS)** framework you prefer, such as:

- AutoGen  
- CrewAI  
- LangGraph  

If you are new to building agents, we recommend **LangChain**.

**Why?**  
It makes composing agents quick and intuitive.

📚 **Docs:** [LangChain Documentation](https://docs.langchain.com)

---

## API Keys
> _(Loubna and James to review — feel free to change this part as necessary)_

To access the LLM services required for your agents, you will use your own API keys. We recommend **OpenAI** for its ease of use and documentation, though you are free to use **Anthropic**, **Gemini**, or others.

💰 **Reimbursement Policy**  
We will reimburse API costs incurred during the event up to **£[X] per team**.  
Please save your usage receipts or screenshots for submission at the end of the event.

📉 **Tips to keep costs low:**

- **Use efficient models:**  
  Start with cheaper models (e.g., `gpt-5-nano` or `gpt-5-mini`) for testing, and only switch to flagship models (e.g., `gpt-5`) for final, distinct tasks.
- **Limit your Jury:**  
  When testing, reduce the number of agents in your loop.
- **Watch the loop:**  
  Ensure your code has clear *exit conditions* to avoid infinite retry loops that drain credits.
- **Set hard limits:**  
  Configure a hard budget limit in your API provider’s dashboard to prevent accidental overspending.

---

## 🎯 Final Thought

Facts rarely break in obvious ways.  
They often break through **interpretation**.

Your job is to design an AI system that notices when that happens.

**Good luck — and have fun building your jury.**
