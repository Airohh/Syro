PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS organizations (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  credit_balance INTEGER DEFAULT 0,
  max_members INTEGER DEFAULT 5,
  status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT CHECK(role IN ('owner','admin','member')) NOT NULL,
  status TEXT DEFAULT 'active',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  organization_id INTEGER REFERENCES organizations(id),
  category TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
