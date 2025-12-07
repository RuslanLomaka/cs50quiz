from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# ------------------------
# USER MODEL
# ------------------------
class User(AbstractUser):
    """
    Custom user model with follower relationships and optional profile info.
    """

    # Each user can follow many users and be followed by many users.
    followers = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="following",
        blank=True,
    )

    # Helper methods

    def follows(self, user) -> bool:
        """
        Return True if this user follows the given user.
        Self-follow is not allowed.
        """
        if user == self:
            return False
        return self.following.filter(id=user.id).exists()

    def follow(self, user) -> None:
        """
        Make this user follow the given user.
        Self-follow is ignored.
        """
        if user != self:
            self.following.add(user)

    def unfollow(self, user) -> None:
        """
        Make this user unfollow the given user.
        Self-unfollow is ignored.
        """
        if user != self:
            self.following.remove(user)

    def follower_count(self) -> int:
        """Return how many users follow this user."""
        return self.followers.count()

    def following_count(self) -> int:
        """Return how many users this user is following."""
        return self.following.count()


# ------------------------
# POST MODEL
# ------------------------
class Post(models.Model):
    """
    A post in the network.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Users who liked this post
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True,
    )

    # Helper methods

    def __str__(self) -> str:
        return (
            f"Post by {self.author.username} "
            f"at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )

    def like_count(self) -> int:
        """Return the number of likes for this post."""
        return self.liked_by.count()

    def is_liked_by(self, user) -> bool:
        """Return True if the given user has liked this post."""
        return self.liked_by.filter(id=user.id).exists()

    def toggle_like(self, user) -> None:
        """Toggle like/unlike for the given user."""
        if self.is_liked_by(user):
            self.liked_by.remove(user)
        else:
            self.liked_by.add(user)


