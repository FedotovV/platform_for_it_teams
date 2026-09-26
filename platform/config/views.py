from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import JsonResponse


@login_not_required
def health(request):
    connection.ensure_connection()
    return JsonResponse({"status": "ok"})
