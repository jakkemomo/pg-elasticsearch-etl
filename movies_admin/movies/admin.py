from django.contrib import admin

from .models import Genre, Movie, MovieGenre, MoviePerson, Person


class MovieGenreInline(admin.TabularInline):
    """
    Связующая модель между фильмами и жанрами.
    """

    model = MovieGenre
    extra = 0


class MoviePersonInline(admin.TabularInline):
    """
    Связующая модель между фильмами, действующими лицами и ролями.
    """

    model = MoviePerson
    extra = 0


# todo: пересмотреть подход к inlines, потому что относитетельно долго грузит
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """
    Панель администрирования фильмов.
    """

    list_display = ["title", "rating"]
    fields = [
        "title",
        "description",
        "type",
        "creation_date",
        "certificate",
        "file_path",
        "rating",
    ]
    list_filter = ("type",)
    search_fields = ("title", "description", "id", "rating")

    inlines = [MovieGenreInline, MoviePersonInline]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """
    Панель администрирования жанров.
    """

    list_display = ["name", "description"]
    fields = ["name", "description"]
    search_fields = ["name"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """
    Панель администрирования действующих лиц.
    """

    list_display = ["name"]
    fields = ["name", "birth_date"]
    search_fields = ["name"]

    inlines = [MoviePersonInline]
