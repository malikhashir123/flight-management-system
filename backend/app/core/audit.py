import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.all_models import AdminAuditLog, SystemAuditTrail

async def log_admin_action(
    db: AsyncSession,
    admin_user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> AdminAuditLog:
    """Logs administrative mutations into the immutable admin_audit_logs table."""
    audit_entry = AdminAuditLog(
        id=str(uuid.uuid4()),
        admin_user_id=admin_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit_entry)
    return audit_entry

async def log_system_decision(
    db: AsyncSession,
    event_type: str,
    actor_system: str, # 'FASTAPI', 'N8N', 'HUMAN'
    actor_id: str,
    entity_type: str,
    entity_id: str,
    rule_applied: str,
    decision_metadata: Dict[str, Any]
) -> SystemAuditTrail:
    """Logs automated business decisions into the immutable system_audit_trail ledger."""
    trail_entry = SystemAuditTrail(
        id=str(uuid.uuid4()),
        event_type=event_type,
        actor_system=actor_system,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        rule_applied=rule_applied,
        decision_metadata=decision_metadata,
        created_at=datetime.now(timezone.utc)
    )
    db.add(trail_entry)
    return trail_entry
