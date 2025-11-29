-- Migration: Ajout des profils utilisateurs et système de permissions
-- Date: 2025-12-03
-- Description: Ajoute les champs de profil, les niveaux d'accès et la distinction entreprise/particulier

-- ============================================================================
-- 1. EXTENSION TABLE USERS (Profils utilisateurs)
-- ============================================================================

-- Ajouter les champs de profil utilisateur
ALTER TABLE users ADD COLUMN first_name TEXT;
ALTER TABLE users ADD COLUMN last_name TEXT;
ALTER TABLE users ADD COLUMN avatar_url TEXT;
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN phone TEXT;
ALTER TABLE users ADD COLUMN preferences TEXT;  -- JSON pour préférences personnalisées
ALTER TABLE users ADD COLUMN last_login TEXT;
ALTER TABLE users ADD COLUMN updated_at TEXT;

-- Mettre à jour updated_at avec la valeur par défaut
UPDATE users SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL;

-- ============================================================================
-- 2. EXTENSION TABLE ORGANIZATIONS (Type entreprise/particulier)
-- ============================================================================

-- Ajouter le type d'organisation (enterprise ou individual)
ALTER TABLE organizations ADD COLUMN org_type TEXT CHECK(org_type IN ('enterprise', 'individual')) DEFAULT 'individual';
ALTER TABLE organizations ADD COLUMN company_name TEXT;  -- Pour entreprises
ALTER TABLE organizations ADD COLUMN address TEXT;
ALTER TABLE organizations ADD COLUMN contact_email TEXT;
ALTER TABLE organizations ADD COLUMN settings TEXT;  -- JSON pour paramètres spécifiques

-- ============================================================================
-- 3. TABLE DOCUMENT_ACCESS_LEVELS (Niveaux d'accès aux documents)
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_access_levels (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,  -- 'public', 'internal', 'confidential', 'restricted'
  description TEXT,
  priority INTEGER NOT NULL DEFAULT 0,  -- Plus élevé = plus restrictif
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insérer les niveaux d'accès par défaut
INSERT OR IGNORE INTO document_access_levels (id, name, description, priority) VALUES
  (1, 'public', 'Document accessible à tous les membres de l''organisation', 0),
  (2, 'internal', 'Document interne à l''organisation', 1),
  (3, 'confidential', 'Document confidentiel, accès restreint', 2),
  (4, 'restricted', 'Document très restreint, accès limité', 3);

-- ============================================================================
-- 4. TABLE DOCUMENT_QUALITY_LEVELS (Niveaux de qualité)
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_quality_levels (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,  -- 'draft', 'reviewed', 'verified', 'official'
  description TEXT,
  priority INTEGER NOT NULL DEFAULT 0,  -- Plus élevé = meilleure qualité
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insérer les niveaux de qualité par défaut
INSERT OR IGNORE INTO document_quality_levels (id, name, description, priority) VALUES
  (1, 'draft', 'Brouillon, en cours de rédaction', 0),
  (2, 'reviewed', 'Document relu et validé', 1),
  (3, 'verified', 'Document vérifié et approuvé', 2),
  (4, 'official', 'Document officiel et final', 3);

-- ============================================================================
-- 5. EXTENSION TABLE DOCUMENTS (Niveaux d'accès et qualité)
-- ============================================================================

-- Ajouter les niveaux d'accès et de qualité aux documents (sans DEFAULT pour REFERENCES)
ALTER TABLE documents ADD COLUMN access_level_id INTEGER;
ALTER TABLE documents ADD COLUMN quality_level_id INTEGER;
ALTER TABLE documents ADD COLUMN created_by_user_id INTEGER;
ALTER TABLE documents ADD COLUMN access_notes TEXT;  -- Notes sur les restrictions d'accès

-- Mettre à jour les valeurs par défaut
UPDATE documents SET access_level_id = 1 WHERE access_level_id IS NULL;
UPDATE documents SET quality_level_id = 1 WHERE quality_level_id IS NULL;

-- ============================================================================
-- 6. TABLE USER_PERMISSIONS (Permissions par utilisateur)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_permissions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  
  -- Permissions d'accès aux documents
  max_access_level_id INTEGER REFERENCES document_access_levels(id) DEFAULT 1,  -- Niveau max accessible
  min_quality_level_id INTEGER REFERENCES document_quality_levels(id) DEFAULT 1,  -- Qualité min requise
  
  -- Permissions spécifiques
  can_upload_documents BOOLEAN DEFAULT 1,
  can_delete_documents BOOLEAN DEFAULT 0,
  can_manage_users BOOLEAN DEFAULT 0,
  can_view_analytics BOOLEAN DEFAULT 1,
  can_export_data BOOLEAN DEFAULT 0,
  
  -- Métadonnées
  granted_by_user_id INTEGER REFERENCES users(id),  -- Qui a accordé cette permission
  granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT,  -- Optionnel: expiration des permissions
  notes TEXT,
  
  UNIQUE(user_id, organization_id)
);

-- ============================================================================
-- 7. TABLE DOCUMENT_SHARES (Partage de documents entre utilisateurs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_shares (
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  shared_with_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shared_by_user_id INTEGER NOT NULL REFERENCES users(id),
  access_level_id INTEGER REFERENCES document_access_levels(id),
  can_edit BOOLEAN DEFAULT 0,
  can_download BOOLEAN DEFAULT 1,
  expires_at TEXT,  -- Optionnel: expiration du partage
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(document_id, shared_with_user_id)
);

-- ============================================================================
-- 8. INDEXES pour performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_documents_access ON documents(access_level_id);
CREATE INDEX IF NOT EXISTS idx_documents_quality ON documents(quality_level_id);
CREATE INDEX IF NOT EXISTS idx_documents_creator ON documents(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_user ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_org ON user_permissions(organization_id);
CREATE INDEX IF NOT EXISTS idx_document_shares_doc ON document_shares(document_id);
CREATE INDEX IF NOT EXISTS idx_document_shares_user ON document_shares(shared_with_user_id);

-- ============================================================================
-- 9. TRIGGERS pour updated_at automatique
-- ============================================================================

-- Trigger pour mettre à jour updated_at sur users
CREATE TRIGGER IF NOT EXISTS update_users_updated_at
  AFTER UPDATE ON users
  FOR EACH ROW
BEGIN
  UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger pour mettre à jour updated_at sur documents
CREATE TRIGGER IF NOT EXISTS update_documents_updated_at
  AFTER UPDATE ON documents
  FOR EACH ROW
BEGIN
  UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

