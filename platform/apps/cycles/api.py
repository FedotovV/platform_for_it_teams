from apps.cycles.models import Cycle

KIND_SURVEY = Cycle.KIND_SURVEY


def cycle_brief(cycle_id):
    cycle = Cycle.objects.filter(pk=cycle_id).first()
    if cycle is None:
        return None
    return {
        "id": cycle.id,
        "team_id": cycle.team_id,
        "kind": cycle.kind,
        "status": cycle.status,
    }


def survey_cycle_ids(team_id):
    return list(
        Cycle.objects.filter(team_id=team_id, kind=Cycle.KIND_SURVEY)
        .order_by("created_at", "id")
        .values_list("id", flat=True)
    )
