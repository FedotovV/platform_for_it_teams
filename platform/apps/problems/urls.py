from django.urls import path

from apps.problems import views

urlpatterns = [
    path("api/problems/", views.problems_view, name="problems"),
    path("api/problems/<uuid:problem_id>/", views.problem_view, name="problem"),
    path(
        "api/problems/<uuid:problem_id>/status/",
        views.problem_status_view,
        name="problem-status",
    ),
    path("api/problems/<uuid:problem_id>/carry/", views.carry_view, name="problem-carry"),
    path(
        "api/problems/<uuid:problem_id>/actions/",
        views.actions_view,
        name="problem-actions",
    ),
    path("api/actions/<uuid:action_id>/", views.action_view, name="action"),
    path(
        "api/actions/<uuid:action_id>/status/",
        views.action_status_view,
        name="action-status",
    ),
]
