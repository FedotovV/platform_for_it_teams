from django.urls import include, path

from config.views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("", include("apps.identity.urls")),
    path("", include("apps.teams.urls")),
    path("", include("apps.access.urls")),
    path("", include("apps.cycles.urls")),
    path("", include("apps.diagnostics.urls")),
    path("", include("apps.problems.urls")),
    path("", include("apps.history.urls")),
    path("", include("apps.workspace.urls")),
]
