from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=('Lorem ipsum dolor sit amet, consectetur adipiscing elit.'
                  'Maecenas luctus turpis dui, non hendrerit'
                  'libero elementum malesuada.')
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        group = PostModelTest.group
        post = PostModelTest.post
        self.assertEqual(group.title, str(group))
        field_verboses = {
            post.text[:15]: str(post),
            group.title: str(group),
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)
