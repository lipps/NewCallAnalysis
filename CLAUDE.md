# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Chinese AI-powered sales call analysis system (销售通话质检系统) that analyzes sales call transcripts using advanced AI technologies including LangGraph workflows, vector retrieval, and large language models. The system identifies key sales techniques, customer responses, and provides detailed quality assessments.

## Development Commands

### Environment Setup
```bash
# Copy and configure environment file
cp .env.example .env
# Edit .env file with your API keys (OPENAI_API_KEY required)

# Install dependencies
pip install -r requirements.txt
```

### Running the System
```bash
# Start API server (runs on http://localhost:8000)
python main.py server --host 0.0.0.0 --port 8000

# Start interactive dashboard (runs on http://localhost:8501)
python main.py dashboard

# Single call analysis via CLI
python main.py analyze --text "销售：您好，我是益盟操盘手专员..." --output result.json

# Batch analysis
python main.py batch --file batch_input.json --output batch_results.json

# Generate sample data for testing
python main.py sample --output sample_data.json
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_workflow.py -v

# Run performance tests
pytest tests/test_workflow.py::TestPerformance -v
```

## Core Architecture

The system uses a **layered, multi-engine architecture** with the following key components:

### 1. Multi-Engine Analysis Pipeline
- **Rule Engine**: Fast keyword and regex pattern matching for initial detection
- **Vector Engine**: Semantic similarity search using sentence-transformers embeddings
- **LLM Engine**: Intelligent validation and evidence extraction using OpenAI-compatible APIs
- **Fusion Strategy**: Combines all three engines' results with weighted confidence scoring

### 2. Workflow Orchestration
- **Simplified Workflow** (`src/workflows/simplified_workflow.py`): Serial execution coordinator to avoid LangGraph concurrency issues
- **8 Processing Stages**: Text preprocessing → Icebreak → Deduction → Process → Customer → Actions → Customer Probing → Pain Points
- **Parallel Detection**: Within each processor, individual detection points are analyzed in parallel using `asyncio.gather`

### 3. Processor Modules (`src/processors/`)
Each processor handles specific analysis aspects:
- `icebreak_processor.py`: Professional identity, value proposition, time notice, company background, free teaching
- `deduction_processor.py`: BS points, cycle resonance, fund control, BuBuGao, value quantification, customer stock analysis
- `process_processor.py`: Call duration, interaction frequency, deal/appointment outcomes
- `customer_processor.py`: Attitude scoring, value recognition, question extraction
- `action_processor.py`: Standard sales action execution tracking
- `customer_probing_processor.py`: Customer situation investigation analysis
- `pain_point_processor.py`: Pain point identification and quantification

### 4. Configuration System (`src/config/settings.py`)
- **Pydantic-based settings** with environment variable support
- **Detection rules** with keywords and regex patterns for each analysis point
- **Rejection/handling patterns** for customer objection analysis
- **Model configurations** supporting multiple LLM providers
- **Performance tuning** parameters (batch sizes, timeouts, cache sizes)

### 5. Data Models (`src/models/schemas.py`)
- **EvidenceHit**: Standard structure for detection results with confidence, evidence, and source tracking
- **Structured outputs** for each analysis module (IcebreakModel, DeductionModel, etc.)
- **Signal fusion** metadata for debugging and optimization

## Key Implementation Details

### Engine Coordination Pattern
```python
# Each processor follows this three-stage pattern:
rule_result = await rule_engine.detect(category, point, text)
if confidence_low:
    vector_result = await vector_engine.search(query, text)
if still_uncertain:
    llm_result = await llm_engine.validate(point, evidence)
# Combine results with weighted fusion
```

### Parallel Processing Strategy
- **Workflow level**: Serial execution to maintain data consistency
- **Processor level**: Parallel detection of multiple points using `asyncio.gather`
- **Batch processing**: Controlled concurrency with semaphores (max_concurrency=3-5)

### Error Handling & Resilience
- **Graceful degradation**: System continues with lower confidence if engines fail
- **Timeout management**: Per-request and global timeouts prevent hanging
- **Exception isolation**: Individual point failures don't crash entire analysis
- **Result validation**: Pydantic models ensure data consistency

## Configuration Notes

### Environment Variables
Key settings in `.env`:
- `OPENAI_API_KEY`: Required for LLM engine
- `OPENAI_BASE_URL`: Supports custom endpoints (default: Alibaba DashScope compatible)
- `CHROMA_PERSIST_DIRECTORY`: Vector database storage location
- `LOG_LEVEL`: Controls logging verbosity

### Model Selection
The system is configured for Chinese language analysis with:
- **Embedding model**: `paraphrase-multilingual-MiniLM-L12-v2` for semantic search
- **LLM model**: `deepseek-v3.1` optimized for Chinese understanding
- **Temperature**: 0.1 for consistent, deterministic outputs

### Performance Tuning
- **Batch size**: 32 for optimal throughput
- **Cache size**: 1000 entries for rule/vector result caching
- **Max workers**: 4 for parallel processing
- **Timeout**: 300s for complex analyses

## Business Logic

The system analyzes Chinese sales calls for financial services (specifically stock trading advisory calls) with domain-specific detection rules for:
- **Sales techniques**: Professional introduction, value statements, objection handling
- **Product explanations**: Technical indicators (BS points, fund control, etc.)
- **Customer responses**: Attitudes, questions, rejection patterns
- **Call outcomes**: Success metrics, next steps, follow-up actions

The analysis produces structured JSON reports with confidence scores, evidence snippets, and actionable insights for sales training and quality assessment.