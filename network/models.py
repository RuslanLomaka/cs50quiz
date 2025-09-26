# Import Django’s built-in user base class
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


# ------------------------
# USER MODEL
# ------------------------
class User(AbstractUser):
    # A self-referential many-to-many relationship:
    # - Each user can follow many other users
    # - Each user can also be followed by many users
    # - symmetrical=False means: if A follows B, B does NOT automatically follow A
    # - related_name='following' lets us query "who this user follows"
    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        blank=True   # allow a user to exist without followers
    )

    # Short biography for profile page
    bio = models.TextField(max_length=500, blank=True)

    # Optional profile image uploaded by the user
    # - upload_to defines the folder inside MEDIA_ROOT
    # - blank=True and null=True means this field is not required
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)


    # ------------------------
    # HELPER METHODS
    # ------------------------

    def follows(self, user):
        """
        Return True if the current user follows another given user.
        Prevents self-follow.
        """
        if user == self:
            return False
        return self.following.filter(id=user.id).exists()

    def follow(self, user):
        """
        Make the current user follow another user.
        Self-follow is blocked.
        """
        if user != self:
            self.following.add(user)

    def unfollow(self, user):
        """
        Make the current user unfollow another user.
        Self-unfollow is ignored.
        """
        if user != self:
            self.following.remove(user)

    def follower_count(self):
        """
        Return how many users are following THIS user.
        """
        return self.followers.count()

    def following_count(self):
        """
        Return how many users THIS user is following.
        """
        return self.following.count()


# ------------------------
# POST MODEL
# ------------------------
class Post(models.Model):
    # The user who created the post
    # - CASCADE means: if user is deleted, their posts are also deleted
    # - related_name='posts' lets us do user.posts.all()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )

    # The text content of the post
    content = models.TextField()

    # Timestamp when post is first created
    created_at = models.DateTimeField(auto_now_add=True)

    # Timestamp when post is last updated
    updated_at = models.DateTimeField(auto_now=True)

    # Many-to-many relationship for likes:
    # - A post can be liked by many users
    # - A user can like many posts
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_posts',
        blank=True   # a post can start with zero likes
    )


    # ------------------------
    # HELPER METHODS
    # ------------------------

    def __str__(self):
        """
        String representation of a post.
        Example: "Post by alice at 2025-09-25 12:30"
        """
        return f"Post by {self.author.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def like_count(self):
        """
        Return number of likes for this post.
        Using .count() ensures data is always accurate.
        """
        return self.liked_by.count()

    def is_liked_by(self, user):
        """
        Return True if the given user has liked this post.
        """
        return self.liked_by.filter(id=user.id).exists()

    def toggle_like(self, user):
        """
        Toggle like/unlike for a given user.
        If user already liked → remove like.
        If not → add like.
        """
        if self.is_liked_by(user):
            self.liked_by.remove(user)
        else:
            self.liked_by.add(user)


# ------------------------
# COMMENT MODEL
# ------------------------
class Comment(models.Model):
    # The post this comment belongs to
    # - CASCADE means: if post is deleted, all comments are deleted too
    # - related_name='comments' lets us do post.comments.all()
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    # The author (user) of this comment
    # - CASCADE means: if user is deleted, their comments are also deleted
    # - related_name='comments' lets us do user.comments.all()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    # The text content of the comment
    content = models.TextField()

    # Timestamp when comment was created
    created_at = models.DateTimeField(auto_now_add=True)

    # Timestamp when comment was last updated
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        # Default ordering: newest comments first
        ordering = ['-created_at']


    def __str__(self):
        """
        String representation of a comment.
        Example: "Comment by alice on post 42"
        """
        return f'Comment by {self.author.username} on {self.post.id}'
