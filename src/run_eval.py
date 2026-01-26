#!/usr/bin/env python3
"""
Evaluation runner for LLM Evaluation Harness.

Reads prompts from prompts.csv, sends them through Ollama models,
and writes detailed run logs to runs.csv with metadata.
"""

import csv
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


# System prompt templates
SYSTEM_PROMPTS = {
    "v1": "You are a helpful AI assistant. Provide accurate, clear, and concise responses.",
    "v2": "You are a helpful AI assistant. Provide accurate, clear, and concise responses. When uncertain, acknowledge limitations. Cite sources when making factual claims."
}


def load_prompts(filepath: Path) -> List[Dict[str, str]]:
    """Load prompts from CSV file."""
    with open(filepath, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def query_ollama(
    model_name: str,
    prompt: str,
    system_prompt: str,
    temperature: float = 0.7
) -> Optional[Dict]:
    """
    Query Ollama API and return response with timing information.
    
    Returns dict with keys: output_text, latency_ms, or None if error.
    """
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=120)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            latency_ms = int((end_time - start_time) * 1000)
            
            return {
                "output_text": data.get("response", ""),
                "latency_ms": latency_ms
            }
        else:
            print(f"Error: API returned status {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out for prompt")
        return None
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return None


def run_evaluation(
    prompts: List[Dict],
    models: List[str],
    system_prompt_versions: List[str],
    temperature: float = 0.7,
    prompt_limit: Optional[int] = None
) -> List[Dict]:
    """
    Run evaluation across all prompts, models, and system prompt versions.
    
    Args:
        prompt_limit: If specified, only test first N prompts (for quick testing)
    
    Returns list of run dictionaries with schema matching runs.csv.
    """
    runs = []
    run_id = 1
    
    # Apply prompt limit if specified
    test_prompts = prompts[:prompt_limit] if prompt_limit else prompts
    
    total_combinations = len(test_prompts) * len(models) * len(system_prompt_versions)
    current = 0
    
    for model_name in models:
        for sys_prompt_version in system_prompt_versions:
            system_prompt = SYSTEM_PROMPTS[sys_prompt_version]
            
            print(f"\n{'='*60}")
            print(f"Running: {model_name} with system prompt {sys_prompt_version}")
            print(f"{'='*60}")
            
            for prompt_data in test_prompts:
                current += 1
                prompt_id = prompt_data['prompt_id']
                prompt_text = prompt_data['prompt_text']
                
                print(f"[{current}/{total_combinations}] Prompt {prompt_id}...", end=" ", flush=True)
                
                # Query model
                result = query_ollama(
                    model_name=model_name,
                    prompt=prompt_text,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
                
                if result:
                    output_text = result['output_text']
                    latency_ms = result['latency_ms']
                    
                    # Create run record
                    run = {
                        'run_id': run_id,
                        'prompt_id': prompt_id,
                        'model_name': model_name,
                        'system_prompt_version': sys_prompt_version,
                        'temperature': temperature,
                        'timestamp': datetime.now().isoformat(),
                        'latency_ms': latency_ms,
                        'output_len_chars': len(output_text),
                        'output_text': output_text
                    }
                    
                    runs.append(run)
                    print(f"✓ ({latency_ms}ms, {len(output_text)} chars)")
                else:
                    print("✗ FAILED")
                
                run_id += 1
                
                # Small delay to avoid overwhelming Ollama
                time.sleep(0.2)
    
    return runs


def write_runs_csv(runs: List[Dict], filepath: Path):
    """Write runs to CSV file."""
    if not runs:
        print("Warning: No runs to write")
        return
    
    fieldnames = [
        'run_id',
        'prompt_id',
        'model_name',
        'system_prompt_version',
        'temperature',
        'timestamp',
        'latency_ms',
        'output_len_chars',
        'output_text'
    ]
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(runs)


def print_summary(runs: List[Dict]):
    """Print summary statistics."""
    if not runs:
        print("No runs completed")
        return
    
    total = len(runs)
    avg_latency = sum(r['latency_ms'] for r in runs) / total
    avg_length = sum(r['output_len_chars'] for r in runs) / total
    
    # Count by model
    models = {}
    for run in runs:
        model = run['model_name']
        models[model] = models.get(model, 0) + 1
    
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total runs completed: {total}")
    print(f"Average latency: {avg_latency:.0f}ms")
    print(f"Average output length: {avg_length:.0f} chars")
    print(f"\nRuns by model:")
    for model, count in models.items():
        print(f"  {model}: {count}")
    print("="*60 + "\n")


def main():
    """Main execution flow."""
    # Configuration
    base_dir = Path(__file__).parent.parent
    prompts_path = base_dir / 'data' / 'prompts.csv'
    runs_path = base_dir / 'data' / 'runs.csv'
    
    # Models and configs to test
    models = ['llama3.2:latest', 'qwen2.5:latest']  # Compare both models
    system_prompt_versions = ['v2']  # Using v2 as requested
    temperature = 0.7
    prompt_limit = 10  # Test first 10 prompts only (remove or set to None for all 150)
    
    print("LLM Evaluation Harness - Run Evaluation")
    print("="*60)
    print(f"Prompts: {prompts_path}")
    print(f"Models: {models}")
    print(f"System prompt versions: {system_prompt_versions}")
    print(f"Temperature: {temperature}")
    if prompt_limit:
        print(f"Prompt limit: First {prompt_limit} prompts only (TESTING MODE)")
    print("="*60)
    
    # Load prompts
    print(f"\nLoading prompts...")
    prompts = load_prompts(prompts_path)
    print(f"Loaded {len(prompts)} prompts")
    if prompt_limit:
        print(f"Testing with first {prompt_limit} prompts")
    
    # Run evaluation
    print(f"\nStarting evaluation...")
    runs = run_evaluation(prompts, models, system_prompt_versions, temperature, prompt_limit)
    
    # Write results
    print(f"\nWriting results to: {runs_path}")
    write_runs_csv(runs, runs_path)
    
    # Print summary
    print_summary(runs)
    
    print(f"✓ Evaluation complete. Results saved to {runs_path}")
    print(f"\nNext steps:")
    print(f"  1. Run: python src/auto_score.py")
    print(f"  2. Run: python src/sample_for_human_rating.py")


if __name__ == '__main__':
    main()
