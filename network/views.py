import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import (
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Post, User


def index(request):
    return redirect("all_posts")


@login_required
def post_list(request, mode="all"):
    # Build base queryset depending on mode
    if mode == "my":
        posts_qs = Post.objects.filter(author=request.user)
    elif mode == "liked":
        posts_qs = request.user.liked_posts.all()
    elif mode == "feed":
        posts_qs = Post.objects.filter(author__in=request.user.following.all())
    else:  # "all"
        posts_qs = Post.objects.all()

    # Always order newest first
    posts_qs = posts_qs.order_by("-created_at")

    # Paginate: 10 posts per page
    paginator = Paginator(posts_qs, 10)
    page_number = request.GET.get("page")  # None → page 1
    page_obj = paginator.get_page(page_number)

    # Mark which posts are liked by the current user (just for this page)
    for p in page_obj:
        p.is_liked = p.is_liked_by(request.user)

    return render(
        request,
        "network/post_list.html",
        {
            "posts": page_obj,
            "mode": mode,
        },
    )


@login_required
def like_post(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    post = get_object_or_404(Post, pk=post_id)
    post.toggle_like(request.user)

    return JsonResponse(
        {
            "liked": post.is_liked_by(request.user),
            "like_count": post.like_count(),
        }
    )


@login_required
def edit_post(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    post = get_object_or_404(Post, pk=post_id)

    # Only the author may edit
    if post.author != request.user:
        return HttpResponseForbidden("You cannot edit this post.")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    new_content = (data.get("content") or "").strip()
    if not new_content:
        return JsonResponse({"error": "Content cannot be empty"}, status=400)

    post.content = new_content
    post.save()

    return JsonResponse(
        {
            "content": post.content,
            "updated_at": post.updated_at.strftime("%b. %d, %Y, %I:%M %p"),
        }
    )


@login_required
def new_post(request):
    if request.method == "POST":
        content = (request.POST.get("content") or "").strip()
        if content:
            Post.objects.create(author=request.user, content=content)
            return redirect("all_posts")

    return render(request, "network/compose_post.html")


def search(request):
    query = request.GET.get("q", "")
    users = []

    if query:
        users = User.objects.filter(username__icontains=query)

    return render(
        request,
        "network/search.html",
        {
            "users": users,
            "query": query,
        },
    )


@login_required
def user_page(request, user_id):
    profile_user = get_object_or_404(User, pk=user_id)
    is_following = request.user.follows(profile_user)

    # Handle Follow/Unfollow POST
    if request.method == "POST":
        if is_following:
            request.user.unfollow(profile_user)
        else:
            request.user.follow(profile_user)
        return redirect("user_page", user_id=user_id)

    # Posts by this user, newest first
    posts_qs = profile_user.posts.order_by("-created_at")

    # Paginate: 10 per page
    paginator = Paginator(posts_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Mark liked state for current user (for JS + template)
    for p in page_obj:
        p.is_liked = p.is_liked_by(request.user)

    return render(
        request,
        "network/user_page.html",
        {
            "profile_user": profile_user,
            "is_following": is_following,
            "followers_count": profile_user.follower_count(),
            "following_count": profile_user.following_count(),
            "posts": page_obj,
        },
    )



def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        return render(
            request,
            "network/login.html",
            {"message": "Invalid username and/or password."},
        )

    return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(
                request,
                "network/register.html",
                {"message": "Passwords must match."},
            )

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(
                request,
                "network/register.html",
                {"message": "Username already taken."},
            )

        login(request, user)
        return HttpResponseRedirect(reverse("index"))

    return render(request, "network/register.html")
