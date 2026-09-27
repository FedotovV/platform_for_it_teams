from apps.cycles.api import survey_cycle_ids
from apps.diagnostics.models import ColorBound, SurveySnapshot


def color_for(score):
    bounds = list(ColorBound.objects.all())
    if not bounds:
        return None
    for bound in bounds:
        if bound.min_score <= score <= bound.max_score:
            return bound.label
    return None


def _blocks(raw, *, with_color):
    painted = []
    for block in raw:
        item = {"code": block["code"], "score": block["score"]}
        if with_color:
            item["color"] = color_for(block["score"])
        painted.append(item)
    return painted


def snapshot_for(cycle_id, *, with_color=True):
    row = SurveySnapshot.objects.filter(cycle_id=cycle_id).first()
    if row is None:
        return None
    return {
        "cycle_id": str(row.cycle_id),
        "scale_version": row.scale_version,
        "blocks": _blocks(row.blocks, with_color=with_color),
    }


def team_snapshot_pair(team_id, *, with_color):
    found = []
    for cycle_id in survey_cycle_ids(team_id):
        payload = snapshot_for(cycle_id, with_color=with_color)
        if payload is not None:
            found.append(payload)
    latest = found[-1] if found else None
    previous = found[-2] if len(found) > 1 else None
    return latest, previous
