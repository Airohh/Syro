"""Test script to verify the multi-instance structure."""

import sys
import pytest
from pathlib import Path

def test_syro_base():
    """Test that Syro base exists and has essential files."""
    print("Test 1: Verification du dossier Syro/")
    syro_base = Path("Syro")
    
    if not syro_base.exists():
        print("  ERREUR: Le dossier Syro/ n'existe pas")
        return False
    
    essential_files = [
        "app/main.py",
        "app/config.py",
        "app/domains.py",
        "requirements.txt",
        "docker-compose.yml",
        "db/schema.sql",
    ]
    
    all_ok = True
    for file_path in essential_files:
        full_path = syro_base / file_path
        if full_path.exists():
            print(f"  OK: {file_path}")
        else:
            print(f"  ERREUR: {file_path} manquant")
            all_ok = False
    
    return all_ok

@pytest.mark.parametrize("instance_name", ["SyroTech", "SyroMed"])
def test_instance(instance_name: str):
    """Test that an instance exists and is properly configured."""
    print(f"\nTest: Verification de {instance_name}/")
    instance_dir = Path(instance_name)
    
    if not instance_dir.exists():
        print(f"  ERREUR: Le dossier {instance_name}/ n'existe pas")
        return False
    
    essential_files = [
        "app/main.py",
        "app/config.py",
        "requirements.txt",
        "docker-compose.yml",
        "db/schema.sql",
        ".env",
    ]
    
    all_ok = True
    for file_path in essential_files:
        full_path = instance_dir / file_path
        if full_path.exists():
            print(f"  OK: {file_path}")
        else:
            print(f"  ERREUR: {file_path} manquant")
            all_ok = False
    
    # Check .env content
    env_file = instance_dir / ".env"
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        if "DOMAIN=" in content:
            domain_line = [l for l in content.split("\n") if l.startswith("DOMAIN=")][0]
            print(f"  OK: Configuration DOMAIN trouvee: {domain_line.split('=')[1]}")
        else:
            print(f"  ERREUR: DOMAIN non trouve dans .env")
            all_ok = False
    
    return all_ok

def test_imports():
    """Test that imports work."""
    print("\nTest: Verification des imports")
    
    try:
        sys.path.insert(0, str(Path("Syro").absolute()))
        from app.domains import get_domain_config, list_domains
        from app.config import settings
        
        print("  OK: Import de app.domains")
        print("  OK: Import de app.config")
        
        # Test domain configs
        domains = ["tech", "medical", "legal", "finance", "education", "general"]
        for domain in domains:
            config = get_domain_config(domain)
            print(f"  OK: Domaine '{domain}' -> {config.name}")
        
        return True
    except Exception as e:
        print(f"  ERREUR: {e}")
        return False

def test_create_script():
    """Test that create script exists."""
    print("\nTest: Verification du script create_syro_instance.py")
    
    script = Path("create_syro_instance.py")
    if script.exists():
        print("  OK: Script existe")
        return True
    else:
        print("  ERREUR: Script manquant")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Tests de la structure multi-instances Syro")
    print("=" * 60)
    
    results = []
    
    # Test Syro base
    results.append(("Syro base", test_syro_base()))
    
    # Test instances
    instances = ["SyroTech", "SyroMed"]
    for instance in instances:
        results.append((instance, test_instance(instance)))
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test script
    results.append(("Script creation", test_create_script()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Resume des tests")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "OK" if result else "ERREUR"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("Tous les tests sont passes !")
        return 0
    else:
        print("Certains tests ont echoue.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

