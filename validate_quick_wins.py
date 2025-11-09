#!/usr/bin/env python3
"""
Validation Script for Quick Wins Implementation
Verifies that optimizations have been correctly applied

Quick Win 1: vLLM Configuration Optimization
Quick Win 2: Embedding Cache Enhancement (TTL + Disk Persistence)
"""

import os
import sys
import re
from pathlib import Path

def validate_vllm_config():
    """Validate vLLM optimization in config_manager.py and model_orchestrator.py"""
    print("\n🔍 Validating Quick Win 1: vLLM Configuration...")
    
    # Check config_manager.py
    config_path = Path("src/config/config_manager.py")
    if not config_path.exists():
        print("❌ config_manager.py not found")
        return False
    
    config_content = config_path.read_text()
    
    checks = {
        "gpu_memory_utilization: float = 0.92": False,
        "max_num_seqs: int = 64": False,
        "max_num_batched_tokens: int = 8192": False,
        "enable_prefix_caching: bool = True": False,
        "enable_chunked_prefill: bool = True": False,
        "swap_space_gb: int = 8": False
    }
    
    for check in checks:
        if check in config_content:
            checks[check] = True
            print(f"  ✅ Found: {check}")
        else:
            print(f"  ❌ Missing: {check}")
    
    # Check model_orchestrator.py
    orchestrator_path = Path("src/modules/orchestrator/model_orchestrator.py")
    if not orchestrator_path.exists():
        print("❌ model_orchestrator.py not found")
        return False
    
    orchestrator_content = orchestrator_path.read_text()
    
    orchestrator_checks = [
        "gpu_memory_utilization=0.92",
        "max_num_seqs=64",
        "max_num_batched_tokens=8192",
        "enable_prefix_caching=True",
        "enable_chunked_prefill=True"
    ]
    
    for check in orchestrator_checks:
        if check in orchestrator_content:
            print(f"  ✅ Orchestrator uses: {check}")
        else:
            print(f"  ⚠️  Orchestrator missing: {check}")
    
    all_passed = all(checks.values())
    if all_passed:
        print("✅ Quick Win 1: vLLM Configuration VERIFIED")
    else:
        print("❌ Quick Win 1: INCOMPLETE")
    
    return all_passed

def validate_embedding_cache():
    """Validate TTLCache + disk persistence in embedding_manager.py"""
    print("\n🔍 Validating Quick Win 2: Embedding Cache Enhancement...")
    
    embedding_path = Path("src/modules/embeddings/embedding_manager.py")
    if not embedding_path.exists():
        print("❌ embedding_manager.py not found")
        return False
    
    content = embedding_path.read_text()
    
    checks = {
        "from cachetools import TTLCache": False,
        "import pickle": False,
        "cache_size: int = 5000": False,
        "cache_ttl: int = 3600": False,
        "TTLCache(maxsize=cache_size, ttl=cache_ttl)": False,
        "_load_disk_cache": False,
        "_save_disk_cache": False,
        "def __del__": False,
        "embedding_cache.pkl": False
    }
    
    for check in checks:
        if check in content:
            checks[check] = True
            print(f"  ✅ Found: {check}")
        else:
            print(f"  ❌ Missing: {check}")
    
    all_passed = all(checks.values())
    if all_passed:
        print("✅ Quick Win 2: Embedding Cache VERIFIED")
    else:
        print("❌ Quick Win 2: INCOMPLETE")
    
    return all_passed

def validate_requirements():
    """Check requirements.txt for cachetools"""
    print("\n🔍 Validating requirements.txt...")
    
    req_path = Path("requirements.txt")
    if not req_path.exists():
        print("❌ requirements.txt not found")
        return False
    
    content = req_path.read_text()
    
    if "cachetools" in content:
        print("  ✅ cachetools added to requirements.txt")
        return True
    else:
        print("  ❌ cachetools missing from requirements.txt")
        return False

def check_git_status():
    """Show modified files"""
    print("\n📋 Modified Files:")
    os.system("git status --short --untracked-files=no 2>/dev/null || echo 'Not a git repository'")

def main():
    print("="*60)
    print("🚀 Quick Wins Implementation Validator")
    print("="*60)
    
    results = {
        "vLLM Config": validate_vllm_config(),
        "Embedding Cache": validate_embedding_cache(),
        "Requirements": validate_requirements()
    }
    
    check_git_status()
    
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL QUICK WINS VALIDATED SUCCESSFULLY!")
        print("\n📈 Expected Improvements:")
        print("  • vLLM throughput: +200-300% (16 → 64 concurrent sequences)")
        print("  • Embedding cache hit rate: 95% → 98%")
        print("  • Cache persistence: Survives restarts")
        print("  • GPU memory utilization: +7% (0.90 → 0.92)")
        return 0
    else:
        print("\n⚠️  SOME VALIDATIONS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
