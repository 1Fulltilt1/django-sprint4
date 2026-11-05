from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, PostForm, UserEditForm
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


def annotate_posts(queryset):
    """Добавляет связанные объекты и число комментариев к постам."""
    return queryset.select_related(
        'author', 'location', 'category'
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def filter_published(queryset):
    """Опубликованные посты с наступившей датой из опубликованных категорий."""
    return queryset.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    )


def paginate(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get('page'))


def index(request):
    """Главная страница: лента публикаций."""
    posts = annotate_posts(filter_published(Post.objects.all()))
    context = {'page_obj': paginate(request, posts)}
    return render(request, 'blog/index.html', context)


def category_posts(request, category_slug):
    """Страница категории."""
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    posts = annotate_posts(filter_published(category.posts.all()))
    context = {'category': category, 'page_obj': paginate(request, posts)}
    return render(request, 'blog/category.html', context)


def post_detail(request, post_id):
    """Страница отдельной публикации; автор видит и неопубликованные."""
    post = get_object_or_404(
        Post.objects.select_related('author', 'location', 'category'),
        pk=post_id,
    )
    if post.author != request.user:
        post = get_object_or_404(filter_published(Post.objects), pk=post_id)
    context = {
        'post': post,
        'form': CommentForm(),
        'comments': post.comments.select_related('author'),
    }
    return render(request, 'blog/detail.html', context)


def profile(request, username):
    """Страница пользователя с его публикациями."""
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    if author != request.user:
        posts = filter_published(posts)
    context = {
        'profile': author,
        'page_obj': paginate(request, annotate_posts(posts)),
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    form = UserEditForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', request.user.username)
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(filter_published(Post.objects), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    context = {'form': form, 'comment': comment}
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
