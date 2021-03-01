import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

SCHEMA = settings.CONTENT_SCHEMA

NULL_BLANK = {"null": True, "blank": True}

NULL_BLANK_FALSE = {"null": False, "blank": False}


class CertificateType(models.TextChoices):
    """
    Модель сертификатов фильмов.
    """

    general = "G", _("G")
    pg = "PG", _("PG")
    pg_13 = "PG_13", _("PG-13")
    R = "R", _("R")
    nc_17 = "NC_17", _("NC-17")
    empty = "", _("")


class MovieType(models.TextChoices):
    """
    Модель типов фильмов.
    """

    movie = "movie", _("фильм")
    tv_series = "tv_series", _("сериал")


class RoleType(models.TextChoices):
    """
    Модель типов фильмов.
    """

    actor = "actor", _("актёр")
    writer = "writer", _("сценарист")
    director = "director", _("режиссёр")


class Movie(TimeStampedModel):
    """
    Модель фильмов.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_("название"), max_length=255)
    description = models.TextField(_("описание"), **NULL_BLANK)
    creation_date = models.DateField(_("дата создания фильма"), **NULL_BLANK)
    rating = models.FloatField(
        _("рейтинг"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        **NULL_BLANK,
    )
    certificate = models.CharField(
        _("сертификат"),
        max_length=20,
        choices=CertificateType.choices,
        default=CertificateType.empty,
        **NULL_BLANK_FALSE,
    )
    file_path = models.FileField(_("файл"), upload_to="movies/", **NULL_BLANK)
    type = models.CharField(
        _("тип"),
        max_length=20,
        choices=MovieType.choices,
        default=MovieType.movie,
        **NULL_BLANK_FALSE,
    )
    persons = models.ManyToManyField(
        "Person", through="MoviePerson", through_fields=("movie", "person")
    )
    genres = models.ManyToManyField(
        "Genre", through="MovieGenre", through_fields=("movie", "genre")
    )

    class Meta:
        verbose_name = _("фильм")
        verbose_name_plural = _("фильмы")
        db_table = f'{SCHEMA}"."movie'

    def __str__(self):
        return self.title


class Genre(TimeStampedModel):
    """
    Модель жанров фильмов.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("название"), max_length=50, **NULL_BLANK_FALSE)
    description = models.TextField(_("описание"), **NULL_BLANK)

    class Meta:
        verbose_name = _("жанр")
        verbose_name_plural = _("жанры")
        db_table = f'{SCHEMA}"."genre'

    def __str__(self):
        return self.name


class MovieGenre(TimeStampedModel):
    """
    Модель связи жанров и фильмов.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    movie = models.ForeignKey(
        Movie,
        verbose_name=_("фильм"),
        related_name="genre_as_movie",
        on_delete=models.CASCADE,
        **NULL_BLANK,
    )
    genre = models.ForeignKey(
        Genre,
        verbose_name=_("жанр"),
        related_name="genres_as_genre",
        on_delete=models.RESTRICT,
        **NULL_BLANK,
    )

    class Meta:
        db_table = f'{SCHEMA}"."movie_genre_rel'


class Person(TimeStampedModel):
    """
    Модель действующих лиц.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("название"), max_length=255, **NULL_BLANK_FALSE)
    birth_date = models.DateField(_("дата рождения"), **NULL_BLANK)

    class Meta:
        verbose_name = _("действующее лицо")
        verbose_name_plural = _("действующие лица")
        db_table = f'{SCHEMA}"."person'

    def __str__(self):
        return self.name


class MoviePerson(TimeStampedModel):
    """
    Связующая модель между фильмами, действующими лицами и ролями.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    movie = models.ForeignKey(
        Movie,
        verbose_name=_("фильм"),
        related_name="persons_as_movie",
        on_delete=models.CASCADE,
        **NULL_BLANK,
    )
    person = models.ForeignKey(
        Person,
        verbose_name=_("действующее лицо"),
        related_name="persons_as_person",
        on_delete=models.RESTRICT,
        **NULL_BLANK,
    )
    role = models.CharField(
        _("роль"), max_length=20, choices=RoleType.choices, **NULL_BLANK_FALSE
    )

    class Meta:
        db_table = f'{SCHEMA}"."movie_person_rel'
