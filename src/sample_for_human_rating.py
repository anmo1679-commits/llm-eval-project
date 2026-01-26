#!/usr/bin/env python3
"""
Human rating sampling script for LLM evaluation harness.

Generates a stratified sample of runs across cohorts (model, system_prompt_version, category)
and creates a CSV template for manual human rating.

Target sample size: 80-120 runs
"""

import csv
import random
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


def load_csv(filepath: Path) -> List[Dict[str, str]]:
    """Load CSV file into list of dictionaries."""
    with open(filepath, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def stratified_sample(runs: List[Dict], prompts_lookup: Dict, 
                     target_size: int = 100, samples_per_bucket: int = 8) -> List[Dict]:
    """
    Create stratified sample across cohorts.
    
    Cohort = (model_name, system_prompt_version, category)
    
    Args:
        runs: List of run dictionaries
        prompts_lookup: Dictionary mapping prompt_id to prompt data
        target_size: Target total number of samples (80-120)
        samples_per_bucket: Number of samples to take per cohort
    
    Returns:
        List of sampled run dictionaries
    """
    # Group runs by cohort
    cohorts = defaultdict(list)
    
    for run in runs:
        prompt = prompts_lookup.get(run['prompt_id'])
        if not prompt:
            continue
        
        cohort_key = (
            run.get('model_name', 'unknown'),
            run.get('system_prompt_version', 'unknown'),
            prompt.get('category', 'unknown')
        )
        cohorts[cohort_key].append(run)
    
    # Sample from each cohort
    sampled = []
    for cohort_key, cohort_runs in sorted(cohorts.items()):
        # Randomly sample up to samples_per_bucket from this cohort
        k = min(samples_per_bucket, len(cohort_runs))
        cohort_sample = random.sample(cohort_runs, k)
        sampled.extend(cohort_sample)
    
    # If we're under target, take more samples
    if len(sampled) < target_size:
        remaining = target_size - len(sampled)
        already_sampled_ids = {r['run_id'] for r in sampled}
        available = [r for r in runs if r['run_id'] not in already_sampled_ids]
        
        if available:
            additional = random.sample(available, min(remaining, len(available)))
            sampled.extend(additional)
    
    # If we're over target, trim randomly
    if len(sampled) > target_size:
        sampled = random.sample(sampled, target_size)
    
    # Sort by run_id for consistency
    sampled.sort(key=lambda x: int(x['run_id']))
    
    return sampled


def create_rating_template(sampled_runs: List[Dict], output_path: Path):
    """
    Create human rating CSV template with empty rating fields.
    
    Schema:
    - run_id
    - helpfulness_1_5 (empty)
    - correctness_1_5 (empty)
    - clarity_1_5 (empty)
    - compliance_1_5 (empty)
    - hallucination_flag (empty)
    - notes (empty)
    """
    fieldnames = [
        'run_id',
        'helpfulness_1_5',
        'correctness_1_5',
        'clarity_1_5',
        'compliance_1_5',
        'hallucination_flag',
        'notes'
    ]
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for run in sampled_runs:
            writer.writerow({
                'run_id': run['run_id'],
                'helpfulness_1_5': '',
                'correctness_1_5': '',
                'clarity_1_5': '',
                'compliance_1_5': '',
                'hallucination_flag': '',
                'notes': ''
            })


def print_cohort_breakdown(sampled_runs: List[Dict], prompts_lookup: Dict):
    """Print breakdown of samples by cohort."""
    cohorts = defaultdict(int)
    
    for run in sampled_runs:
        prompt = prompts_lookup.get(run['prompt_id'])
        if not prompt:
            continue
        
        cohort_key = (
            run.get('model_name', 'unknown'),
            run.get('system_prompt_version', 'unknown'),
            prompt.get('category', 'unknown')
        )
        cohorts[cohort_key] += 1
    
    print("\n" + "="*60)
    print("COHORT BREAKDOWN")
    print("="*60)
    print(f"{'Model':<20} {'SysPrompt':<12} {'Category':<15} Count")
    print("-"*60)
    
    for (model, sys_prompt, category), count in sorted(cohorts.items()):
        print(f"{model:<20} {sys_prompt:<12} {category:<15} {count:>5}")
    
    print("="*60 + "\n")


def main():
    """Main execution flow."""
    # Set random seed for reproducibility
    random.seed(42)
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    prompts_path = base_dir / 'data' / 'prompts.csv'
    runs_path = base_dir / 'data' / 'runs.csv'
    ratings_path = base_dir / 'data' / 'human_ratings.csv'
    
    # Configuration
    target_size = 100  # Target between 80-120
    samples_per_bucket = 8
    
    print("Loading data...")
    print(f"  Prompts: {prompts_path}")
    print(f"  Runs: {runs_path}")
    
    # Load data
    prompts = load_csv(prompts_path)
    runs = load_csv(runs_path)
    
    prompts_lookup = {p['prompt_id']: p for p in prompts}
    
    print(f"Loaded {len(prompts)} prompts, {len(runs)} runs")
    
    # Create stratified sample
    print(f"\nCreating stratified sample (target: {target_size})...")
    print(f"Strategy: {samples_per_bucket} samples per cohort (model × sys_prompt × category)")
    
    sampled = stratified_sample(runs, prompts_lookup, target_size, samples_per_bucket)
    
    print(f"Sampled {len(sampled)} runs for human rating")
    
    # Print cohort breakdown
    print_cohort_breakdown(sampled, prompts_lookup)
    
    # Write template
    print(f"Writing rating template to: {ratings_path}")
    create_rating_template(sampled, ratings_path)
    
    print(f"✓ Human rating template created with {len(sampled)} rows")
    print(f"\nNext steps:")
    print(f"  1. Open {ratings_path}")
    print(f"  2. Fill in rating columns (1-5 scale for helpfulness/correctness/clarity/compliance)")
    print(f"  3. Mark hallucination_flag as 0 or 1")
    print(f"  4. Add optional notes for interesting cases")


if __name__ == '__main__':
    main()
