# FactTrace Hackathon @ University of Cambridge
## 🧠 Agentic AI Jury Hackathon
Welcome to the AI Jury Hackathon!

In this hackathon, you’ll design a jury of AI agents that evaluates whether a statement faithfully represents a given fact or mutates it.
This is a fast, hands-on challenge focused on reasoning, disagreement, and trust, not infrastructure or large-scale systems.

## Contents
[Challenge](#challenge)\
[Judging Criteria](#-judging-criteria)\
[Important Question](#-important-question)\
[Possible Extension Direction](#-possible-extension-direction)\
[Getting Started](#-getting-started)\
[API Keys](#api-keys)

## Challenge
### 🚩 The Core Problem
You will be given pairs of statements:
1. Internal Fact
A factual statement (e.g. from a report, paper, dataset, or trusted source)

2. External Interpretation
A statement derived from that fact (e.g. a summary, headline, tweet, or claim)

#### Your task is to answer:
> **Is the external interpretation a faithful representation of the internal fact, or is it a mutation?**

This is harder than it sounds. Mutations can happen in many ways, including but not limited to:

- Missing context or qualifiers  
- Over-generalization  
- Changes in tone or implication  
- Shifts in scope or certainty  

---

### ⚖️ Build an AI Jury

You will design a **multi-agent system** - an *AI jury*.

Given a *(fact, interpretation)* pair, your jury must:

- Reach a verdict  
- Explain its reasoning  
- Know when it is uncertain  

This is not about being **“right at all costs.”**  It is about reasoning **transparently and responsibly**.

---

### 🏁 Expected Output

By the end of the hackathon, your team should be able to:

- Demo your AI jury 
- Show how agents reason and (possibly) disagree  
- Present the final verdict and explanation  

### Demos can be:
- CLI output  
- Notebook  
- Minimal UI  

> *Simple is great - clarity matters more than polish.*

---

## 🏆 Judging criteria 

Projects will be judged on:

- Quality of agent design (clear roles, meaningful interaction)  
- Clarity and honesty of explanations  
- Handling of uncertainty  
- Demo clarity and insight  

We care more about **good reasoning** than perfect answers.

### A golden solution is:
- Clearly better than a single-agent baseline  
- Understandable in a 3-minute demo  
- Teaches you something about multi-agent value  
- Handles uncertainty responsibly  

---

## 🧠 Important Question

During your demo, be prepared to answer:

> **What did using multiple agents add compared to a single AI call?**

There is no “correct” answer — **thoughtful reflections are highly valued**.

---

## 🚀 Possible Extension Direction

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

## 🚀 Getting Started

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
