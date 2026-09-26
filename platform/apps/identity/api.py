def current_user_id(request):
    """Идентификатор текущего пользователя. Доменные модули берут только его."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return None
    return user.pk
