from django.urls import path

from apps.cycles import views

urlpatterns = [
    path("api/cycles/", views.cycles_view, name="cycles"),
    path("api/cycles/<uuid:cycle_id>/", views.cycle_view, name="cycle"),
    path("api/cycles/<uuid:cycle_id>/schedule/", views.schedule_view, name="cycle-schedule"),
    path("api/cycles/<uuid:cycle_id>/summary/", views.summary_view, name="cycle-summary"),
    path("api/cycles/<uuid:cycle_id>/advance/", views.advance_view, name="cycle-advance"),
    path(
        "api/teams/<uuid:team_id>/survey-interval/",
        views.interval_view,
        name="survey-interval",
    ),
]
