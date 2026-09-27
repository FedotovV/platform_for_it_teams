from apps.problems.models import Action, Problem


def team_id_of_problem(problem_id):
    row = Problem.objects.filter(pk=problem_id).first()
    if row is None:
        return None
    return row.team_id


def team_id_of_action(action_id):
    row = Action.objects.filter(pk=action_id).select_related("problem").first()
    if row is None:
        return None
    return row.problem.team_id


def problem_payload(problem, viewer_id):
    data = {
        "id": str(problem.id),
        "team_id": str(problem.team_id),
        "text": problem.text,
        "source": problem.source,
        "for_discussion": problem.for_discussion,
        "status": problem.status,
        "anonymous": problem.anonymous,
        "links": [
            {"cycle_id": str(link.cycle_id), "kind": link.kind}
            for link in problem.links.all().order_by("kind", "cycle_id")
        ],
    }
    if viewer_id is not None and problem.author_id == viewer_id:
        data["author_id"] = str(problem.author_id)
    return data


def action_payload(action):
    return {
        "id": str(action.id),
        "problem_id": str(action.problem_id),
        "owner_id": str(action.owner_id),
        "due_at": None if action.due_at is None else action.due_at.isoformat(),
        "status": action.status,
    }
