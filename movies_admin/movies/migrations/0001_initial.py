# Generated by Django 3.1 on 2020-11-20 10:22

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50, verbose_name='название')),
                ('description', models.TextField(blank=True, null=True, verbose_name='описание')),
            ],
            options={
                'verbose_name': 'жанр',
                'verbose_name_plural': 'жанры',
                'db_table': 'content"."genre',
            },
        ),
        migrations.CreateModel(
            name='Movie',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255, verbose_name='название')),
                ('description', models.TextField(blank=True, null=True, verbose_name='описание')),
                ('creation_date', models.DateField(blank=True, null=True, verbose_name='дата создания фильма')),
                ('rating', models.FloatField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='рейтинг')),
                ('certificate', models.CharField(choices=[('G', 'G'), ('PG', 'PG'), ('PG_13', 'PG-13'), ('R', 'R'), ('NC_17', 'NC-17'), ('', '')], default='', max_length=20, verbose_name='сертификат')),
                ('file_path', models.FileField(blank=True, null=True, upload_to='movies/', verbose_name='файл')),
                ('type', models.CharField(choices=[('movie', 'фильм'), ('tv_series', 'сериал')], default='movie', max_length=20, verbose_name='тип')),
            ],
            options={
                'verbose_name': 'фильм',
                'verbose_name_plural': 'фильмы',
                'db_table': 'content"."movie',
            },
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='название')),
                ('birth_date', models.DateField(blank=True, null=True, verbose_name='дата рождения')),
            ],
            options={
                'verbose_name': 'действующее лицо',
                'verbose_name_plural': 'действующие лица',
                'db_table': 'content"."person',
            },
        ),
        migrations.CreateModel(
            name='MoviePerson',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('actor', 'актёр'), ('writer', 'сценарист'), ('director', 'режиссёр')], max_length=20, verbose_name='роль')),
                ('movie', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='persons_as_movie', to='movies.movie', verbose_name='фильм')),
                ('person', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='persons_as_person', to='movies.person', verbose_name='действующее лицо')),
            ],
            options={
                'db_table': 'content"."movie_person_rel',
            },
        ),
        migrations.CreateModel(
            name='MovieGenre',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('genre', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='genres_as_genre', to='movies.genre', verbose_name='жанр')),
                ('movie', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='genre_as_movie', to='movies.movie', verbose_name='фильм')),
            ],
            options={
                'db_table': 'content"."movie_genre_rel',
            },
        ),
    ]
