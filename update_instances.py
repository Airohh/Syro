"""Script to update all Syro instances with code from Syro base."""

import os
import shutil
import sys
from pathlib import Path


def find_instances(base_dir: Path) -> list[Path]:
    """Find all Syro instance directories."""
    instances = []
    for item in base_dir.iterdir():
        if item.is_dir() and item.name.startswith("Syro") and item.name != "Syro":
            # Check if it's an instance (has app/ directory)
            if (item / "app").exists():
                instances.append(item)
    return sorted(instances)


def update_instance(instance_dir: Path, syro_base: Path, dry_run: bool = False) -> bool:
    """Update a single instance with code from Syro base."""
    instance_name = instance_dir.name
    
    if not (instance_dir / "app").exists():
        print(f"  Ignore {instance_name} (pas de dossier app/)")
        return False
    
    print(f"  Mise a jour: {instance_name}")
    
    # Files to update
    files_to_update = [
        "requirements.txt",
        "docker-compose.yml",
        "pytest.ini",
    ]
    
    # Directories to update
    dirs_to_update = [
        "app",
        "scripts",
        "tests",
    ]
    
    if not dry_run:
        # Update files
        for file_name in files_to_update:
            src = syro_base / file_name
            dst = instance_dir / file_name
            if src.exists():
                shutil.copy2(src, dst)
                print(f"    - {file_name}")
        
        # Update directories
        for dir_name in dirs_to_update:
            src = syro_base / dir_name
            dst = instance_dir / dir_name
            if src.exists():
                # Remove old directory
                if dst.exists():
                    shutil.rmtree(dst)
                # Copy new directory
                shutil.copytree(src, dst)
                print(f"    - {dir_name}/")
        
        # Update schema.sql
        schema_src = syro_base / "db" / "schema.sql"
        schema_dst = instance_dir / "db" / "schema.sql"
        if schema_src.exists():
            if not schema_dst.parent.exists():
                schema_dst.parent.mkdir(parents=True)
            shutil.copy2(schema_src, schema_dst)
            print(f"    - db/schema.sql")
    else:
        # Dry run - just list what would be updated
        for file_name in files_to_update:
            if (syro_base / file_name).exists():
                print(f"    - {file_name} (serait mis a jour)")
        for dir_name in dirs_to_update:
            if (syro_base / dir_name).exists():
                print(f"    - {dir_name}/ (serait mis a jour)")
    
    return True


def main():
    """Main function."""
    base_dir = Path(__file__).parent
    syro_base = base_dir / "Syro"
    
    # Check if Syro base exists
    if not syro_base.exists():
        print("Erreur: Le dossier 'Syro' n'existe pas.")
        print("   Creez d'abord le dossier Syro avec le code commun.")
        return False
    
    # Find all instances
    instances = find_instances(base_dir)
    
    if not instances:
        print("Aucune instance trouvee.")
        return False
    
    print(f"Instances trouvees: {len(instances)}")
    for inst in instances:
        print(f"  - {inst.name}")
    
    # Check for dry run
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    if dry_run:
        print("\nMode dry-run (aucune modification ne sera faite)")
    else:
        response = input("\nVoulez-vous mettre a jour toutes ces instances? (o/N): ")
        if response.lower() != 'o':
            print("Operation annulee.")
            return False
    
    print("\nMise a jour des instances...")
    
    updated = 0
    for instance_dir in instances:
        if update_instance(instance_dir, syro_base, dry_run=dry_run):
            updated += 1
    
    if dry_run:
        print(f"\nDry-run termine. {updated} instance(s) seraient mises a jour.")
    else:
        print(f"\nMise a jour terminee. {updated} instance(s) mise(s) a jour.")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

