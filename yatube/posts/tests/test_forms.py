import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Post, Group, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='UserName')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовый текст',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый заголовок',
            image=uploaded,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый коммент'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_form_create(self):
        """Валидная форма создает пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': self.post.image,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        current_post = Post.objects.latest('pub_date')
        self.assertEqual(
            current_post.text, form_data['text']
        )
        self.assertEqual(
            current_post.group, self.group
        )
        self.assertEqual(
            current_post.author, self.user
        )
        self.assertTrue(
            Post.objects.filter(
                group=form_data['group'],
                text=form_data['text'],
                image=form_data['image'],
            ).exists()
        )

    def test_post_edit(self):
        """При отправке валидной формы пост редактируется."""
        text_edit = 'Отредактированный текст'
        form_data = {
            'text': text_edit,
            'group': self.group.id,
        }
        response_1 = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response_1, reverse(
            'posts:post_detail', kwargs={
                'post_id': self.post.id
            }),
        )

        current_post = Post.objects.latest('pub_date')
        self.assertEqual(
            current_post.text, form_data['text']
        )
        self.assertEqual(
            current_post.group, self.group
        )
        self.assertEqual(
            current_post.author, self.user
        )

    def test_guest_can_not_create_new_post(self):
        """Неавторизованный пользователь не может создать пост"""
        posts_count = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'),
            follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertEqual(posts_count, Post.objects.count())

    def test_add_comment_only_authorized_user(self):
        """Добавить комментарий может только авторизованный пользователь"""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый коммент',
            'post': self.post,
            'author': self.user,
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        """
        Получили комментарий из базы и проверили что там верно
        заполнены текст, автор и пост
        """
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
                post=form_data['post'],
                author=form_data['author'],
            ).exists()
        )
