from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),

    # Posts
    path("posts/", views.post_list, name="all_posts"),
    path("posts/new/", views.new_post, name="new_post"),
    path("posts/my/", lambda req: views.post_list(req, "my"), name="my_posts"),
    path("posts/liked/", lambda req: views.post_list(req, "liked"), name="liked_posts"),
    path("posts/feed/", lambda req: views.post_list(req, "feed"), name="feed_posts"),

    # Post interactions
    path("posts/<int:post_id>/like/", views.like_post, name="like_post"),
    path("posts/<int:post_id>/edit/", views.edit_post, name="edit_post"),

    # Search
    path("search/", views.search, name="search"),

    # User profiles
    path("user/<int:user_id>/", views.user_page, name="user_page"),
]
