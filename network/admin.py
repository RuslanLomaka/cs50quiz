from django.contrib import admin

from network.models import Post, User


# Register your models here.

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    pass

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass