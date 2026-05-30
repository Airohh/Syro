PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  credit_balance INTEGER DEFAULT 0,
  max_members INTEGER DEFAULT 5,
  status TEXT DEFAULT 'active',
  org_type TEXT CHECK(org_type IN ('enterprise', 'individual')) DEFAULT 'individual',
  company_name TEXT,
  address TEXT,
  contact_email TEXT,
  settings TEXT
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT CHECK(role IN ('owner','admin','member')) NOT NULL,
  status TEXT DEFAULT 'active',
  first_name TEXT,
  last_name TEXT,
  avatar_url TEXT,
  bio TEXT,
  phone TEXT,
  preferences TEXT,
  last_login TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  name TEXT NOT NULL,
  secret TEXT NOT NULL UNIQUE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage_events (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  user_id INTEGER REFERENCES users(id),
  event_type TEXT NOT NULL,
  amount INTEGER NOT NULL,
  metadata TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  title TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY,
  conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  sender_type TEXT CHECK(sender_type IN ('user','assistant','tool')) NOT NULL,
  sender_id INTEGER,
  content TEXT NOT NULL,
  token_usage INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ACCESS & QUALITY LEVELS
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_access_levels (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  priority INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO document_access_levels (id, name, description, priority) VALUES
  (1, 'public',       'Accessible à tous les membres de l''organisation', 0),
  (2, 'internal',     'Document interne à l''organisation', 1),
  (3, 'confidential', 'Document confidentiel, accès restreint', 2),
  (4, 'restricted',   'Document très restreint, accès limité', 3);

CREATE TABLE IF NOT EXISTS document_quality_levels (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  priority INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO document_quality_levels (id, name, description, priority) VALUES
  (1, 'draft',    'Brouillon, en cours de rédaction', 0),
  (2, 'reviewed', 'Document relu et validé', 1),
  (3, 'verified', 'Document vérifié et approuvé', 2),
  (4, 'official', 'Document officiel et final', 3);

-- ============================================================================
-- DOCUMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  mime_type TEXT,
  checksum TEXT,
  status TEXT DEFAULT 'active',
  tags TEXT,
  version INTEGER DEFAULT 1,
  ingestion_status TEXT DEFAULT 'pending',
  ingestion_error TEXT,
  chunk_count INTEGER DEFAULT 0,
  source_type TEXT,
  access_level_id INTEGER DEFAULT 1 REFERENCES document_access_levels(id),
  quality_level_id INTEGER DEFAULT 1 REFERENCES document_quality_levels(id),
  created_by_user_id INTEGER REFERENCES users(id),
  access_notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doc_chunks (
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_embeddings (
  id INTEGER PRIMARY KEY,
  chunk_id INTEGER NOT NULL REFERENCES doc_chunks(id) ON DELETE CASCADE,
  organization_id INTEGER NOT NULL,
  embedding BLOB NOT NULL
);

-- ============================================================================
-- PERMISSIONS & SHARING
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_permissions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  max_access_level_id INTEGER DEFAULT 1 REFERENCES document_access_levels(id),
  min_quality_level_id INTEGER DEFAULT 1 REFERENCES document_quality_levels(id),
  can_upload_documents BOOLEAN DEFAULT 1,
  can_delete_documents BOOLEAN DEFAULT 0,
  can_manage_users BOOLEAN DEFAULT 0,
  can_view_analytics BOOLEAN DEFAULT 1,
  can_export_data BOOLEAN DEFAULT 0,
  granted_by_user_id INTEGER REFERENCES users(id),
  granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT,
  notes TEXT,
  UNIQUE(user_id, organization_id)
);

CREATE TABLE IF NOT EXISTS document_shares (
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  shared_with_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shared_by_user_id INTEGER NOT NULL REFERENCES users(id),
  access_level_id INTEGER REFERENCES document_access_levels(id),
  can_edit BOOLEAN DEFAULT 0,
  can_download BOOLEAN DEFAULT 1,
  expires_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(document_id, shared_with_user_id)
);

-- ============================================================================
-- EVENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER REFERENCES organizations(id),
  category TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_users_org              ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_documents_org          ON documents(organization_id);
CREATE INDEX IF NOT EXISTS idx_documents_status       ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_access       ON documents(access_level_id);
CREATE INDEX IF NOT EXISTS idx_documents_quality      ON documents(quality_level_id);
CREATE INDEX IF NOT EXISTS idx_documents_creator      ON documents(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc         ON doc_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_conversations_org      ON conversations(organization_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation  ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_org       ON usage_events(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_user  ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_org   ON user_permissions(organization_id);
CREATE INDEX IF NOT EXISTS idx_document_shares_doc    ON document_shares(document_id);
CREATE INDEX IF NOT EXISTS idx_document_shares_user   ON document_shares(shared_with_user_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE TRIGGER IF NOT EXISTS update_users_updated_at
  AFTER UPDATE ON users
  FOR EACH ROW
BEGIN
  UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_documents_updated_at
  AFTER UPDATE ON documents
  FOR EACH ROW
BEGIN
  UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
