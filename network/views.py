from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import User, Post


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

    return render(request, "network/post_list.html", {
        "posts": posts,
        "mode": mode
    })

def new_post(request):
    if request.method == "POST":
        content = request.POST.get("content")
        if content.strip():
            Post.objects.create(author=request.user, content=content)
            return redirect("all_posts")
    return render(request, "network/compose_post.html")


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
