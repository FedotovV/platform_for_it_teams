import uuid

from django.shortcuts import render

from apps.identity.api import user_label


def parse_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def safe_next(value):
    if not isinstance(value, str):
        return "/"
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    return value


def notice(request, detail, status=400):
    return render(request, "workspace/notice.html", {"detail": detail}, status=status)


def input_datetime(value):
    if not value:
        return ""
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1]
    plus = text.find("+", 10)
    if plus != -1:
        text = text[:plus]
    return text[:16]


def actor_label(user_id):
    label = user_label(user_id)
    if label:
        return label
    if user_id:
        return str(user_id)
    return ""
