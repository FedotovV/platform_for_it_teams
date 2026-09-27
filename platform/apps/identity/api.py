def current_user_id(request):
    """Идентификатор текущего пользователя. Доменные модули берут только его."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return None
    return user.pk


def user_exists(user_id):
    """Есть ли учётная запись с этим id. Доменные модули не читают модель входа."""
    from apps.identity.models import User

    if user_id is None:
        return False
    return User.objects.filter(pk=user_id).exists()
