import json

from django.http import JsonResponse


def loads_object(request):
    raw = request.body.decode() if request.body else "{}"
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def respond(payload, status=200):
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})
