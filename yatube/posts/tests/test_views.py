import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from ..forms import PostForm
from ..models import Post, Group, User, Follow
from ..views import PAGE_COUNT

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
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
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Текст',
            image=uploaded,
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.user,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаём неавторизованный клиент
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.unfollower_client = Client()
        self.follower_client = Client()
        self.authorized_client.force_login(self.user)
        self.unfollower_user = User.objects.create_user(username='noname')
        self.follower_user = User.objects.create_user(username='follower')
        self.author = User.objects.create_user(username='following')

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}
            ): 'posts/create.html',
            reverse('posts:post_create'): 'posts/create.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_correct_context(self):
        """Шаблон home сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        object = response.context['page_obj'][0]
        self.assertEqual(object, self.post)

    def test_group_list_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertIn('group', response.context)
        object = response.context['group']
        text = response.context['page_obj'][0].text
        group = response.context['page_obj'][0].group.title
        self.assertEqual(object, self.group)
        self.assertEqual(text, self.post.text)
        self.assertEqual(group, self.group.title)

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username})
        )
        object = response.context['author']
        self.assertEqual(object, self.post.author)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
        )
        post = response.context['post']
        author = self.post.author
        group = self.group
        text = self.post.text
        self.assertEqual(author, post.author)
        self.assertEqual(text, post.text)
        self.assertEqual(group, post.group)

    def test_create_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse('posts:post_create')))
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertIsInstance(form, PostForm)

    def test_post_edit_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}))
        object = response.context['form'].initial['text']
        self.assertEqual(object, self.post.text)

    def test_display_img_post_page(self):
        """При выводе поста с картинкой изображение
        передаётся в словаре context"""
        urls = (
            reverse('posts:profile', args=(self.user,)),
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        )
        for url in urls:
            with self.subTest(url=url):
                responce = self.client.get(url)
                self.assertTrue(responce.context['page_obj'][0].image)
                self.assertEqual(
                    responce.context['page_obj'][0].image, self.post.image
                )
        response_detail = self.guest_client.get(
            reverse('posts:post_detail', args=(self.post.pk,)),
        )
        self.assertTrue(response_detail.context['post'].image)
        self.assertEqual(
            response_detail.context['post'].image, self.post.image
        )

    def test_cache_index(self):
        """Тестирование кеша"""
        cache.clear()
        post = Post.objects.get(pk=1)
        response_1 = self.authorized_client.get(reverse('posts:index'))
        post.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)

    def test_auth_user_can_follow(self):
        """Авторизованный пользователь можнот подписываться на других."""
        self.unfollower_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author}))
        self.assertFalse(Follow.objects.filter(
            user=self.unfollower_user,
            author=self.author,
        ).exists())

    def test_auth_user_can_unfollow(self):
        """Авторизованный пользователь может удалять других из подписок."""
        self.unfollower_client.get(
            reverse(
                'posts:profile_unfollow', kwargs={'username': self.author})
        )
        self.assertFalse(Follow.objects.filter(
            user=self.follower_user,
            author=self.author,
        ).exists())

    def test_new_post_follower(self):
        """Новая запись появилась у подписчика."""
        follow_count = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.author}
        ))
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_new_post_unfollower(self):
        """Новая запись не появилась у неподписанного пользователя."""
        follow_count = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author}
        ))
        self.assertEqual(Follow.objects.count(), follow_count)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        for i in range(1, 14):
            cls.post = Post.objects.create(
                author=cls.user,
                text=f'{i} Тестовый пост',
                group=cls.group,
            )

    def setUp(self):
        cache.clear()

    def test_index_first_page(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), PAGE_COUNT)

    def test_index_second_page(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        second_page = Post.objects.count() % PAGE_COUNT
        self.assertEqual(len(response.context['page_obj']), second_page)

    def test_group_list_first_page(self):
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(len(response.context['page_obj']), PAGE_COUNT)

    def test_group_list_second_page(self):
        response = self.client.get(reverse(
            'posts:group_list', kwargs={'slug': 'test-slug'}) + '?page=2')
        second_page = Post.objects.count() % PAGE_COUNT
        self.assertEqual(len(response.context['page_obj']), second_page)

    def test_profile_first_page(self):
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(len(response.context['page_obj']), PAGE_COUNT)

    def test_profile_second_page(self):
        response = self.client.get(reverse(
            'posts:profile', kwargs={'username': self.user.username}
        ) + '?page=2')
        second_page = Post.objects.count() % PAGE_COUNT
        self.assertEqual(len(response.context['page_obj']), second_page)
