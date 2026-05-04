"""Inference script for BIS standard retrieval."""

import json
import time
import argparse
import sys
import os
from typing import List, Dict, Any
from pathlib import Path

from src.pipeline import init_pipeline, get_recommendations


def load_docs(verbose: bool = False) -> List[Dict]:
    """
    Load document chunks with automatic fallback.

    Priority:
    1. chunks_enriched.json (from metadata_builder.py)
    2. chunksss.json (from chunking.py)

    Args:
        verbose: Print loading details

    Returns:
        List[Dict]: Document chunks
    """
    enriched_path = "data/processed/chunks_eenriched.json"
    original_path = "data/processed/chunksss.json"

    if os.path.exists(enriched_path):
        path = enriched_path
        chunk_type = "enriched"
    elif os.path.exists(original_path):
        path = original_path
        chunk_type = "basic"
    else:
        raise FileNotFoundError(
            f"❌ No chunks found. Please run chunking.py first.\n"
            f"   Expected: {original_path} or {enriched_path}"
        )

    if verbose:
        print(f"📂 Loading {chunk_type} chunks from: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            docs = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ Invalid JSON in chunks file: {e}")

    if verbose:
        print(f"   ✓ Loaded {len(docs)} chunks")

    return docs


def process_single_query(item: Dict, verbose: bool = False) -> Dict[str, Any]:
    """
    Process a single query with error handling.

    Args:
        item: Query dict with 'id' and 'query' fields
        verbose: Print processing details

    Returns:
        Dict: Result in specified format with id, query, expected_standards, 
              retrieved_standards, latency_seconds
    """
    query_id = item.get("id", "unknown")
    query_text = item.get("query", "")

    if verbose:
        print(f"   [{query_id}] {query_text[:60]}...")

    start_time = time.time()

    try:
        predictions = get_recommendations(query_text)
        latency = time.time() - start_time

        if not isinstance(predictions, list):
            predictions = []

        predictions = [str(p) for p in predictions if str(p).strip()]

        # Build result in exact order requested
        result = {
            "id": query_id,
            "query": query_text,
            "expected_standards": item.get("expected_standards", []),
            "retrieved_standards": predictions,
            "latency_seconds": round(latency, 4),
        }

        if verbose:
            print(f"      → {len(predictions)} standards | {latency:.3f}s")

        return result

    except Exception as e:
        latency = time.time() - start_time

        if verbose:
            print(f"      ⚠️  Error: {e}")

        # Return empty results but maintain format
        result = {
            "id": query_id,
            "query": query_text,
            "expected_standards": item.get("expected_standards", []),
            "retrieved_standards": [],
            "latency_seconds": round(latency, 4),
        }

        return result


def validate_results(results: List[Dict], verbose: bool = False) -> bool:
    """
    Validate output format before saving.

    Checks:
    - All results have required fields
    - All retrieved_standards are non-empty strings
    - No duplicate query IDs

    Args:
        results: List of result dicts
        verbose: Print validation details

    Returns:
        bool: True if valid, False otherwise
    """
    if verbose:
        print(f"\n🔍 Validating {len(results)} results...")

    issues = []
    query_ids = set()

    required_fields = ["id", "query", "expected_standards", "retrieved_standards", "latency_seconds"]

    for i, result in enumerate(results):
        for field in required_fields:
            if field not in result:
                issues.append(f"Result {i}: Missing '{field}' field")

        query_id = result.get("id")
        if query_id in query_ids:
            issues.append(f"Duplicate query ID: {query_id}")
        query_ids.add(query_id)

        standards = result.get("retrieved_standards", [])
        if not isinstance(standards, list):
            issues.append(f"Query {query_id}: retrieved_standards is not a list")
        else:
            for j, std in enumerate(standards):
                if not isinstance(std, str) or not std.strip():
                    issues.append(f"Query {query_id}: Invalid standard at position {j}")

        expected = result.get("expected_standards", [])
        if not isinstance(expected, list):
            issues.append(f"Query {query_id}: expected_standards is not a list")

    if issues:
        print(f"❌ Validation failed with {len(issues)} issues:", file=sys.stderr)
        for issue in issues[:10]:
            print(f"   - {issue}", file=sys.stderr)
        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more", file=sys.stderr)
        return False

    if verbose:
        print(f"   ✓ All results valid")

    return True


def print_statistics(results: List[Dict]):
    """
    Print summary statistics about the inference run.

    Reports:
    - Total queries processed
    - Output size distribution
    - Latency statistics (min/max/mean/median/p95)
    """
    print("\n" + "=" * 70)
    print("📊 INFERENCE STATISTICS")
    print("=" * 70)

    total = len(results)
    print(f"\n📝 Total queries processed: {total}")

    # Output size distribution
    sizes = [len(r.get("retrieved_standards", [])) for r in results]
    from collections import Counter
    size_dist = Counter(sizes)

    print(f"\n📏 Output Size Distribution:")
    for size in sorted(size_dist.keys()):
        count = size_dist[size]
        print(f"   {size} standards: {count} queries ({count/total*100:.1f}%)")

    # Latency statistics
    latencies = [r.get("latency_seconds", 0) for r in results]

    if latencies:
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)

        print(f"\n⏱️  Latency Statistics:")
        print(f"   Min:    {min(latencies):.3f}s")
        print(f"   Max:    {max(latencies):.3f}s")
        print(f"   Mean:   {sum(latencies)/n:.3f}s")
        print(f"   Median: {latencies_sorted[n//2]:.3f}s")
        print(f"   P95:    {latencies_sorted[int(n*0.95)]:.3f}s")
        print(f"   Total:  {sum(latencies):.1f}s")

    print("\n" + "=" * 70 + "\n")


def main(input_path: str, output_path: str, verbose: bool = False):
    """
    Main inference pipeline.

    Steps:
    1. Load document chunks
    2. Initialize pipeline (models, indices)
    3. Load test queries
    4. Process each query with progress tracking
    5. Validate outputs
    6. Save results
    7. Print statistics

    Args:
        input_path: Path to test queries JSON
        output_path: Path to save predictions JSON
        verbose: Enable detailed logging
    """

    print("\n" + "=" * 70)
    print("🚀 BIS STANDARD RETRIEVAL - INFERENCE")
    print("=" * 70 + "\n")

    try:
        docs = load_docs(verbose=verbose)
    except Exception as e:
        print(f"❌ Failed to load chunks: {e}", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"🔧 Initializing pipeline (loading models)...")

    try:
        init_pipeline(docs)
        if verbose:
            print(f"   ✓ Pipeline ready\n")
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"📥 Loading test queries from: {input_path}")

    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print(f"❌ Input must be a JSON array of queries", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"   ✓ Loaded {len(data)} queries\n")

    print(f"🔍 Processing {len(data)} queries...\n")

    results = []
    start_time = time.time()

    for i, item in enumerate(data, 1):
        if verbose:
            print(f"[{i}/{len(data)}]", end=" ")
        elif i % 10 == 0 or i == len(data):
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(data) - i) / rate if rate > 0 else 0
            print(
                f"Progress: {i}/{len(data)} ({i/len(data)*100:.1f}%) | "
                f"Rate: {rate:.1f} q/s | ETA: {eta:.0f}s"
            )

        result = process_single_query(item, verbose=verbose)
        results.append(result)

    total_time = time.time() - start_time

    print(
        f"\n✓ Completed in {total_time:.1f}s "
        f"(avg {total_time/len(data):.2f}s per query)\n"
    )

    is_valid = validate_results(results, verbose=verbose)

    if not is_valid:
        print(
            f"⚠️  Warning: Output validation failed. Saving anyway...\n",
            file=sys.stderr,
        )

    if verbose:
        print(f"💾 Saving results to: {output_path}")

    try:
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        if verbose:
            print(f"   ✓ Saved {len(results)} results\n")
        else:
            print(f"✅ Saved predictions to: {output_path}\n")

    except Exception as e:
        print(f"❌ Failed to save results: {e}", file=sys.stderr)
        sys.exit(1)

    print_statistics(results)

    print("✨ Inference complete!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BIS Standard Retrieval - Inference Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inference.py --input test.json --output predictions.json
  python inference.py --input test.json --output predictions.json --verbose
  python inference.py -i data/test.json -o results/predictions.json -v
        """,
    )

    parser.add_argument(
        "--input", "-i", required=True, help="Path to input test queries JSON file"
    )

    parser.add_argument(
        "--output", "-o", required=True, help="Path to save predictions JSON file"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (shows each query being processed)",
    )

    args = parser.parse_args()

    main(args.input, args.output, args.verbose)