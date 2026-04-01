"""Template context available on every page."""

from .models import Wishlist


def nav_wishlist(request):
    """Header badge: saved cars count for the current user (0 if anonymous)."""
    if request.user.is_authenticated:
        n = Wishlist.objects.filter(user=request.user).count()
    else:
        n = 0
    return {'nav_wishlist_count': n}
