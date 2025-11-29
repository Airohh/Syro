"""Create a specialized Syro instance for portfolio (MLOps or Data Science)."""

import argparse
import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domains import DOMAINS

SPECIALIZATIONS = {
    "mlops": {
        "name": "Syro MLOps",
        "description": "AI assistant specialized in MLOps, MLflow, Kubeflow, and production ML",
        "system_prompt": """You are an expert MLOps assistant specializing in:
- MLflow (experiment tracking, model registry, deployment)
- Kubeflow (ML pipelines, orchestration)
- Weights & Biases (experiment tracking)
- Model deployment and serving
- ML pipeline best practices
- Model versioning and monitoring

Provide accurate, technical answers based on the provided context. Always cite sources when available.""",
        "domain_key": "mlops",
    },
    "datascience": {
        "name": "Syro Data Science",
        "description": "AI assistant specialized in data science, Python, pandas, scikit-learn, and statistics",
        "system_prompt": """You are an expert data science assistant specializing in:
- Python data science ecosystem (pandas, numpy, scikit-learn)
- Statistical analysis and hypothesis testing
- Machine learning algorithms and model selection
- Data preprocessing and feature engineering
- Data visualization (matplotlib, seaborn, plotly)
- Best practices for data analysis

Provide accurate, technical answers based on the provided context. Always cite sources when available.""",
        "domain_key": "datascience",
    },
}

def create_specialized_domain(specialization: str) -> None:
    """Add specialized domain to domains.py if it doesn't exist."""
    domains_file = Path(__file__).parent.parent / "app" / "domains.py"
    
    if not domains_file.exists():
        print(f"❌ Error: {domains_file} not found")
        return
    
    content = domains_file.read_text(encoding="utf-8")
    
    # Check if domain already exists
    domain_key = SPECIALIZATIONS[specialization]["domain_key"]
    if f'"{domain_key}"' in content or f"'{domain_key}'" in content:
        print(f"✅ Domain '{domain_key}' already exists in domains.py")
        return
    
    # Find the DOMAINS dict and add new domain
    if "DOMAINS = {" in content:
        # Find the closing brace of DOMAINS dict
        lines = content.split("\n")
        insert_index = None
        
        for i, line in enumerate(lines):
            if "DOMAINS = {" in line:
                # Find the last entry before closing brace
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() == "}":
                        insert_index = j
                        break
                break
        
        if insert_index:
            spec = SPECIALIZATIONS[specialization]
            new_domain = f'''    "{domain_key}": DomainConfig(
        name="{spec["name"]}",
        description="{spec["description"]}",
        system_prompt="""{spec["system_prompt"]}""",
    ),'''
            lines.insert(insert_index, new_domain)
            domains_file.write_text("\n".join(lines), encoding="utf-8")
            print(f"✅ Added domain '{domain_key}' to domains.py")
        else:
            print(f"❌ Error: Could not find insertion point in domains.py")
    else:
        print(f"❌ Error: DOMAINS dict not found in domains.py")

def create_env_file(specialization: str, output_dir: Path) -> None:
    """Create optimized .env file for specialized instance."""
    spec = SPECIALIZATIONS[specialization]
    domain_key = spec["domain_key"]
    
    env_content = f"""# Syro {spec['name']} Configuration
# Specialized instance for portfolio

# Domain
DOMAIN={domain_key}

# Performance Mode (FAST for demo, QUALITY for production)
PERFORMANCE_MODE=fast

# LLM Settings
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
EMBEDDINGS_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768
CHAT_MODEL=llama3.2:1b  # Fast model for demo
CHAT_TEMPERATURE=0.2

# GPU Settings
OLLAMA_USE_GPU=True

# Performance Settings (FAST mode)
RETRIEVAL_TOP_K=5
RERANK_TOP_K=3
ENABLE_RERANKING=False
HYBRID_SEARCH_ALPHA=0.8

# Cache Settings
EMBEDDING_CACHE_ENABLED=True
EMBEDDING_CACHE_SIZE=1000

# MLOps Tracking
MLOPS_ENABLED=True
MLOPS_EXPERIMENT_NAME=syro_{domain_key}

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=syro_{domain_key}_chunks

# Database
DB_PATH=db/syro_{domain_key}.db
"""
    
    env_file = output_dir / ".env"
    env_file.write_text(env_content, encoding="utf-8")
    print(f"✅ Created .env file at {env_file}")

def create_setup_guide(specialization: str, output_dir: Path) -> None:
    """Create setup guide for specialized instance."""
    spec = SPECIALIZATIONS[specialization]
    domain_key = spec["domain_key"]
    
    guide_content = f"""# {spec['name']} - Setup Guide

## Overview

This is a specialized Syro instance for **{spec['name']}**.

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start services**:
   ```bash
   docker-compose up -d qdrant
   ```

3. **Initialize database**:
   ```bash
   python scripts/init_db.py
   ```

4. **Start API**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Ingest documents**:
   ```bash
   python scripts/upload_document.py \\
       --file path/to/document.pdf \\
       --org-id 1 \\
       --metadata '{{"source_type": "{domain_key}", "category": "documentation"}}'
   ```

## Document Organization

Recommended structure for documents:

```
docs/
├── {domain_key}/
│   ├── documentation/     # Official docs
│   ├── tutorials/         # Tutorials and guides
│   ├── best-practices/    # Best practices
│   └── examples/          # Code examples
```

## Benchmarking

Run benchmark to measure performance:

```bash
python scripts/benchmark_rag.py \\
    --queries \\
        "Your domain-specific query 1" \\
        "Your domain-specific query 2" \\
    --modes fast quality \\
    --org-id 1 \\
    --output benchmark_{domain_key}.json
```

## Performance Tuning

### FAST Mode (Demo)
- Latency: 1-3s
- Model: llama3.2:1b or llama3.2:3b
- Reranking: Disabled
- Top-K: 5 → 3

### QUALITY Mode (Production)
- Latency: 3-10s
- Model: llama3.2 or mistral
- Reranking: Enabled
- Top-K: 15 → 5

## Next Steps

1. Gather domain-specific documents
2. Ingest documents using batch script
3. Test with domain-specific queries
4. Benchmark and optimize
5. Create demo video/screenshots for portfolio
"""
    
    guide_file = output_dir / "SETUP_SPECIALIZED.md"
    guide_file.write_text(guide_content, encoding="utf-8")
    print(f"✅ Created setup guide at {guide_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Create a specialized Syro instance for portfolio"
    )
    parser.add_argument(
        "specialization",
        choices=["mlops", "datascience"],
        help="Specialization type (mlops or datascience)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: current Syro directory)",
    )
    parser.add_argument(
        "--skip-domain",
        action="store_true",
        help="Skip adding domain to domains.py",
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Creating specialized Syro instance: {args.specialization}")
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(__file__).parent.parent
    
    # Add domain to domains.py
    if not args.skip_domain:
        create_specialized_domain(args.specialization)
    
    # Create .env file
    create_env_file(args.specialization, output_dir)
    
    # Create setup guide
    create_setup_guide(args.specialization, output_dir)
    
    print(f"\n✅ Specialized Syro instance created!")
    print(f"\nNext steps:")
    print(f"1. Review and customize .env file")
    print(f"2. Start services: docker-compose up -d")
    print(f"3. Ingest domain-specific documents")
    print(f"4. Run benchmark: python scripts/benchmark_rag.py")

if __name__ == "__main__":
    main()

