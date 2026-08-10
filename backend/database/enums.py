from enum import Enum

class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"   # Phase 2+: Platform-level admin
    PLATFORM    = "PLATFORM"      # Phase 2+: Platform monitoring (read-only system)
    ADMIN       = "ADMIN"
    ANNOTATOR   = "ANNOTATOR"
    REVIEWER    = "REVIEWER"


class AudioStatus(str, Enum):
    UNASSIGNED      = "UNASSIGNED"
    ASSIGNED        = "ASSIGNED"
    IN_PROGRESS     = "IN_PROGRESS"
    SUBMITTED       = "SUBMITTED"
    REWORK_REQUIRED = "REWORK_REQUIRED"   # Reviewer rejected → back to annotator
    COMPLETED       = "COMPLETED"          # Reviewer approved → terminal state


class AnnotationState(str, Enum):
    DRAFT     = "DRAFT"
    SUBMITTED = "SUBMITTED"
    RETURNED  = "RETURNED"
    APPROVED  = "APPROVED"


class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ValidationState(str, Enum):
    VALID        = "VALID"
    HAS_ERRORS   = "HAS_ERRORS"
    HAS_WARNINGS = "HAS_WARNINGS"


class ApprovalStatus(str, Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuditAction(str, Enum):
    LOGIN    = "LOGIN"
    LOGOUT   = "LOGOUT"
    CREATE   = "CREATE"
    UPDATE   = "UPDATE"
    DELETE   = "DELETE"
    SUBMIT   = "SUBMIT"
    RETURN   = "RETURN"
    APPROVE  = "APPROVE"
    REJECT   = "REJECT"
    # Queue workflow actions
    TASK_ASSIGNED        = "TASK_ASSIGNED"
    TASK_OPENED          = "TASK_OPENED"
    TASK_SUBMITTED       = "TASK_SUBMITTED"
    TASK_RETURNED        = "TASK_RETURNED"
    TASK_REASSIGNED      = "TASK_REASSIGNED"
    TASK_AUTO_RELEASED   = "TASK_AUTO_RELEASED"
    TASK_COMPLETED       = "TASK_COMPLETED"
    # Super Admin specific actions
    IMPERSONATE      = "IMPERSONATE"
    FORCE_LOGOUT     = "FORCE_LOGOUT"
    LOCK_USER        = "LOCK_USER"
    UNLOCK_USER      = "UNLOCK_USER"
    PROMOTE_USER     = "PROMOTE_USER"
    DEMOTE_USER      = "DEMOTE_USER"
    SYSTEM_CONFIG    = "SYSTEM_CONFIG"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"
    DATA_RECOVERY    = "DATA_RECOVERY"