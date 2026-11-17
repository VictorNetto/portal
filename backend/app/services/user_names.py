"""Setting a user's names (Perfil, and admin edits), with the audit detail of what changed."""

from app.models.user import User
from app.schemas.user import NameFields


def name_changes(user: User, body: NameFields, fields: set[str]) -> dict:
    changes = {}
    for f in sorted(fields):
        new, old = getattr(body, f), getattr(user, f)
        if new != old:
            changes[f] = {"from": old, "to": new}
            setattr(user, f, new)
    return changes
