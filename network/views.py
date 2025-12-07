from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Post


def index(request):
    return render(request, "network/index.html")


def post_list(request, mode="all"):
    if mode == "my":
        posts = Post.objects.filter(author=request.user).order_by('-created_at')
    elif mode == "liked":
        posts = request.user.liked_posts.all().order_by('-created_at')
    elif mode == "feed":
        posts = Post.objects.filter(author__in=request.user.following.all()).order_by('-created_at')
    else:  # "all"
        posts = Post.objects.all()

    for p in posts:
        p.is_liked = p.is_liked_by(request.user)
    return render(request, "network/post_list.html", {
        "posts": posts,
        "mode": mode
    })


@login_required
def like_post(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    post = get_object_or_404(Post, pk=post_id)
    post.toggle_like(request.user)

    return JsonResponse({
        "liked": post.is_liked_by(request.user),
        "like_count": post.like_count(),
    })


def new_post(request):
    if request.method == "POST":
        content = request.POST.get("content")
        if content.strip():
            Post.objects.create(author=request.user, content=content)
            return redirect("all_posts")
    return render(request, "network/compose_post.html")


def search(request):
    query = request.GET.get("q", "")
    users = []

    if query:
        users = User.objects.filter(username__icontains=query)

    return render(request, "network/search.html", {
        "users": users,
        "query": query
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import User


@login_required
def user_page(request, user_id):
    profile_user = get_object_or_404(User, pk=user_id)
    is_following = request.user.follows(profile_user)

    # Handle Follow/Unfollow
    if request.method == "POST":
        if is_following:
            request.user.unfollow(profile_user)
        else:
            request.user.follow(profile_user)
        return redirect("user_page", user_id=user_id)

    return render(request, "network/user_page.html", {
        "profile_user": profile_user,
        "is_following": is_following,
        "followers_count": profile_user.follower_count(),
        "following_count": profile_user.following_count(),
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")
