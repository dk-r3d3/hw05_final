from .models import Post, Comment
from django.forms import ModelForm, Textarea, Select
from django.core.exceptions import ValidationError


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['text', 'group', 'image']
        widgets = {
            "text": Textarea(attrs={
                'class': 'form-control',
                'cols': '40',
                'rows': '10'
            }),
            "group": Select(attrs={
                'class': 'form-control'
            })
        }

    def clean_text(self):
        text = self.cleaned_data['text']
        if len(text) < 10:
            raise ValidationError(
                'Текст поста слишком короткий'
            )
        return text


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)

    def clean_text(self):
        text = self.cleaned_data['text']
        if len(text) < 10:
            raise ValidationError(
                'Текст комментария слишком короткий'
            )
        return text
