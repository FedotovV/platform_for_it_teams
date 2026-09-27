from django.urls import path

from apps.diagnostics import views

urlpatterns = [
    path("api/cycles/<uuid:cycle_id>/snapshot/", views.snapshot_view, name="cycle-snapshot"),
    path("api/teams/selected/radar/", views.radar_api, name="radar-api"),
    path("teams/selected/radar/", views.radar_page, name="radar-page"),
    path(
        "api/organizations/<uuid:organization_id>/snapshots/",
        views.org_snapshots,
        name="org-snapshots",
    ),
]
