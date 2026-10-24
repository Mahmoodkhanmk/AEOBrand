# 🔭 AEOBrand — Enterprise AI Visibility Observatory

> **Answer Engine Optimization (AEO) meets measurable telemetry.**  
> A comprehensive framework to measure, analyze, and monitor how your brand is represented across Large Language Models (ChatGPT, Claude, Gemini, Perplexity).

---

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Current Status](#current-status)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Environment Variables](#environment-variables)

---

## Overview

With the paradigm shift from traditional **SEO** to **Answer Engine Optimization (AEO)**, organizations face a critical visibility blindspot — they have no way to measure how AI engines represent them. AEOBrand solves this by creating a continuous, automated testing pipeline that transforms opaque AI outputs into mathematically verifiable telemetry.

**Core Metrics Produced:**
| Metric | Description |
|--------|-------------|
| **BVI** — Brand Visibility Index | Overall share of voice across all tested LLMs |
| **CMCS** — Cross-Model Consistency Score | How uniformly different LLMs recommend your brand |
| **CAS** — Citation Authority Score | Weighted score of authoritative third-party citations |

---

## Architecture

```
Baseline Config → Synthetic Prompt Generator → Multi-LLM Dispatcher
                                                      ↓
                            OpenAI · Anthropic · Gemini · Ollama
                                                      ↓
                         Response Capture → Entity/Sentiment Extraction
                                                      ↓
                           BVI · CMCS · CAS Scoring Engine
                                                      ↓
                              Time-Series DB → Executive Dashboard
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full Mermaid diagram and phased implementation plan.

---

## Current Status

### ✅ Phase 1 — Configuration & Prompt Synthesis (In Progress)
- [x] Pydantic schema models (`src/models.py`)
- [x] LLM-powered synthetic prompt generator (`src/prompt_generator.py`)
- [ ] Web frontend dashboard (HTML/React)

### 🔜 Coming Next
- **Phase 2**: Multi-LLM Dispatch Engine (OpenAI, Anthropic, Gemini, Ollama)
- **Phase 3**: NLP Refinement & Mathematical Scoring (BVI, CMCS, CAS)
- **Phase 4**: Time-Series DB + Executive Analytics Dashboard

---

## Getting Started

### Prerequisites
- Python 3.10+
- An OpenAI API key (for live prompt generation)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/AEOBrand.git
cd AEOBrand

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install openai pydantic python-dotenv

# 4. Set up your environment variables
copy .env.example .env
# Then edit .env and add your OPENAI_API_KEY
```

### Running the Prompt Generator

```bash
cd src
python prompt_generator.py
```

- **With an API key**: Generates real semantic prompt permutations via GPT-4o.
- **Without an API key**: Falls back to the built-in mock generator for safe local testing.

---

## Project Structure

```
AEOBrand/
├── src/
│   ├── models.py              # Pydantic schema definitions (BaselineConfig, SyntheticPromptCollection)
│   └── prompt_generator.py   # LLM-powered synthetic prompt engine
├── ARCHITECTURE.md            # Full system architecture & phased implementation plan
├── .env.example               # Template for environment variables (safe to commit)
├── .env                       # Your local secrets — DO NOT COMMIT
├── .gitignore
└── README.md
```

---

## Contributing

Contributions are welcome! Please follow this workflow:

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Commit your changes**: `git commit -m "feat: add your feature"`
4. **Push to your fork**: `git push origin feature/your-feature-name`
5. **Open a Pull Request** against the `main` branch

Please keep PRs focused and include a clear description of what changed and why.

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key for GPT-4o access | Yes (for live mode) |

Copy `.env.example` → `.env` and fill in your values. **Never commit your `.env` file.**
