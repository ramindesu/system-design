from django.conf import settings
from django.db import models

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="following_edges")
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="follower_edges")
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["follower", "author"], name="unique_follow")]

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["author", "-id"])]

class FeedEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["user","post"],name="unique_feed_item")]
