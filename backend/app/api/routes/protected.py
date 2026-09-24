"""Protected-route examples demonstrating the RBAC gates.

- /protected/admin: academic management surface (ADMIN, SUPER_ADMIN).
- /protected/staff: staff surface (ADMIN, SUPER_ADMIN, FACULTY).

STUDENT has no management surface: every endpoint here rejects it, which is
exactly what the RBAC tests assert. Real Phase 4+ endpoints reuse
require_roles the same way.
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole

router = APIRouter(tags=["protected"])

admin_only = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
staff_only = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY)


@router.get("/admin")
async def admin_surface(user: User = Depends(admin_only)) -> dict:
    return {"surface": "admin", "role": user.role.value}


@router.get("/staff")
async def staff_surface(user: User = Depends(staff_only)) -> dict:
    return {"surface": "staff", "role": user.role.value}
