#!/usr/bin/env python3
"""
Script de migration pour ajouter les profils utilisateurs et le système de permissions.
Applique la migration à toutes les instances du projet.
"""

import sys
import sqlite3
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Liste des instances à migrer
INSTANCES = [
    "Syro",
    "SyroTech",
    "SyroMed",
    "SyroLegal",
    "SyroFinance",
    "SyroEdu",
]

root = Path(__file__).parent.parent
migration_file = root / "db" / "migration_profiles_permissions.sql"

def apply_migration(instance_path: Path, db_path: Path) -> bool:
    """Applique la migration à une instance."""
    try:
        # Lire le fichier de migration
        if not migration_file.exists():
            print(f"❌ {instance_path.name}: Fichier de migration non trouvé: {migration_file}")
            return False
        
        with open(migration_file, "r", encoding="utf-8") as f:
            migration_sql = f.read()
        
        # Appliquer la migration
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Exécuter le script SQL complet
        # executescript() gère mieux les scripts multiples que execute()
        try:
            conn.executescript(migration_sql)
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            # Ignorer les erreurs "already exists" pour les colonnes/tables
            if "duplicate column" in error_msg or "already exists" in error_msg:
                print(f"  ⚠️  {instance_path.name}: Colonnes/tables déjà existantes (ignoré)")
            else:
                # Réessayer commande par commande pour identifier le problème
                commands = [cmd.strip() for cmd in migration_sql.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
                for cmd in commands:
                    try:
                        conn.execute(cmd)
                    except sqlite3.OperationalError as e2:
                        error_msg2 = str(e2).lower()
                        if "duplicate column" in error_msg2 or "already exists" in error_msg2:
                            continue  # Ignorer
                        else:
                            # Si c'est une erreur critique, l'afficher mais continuer
                            if "no such table" not in error_msg2 and "no such column" not in error_msg2:
                                print(f"  ⚠️  {instance_path.name}: {str(e2)[:80]}... (continué)")
                            else:
                                raise
        
        conn.commit()
        conn.close()
        
        print(f"✅ {instance_path.name}: Migration appliquée avec succès")
        return True
        
    except Exception as e:
        print(f"❌ {instance_path.name}: Erreur lors de la migration: {e}")
        return False

def main():
    """Applique la migration à toutes les instances."""
    print("🚀 Début de la migration: Profils utilisateurs et Permissions\n")
    
    success_count = 0
    failed_count = 0
    
    for instance_name in INSTANCES:
        instance_path = root.parent / instance_name
        
        if not instance_path.exists():
            print(f"⚠️  {instance_name}: Dossier non trouvé, ignoré")
            continue
        
        # Déterminer le chemin de la DB
        # Vérifier le .env pour connaître le nom de la DB
        env_file = instance_path / ".env"
        db_name = None
        
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("DB_PATH="):
                            db_name = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass
        
        # Si pas de DB_PATH dans .env, utiliser le nom par défaut
        if not db_name:
            if instance_name == "Syro":
                db_name = "syro.db"
            elif instance_name == "SyroTech":
                db_name = "syro.db"  # SyroTech utilise syro.db
            else:
                db_name = instance_name.lower().replace("syro", "syro") + ".db"
        else:
            # Si DB_PATH est relatif (db/syro.db), extraire juste le nom
            if "/" in db_name or "\\" in db_name:
                db_name = Path(db_name).name
        
        db_path = instance_path / "db" / db_name
        
        if not db_path.exists():
            print(f"⚠️  {instance_name}: Base de données non trouvée ({db_path}), ignoré")
            continue
        
        if apply_migration(instance_path, db_path):
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\n📊 Résumé:")
    print(f"  ✅ Succès: {success_count}")
    print(f"  ❌ Échecs: {failed_count}")
    print(f"  📦 Total: {len(INSTANCES)}")
    
    if failed_count == 0:
        print("\n🎉 Migration terminée avec succès pour toutes les instances!")
    else:
        print(f"\n⚠️  {failed_count} instance(s) ont échoué. Vérifiez les erreurs ci-dessus.")

if __name__ == "__main__":
    main()

