from django.test import TestCase, Client
from django.core.cache import cache

from ..models import Post, Group, User


class PostsURLTests(TestCase):
    """ Тестирование статуса страниц приложения posts."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
        )

    def setUp(self):
        """Создаём экземпляр клиента."""
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls__for_all_client(self):
        """Страницы для неавторизованных пользователей"""
        url_templates_names = {
            '/': 'posts/index.html',
            '/group/test_slug/': 'posts/group_list.html',
            f'/profile/{self.post.author}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for url, template in url_templates_names.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_urls_for_authorized_client(self):
        """Страницы для авторизованных пользователей"""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, 200)

    def test_urls_redicect_anonymous(self):
        """Страницы перенаправляют неавторизованного пользователя."""
        url_templates_names = {
            f'/posts/{self.post.id}/edit/': '/auth/login/?next=/posts/1/edit/',
            '/create/': '/auth/login/?next=/create/',
        }
        for url, template in url_templates_names.items():
            with self.subTest(url=url):
                response = self.guest_client.post(url, follow=True)
                self.assertRedirects(response, template)

    def test_url_edit_is_author(self):
        """Редактировать пост может только его автор"""
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_url_for_unexisting_page(self):
        """запрос к несуществующей странице возвращает ошибку 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/create/': 'posts/create.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/profile/{self.post.author}/': 'posts/profile.html',
            f'/posts/{self.post.id}/edit/': 'posts/create.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
