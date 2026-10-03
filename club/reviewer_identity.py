"""Public reviewer aliases derived only from immutable authenticated provenance."""
import hashlib


def reviewer_identity(reviewer_id):
    # Account names may contain emails or other personal data. Do not serialize
    # them (or raw account IDs); a stable alias identifies the recorded reviewer.
    if not reviewer_id:
        return None
    alias = hashlib.sha256(('ai-room-reviewer-v1:' + reviewer_id).encode()).hexdigest()[:16]
    return dict(display_name='Редактор · ' + alias, attribution='recorded_reviewer_alias')
