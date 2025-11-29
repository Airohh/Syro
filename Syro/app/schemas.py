from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr

class Organization(BaseModel):
    id: int
    name: str
    credit_balance: int
    max_members: int
    status: str
    org_type: Optional[str] = "individual"  # 'enterprise' ou 'individual'
    company_name: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    settings: Optional[dict[str, Any]] = None

class User(BaseModel):
    id: int
    organization_id: int
    email: EmailStr
    role: str
    status: str
    created_at: datetime
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    preferences: Optional[dict[str, Any]] = None
    last_login: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    organization_id: int
    role: str
    exp: int

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class MessageCreate(BaseModel):
    conversation_id: Optional[int] = None
    content: str

class SourceCitation(BaseModel):
    text: str
    score: float
    metadata: dict | None = None

class MessageResponse(BaseModel):
    conversation_id: int
    message: str
    usage: int
    sources: list[SourceCitation] | None = None

class DocumentTextUpload(BaseModel):
    title: str
    content: str
    tags: str | None = None

class DocumentUploadResponse(BaseModel):
    document_id: int
    version: int
    status: str
    chunk_count: int = 0

class OrganizationCreate(BaseModel):
    name: str
    credit_balance: int = 0
    max_members: int = 5

class OrganizationCreditUpdate(BaseModel):
    amount: int

class UserCreate(BaseModel):
    organization_id: int
    email: EmailStr
    password: str
    role: str = "member"

class DocumentStats(BaseModel):
    total: int
    by_domain: dict[str, int]
    last_7_days: int
    last_30_days: int
    pending: int
    failed: int

class StorageStats(BaseModel):
    total_bytes: int
    total_mb: float
    total_gb: float
    chunks_indexed: int

class UsageStats(BaseModel):
    conversations: int
    messages: int
    recent_conversations_7d: int

class ProfileStats(BaseModel):
    documents: DocumentStats
    storage: StorageStats
    usage: UsageStats

class DocumentClassification(BaseModel):
    domain: str
    confidence: float
    alternatives: list[dict[str, Any]] = []

class DocumentUploadWithClassificationResponse(BaseModel):
    document_id: int
    version: int
    status: str
    chunk_count: int = 0
    classification: DocumentClassification

# ============================================================================
# Profils et Permissions
# ============================================================================

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    preferences: Optional[dict[str, Any]] = None

class AccessLevel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    priority: int

class QualityLevel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    priority: int

class UserPermissions(BaseModel):
    user_id: int
    organization_id: int
    max_access_level_id: int
    min_quality_level_id: int
    can_upload_documents: bool
    can_delete_documents: bool
    can_manage_users: bool
    can_view_analytics: bool
    can_export_data: bool

class UserPermissionsUpdate(BaseModel):
    max_access_level_id: Optional[int] = None
    min_quality_level_id: Optional[int] = None
    can_upload_documents: Optional[bool] = None
    can_delete_documents: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_view_analytics: Optional[bool] = None
    can_export_data: Optional[bool] = None

class DocumentShare(BaseModel):
    document_id: int
    shared_with_user_id: int
    access_level_id: Optional[int] = None
    can_edit: bool = False
    can_download: bool = True
    expires_at: Optional[datetime] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    org_type: Optional[str] = None  # 'enterprise' ou 'individual'
    company_name: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    max_members: Optional[int] = None
    settings: Optional[dict[str, Any]] = None