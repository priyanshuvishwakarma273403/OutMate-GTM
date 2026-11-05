"""Execution and tenant context primitives for MCP requests."""

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class PrincipalContext:
    """Represents the authenticated caller and their authorization boundaries."""

    tenant_id: str = "default_tenant"
    user_id: str = "anonymous_user"
    scopes: set[str] = field(default_factory=set)
    is_authenticated: bool = False
    auth_mode: str = "none"

    def has_scope(self, required_scope: str) -> bool:
        """Check if principal possesses the required permission scope."""
        if not self.is_authenticated and self.auth_mode == "none":
            # In unauthenticated local dev mode, all scopes are permitted
            return True
        return required_scope in self.scopes or "*" in self.scopes


_current_principal: ContextVar[PrincipalContext | None] = ContextVar(
    "current_principal", default=None
)


def get_current_principal() -> PrincipalContext:
    """Retrieve principal context for the active async request execution."""
    principal = _current_principal.get()
    return principal if principal is not None else PrincipalContext()


def set_current_principal(principal: PrincipalContext) -> None:
    """Set principal context for the active async request execution."""
    _current_principal.set(principal)
