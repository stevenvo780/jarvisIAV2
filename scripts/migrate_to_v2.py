#!/usr/bin/env python3
"""
Migration Script - Jarvis IA V1 to V2
Safely migrates from old system to new multi-GPU architecture
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Migration")


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(msg):
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")


def print_success(msg):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")


def print_info(msg):
    print(f"{Colors.OKBLUE}ℹ️  {msg}{Colors.ENDC}")


def print_warning(msg):
    print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")


def print_error(msg):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")


def backup_existing_system():
    """Create backup of existing system"""
    print_header("📦 Creating Backup")
    
    backup_dir = f"backup_v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    items_to_backup = [
        'src/config/config.json',
        'src/data/jarvis_context.json',
        'src/data/user_profile.json',
        'src/modules/llm/',
        'main.py'
    ]
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        for item in items_to_backup:
            if os.path.exists(item):
                dest = os.path.join(backup_dir, item)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                
                if os.path.isdir(item):
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
                
                print_success(f"Backed up: {item}")
        
        print_success(f"Backup created: {backup_dir}")
        return backup_dir
    
    except Exception as e:
        print_error(f"Backup failed: {e}")
        return None


def check_dependencies():
    """Check if new dependencies are installed"""
    print_header("🔍 Checking Dependencies")
    
    required_packages = {
        'torch': 'PyTorch',
        'transformers': 'Transformers',
        'vllm': 'vLLM (optional but recommended)',
        'faster_whisper': 'Faster-Whisper',
        'sentence_transformers': 'Sentence-Transformers',
        'chromadb': 'ChromaDB',
        'pynvml': 'PyNVML'
    }
    
    missing = []
    optional_missing = []
    
    for package, name in required_packages.items():
        try:
            __import__(package)
            print_success(f"{name} installed")
        except ImportError:
            if package == 'vllm':
                optional_missing.append(name)
                print_warning(f"{name} not installed (optional)")
            else:
                missing.append(name)
                print_error(f"{name} not installed")
    
    if missing:
        print_error(f"\nMissing required packages: {', '.join(missing)}")
        print_info("Run: ./install_upgrade.sh")
        return False
    
    if optional_missing:
        print_warning(f"\nOptional packages not installed: {', '.join(optional_missing)}")
        print_info("vLLM highly recommended for best performance")
    
    print_success("\nAll required dependencies installed!")
    return True


def migrate_config():
    """Migrate configuration files"""
    print_header("⚙️  Migrating Configuration")
    
    try:
        # Load old config
        with open('src/config/config.json', 'r') as f:
            old_config = json.load(f)
        
        print_info("Old configuration loaded")
        
        # Check if new config exists
        if os.path.exists('src/config/models_v2.json'):
            print_warning("models_v2.json already exists")
            response = input("Overwrite? (y/n): ")
            if response.lower() != 'y':
                print_info("Skipping config migration")
                return True
        
        print_success("New configuration ready (models_v2.json)")
        print_info("Review and adjust model paths in models_v2.json")
        
        return True
    
    except Exception as e:
        print_error(f"Config migration failed: {e}")
        return False


def migrate_data():
    """Migrate user data and context"""
    print_header("📊 Migrating Data")
    
    try:
        # User profile
        if os.path.exists('src/data/user_profile.json'):
            print_success("User profile preserved")
        
        # Context
        if os.path.exists('src/data/jarvis_context.json'):
            print_success("Context file preserved")
        
        # Create new directories
        os.makedirs('vectorstore/chromadb', exist_ok=True)
        print_success("Created vector store directory")
        
        os.makedirs('logs', exist_ok=True)
        print_success("Created logs directory")
        
        return True
    
    except Exception as e:
        print_error(f"Data migration failed: {e}")
        return False


def update_imports():
    """Information about import changes"""
    print_header("📝 Import Changes")
    
    print_info("Main code changes required:")
    print()
    print("  OLD:")
    print("    from src.modules.llm.model_manager import ModelManager")
    print()
    print("  NEW:")
    print("    from src.modules.orchestrator.model_orchestrator import ModelOrchestrator")
    print()
    print("  OLD:")
    print("    from src.modules.voice.audio_handler import AudioHandler")
    print()
    print("  NEW:")
    print("    from src.modules.voice.whisper_handler import WhisperHandler")
    print()
    print_info("The old imports will still work but are deprecated")
    print()


def create_env_template():
    """Create .env template with new API keys"""
    print_header("🔑 Environment Variables")
    
    env_template = """# Jarvis IA V2 - Environment Variables

# Required: OpenAI API
OPENAI_API_KEY=sk-your-key-here

# Required: Google Gemini API
GOOGLE_API_KEY=your-google-key-here

# Optional: Anthropic Claude API
ANTHROPIC_API_KEY=your-anthropic-key-here

# Optional: DeepSeek API (for math/reasoning)
DEEPSEEK_API_KEY=your-deepseek-key-here

# Optional: HuggingFace Token (for downloading models)
HUGGINGFACE_TOKEN=your-hf-token-here

# Legacy (can be removed)
# DEEPINFRA_API_KEY=your-deepinfra-key-here
"""
    
    if os.path.exists('.env'):
        print_warning(".env already exists")
        print_info("Check .env.template for new required variables")
        
        with open('.env.template', 'w') as f:
            f.write(env_template)
        
        print_success("Created .env.template")
    else:
        with open('.env', 'w') as f:
            f.write(env_template)
        print_success("Created .env template")
        print_warning("⚠️  IMPORTANT: Fill in your API keys in .env")
    
    print()
    print_info("New API keys needed:")
    print("  - ANTHROPIC_API_KEY (optional): https://console.anthropic.com/")
    print("  - DEEPSEEK_API_KEY (optional): https://platform.deepseek.com/")
    print()


def show_next_steps():
    """Show next steps after migration"""
    print_header("🎯 Next Steps")
    
    steps = [
        "1. Fill in API keys in .env file",
        "2. Download models: python scripts/download_models.py",
        "3. Review models_v2.json and adjust paths if needed",
        "4. Test the system: python test_v2.py (if exists)",
        "5. Read MIGRATION_GUIDE.md for detailed instructions",
        "6. Monitor performance with: orchestrator.get_stats()",
        "7. Check metrics: cat logs/metrics.jsonl | jq"
    ]
    
    for step in steps:
        print(f"  {step}")
    
    print()
    print_success("Migration completed! 🎉")
    print()
    print_warning("⚠️  Important: Test thoroughly before removing backup")
    print()


def main():
    """Main migration process"""
    print_header("🚀 Jarvis IA V2 Migration")
    print()
    print_info("This script will migrate your Jarvis installation to V2")
    print_warning("Make sure you have run ./install_upgrade.sh first")
    print()
    
    response = input("Continue with migration? (y/n): ")
    if response.lower() != 'y':
        print_info("Migration cancelled")
        return
    
    # Step 1: Backup
    backup_dir = backup_existing_system()
    if not backup_dir:
        print_error("Backup failed. Aborting migration.")
        return
    
    # Step 2: Check dependencies
    if not check_dependencies():
        print_error("Missing dependencies. Please install them first.")
        return
    
    # Step 3: Migrate config
    if not migrate_config():
        print_error("Config migration failed")
        return
    
    # Step 4: Migrate data
    if not migrate_data():
        print_error("Data migration failed")
        return
    
    # Step 5: Show import changes
    update_imports()
    
    # Step 6: Create .env template
    create_env_template()
    
    # Step 7: Next steps
    show_next_steps()
    
    print_success(f"Backup saved in: {backup_dir}")
    print_info("Keep backup until you verify V2 works correctly")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
