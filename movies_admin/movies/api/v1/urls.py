from django.urls import path

from . import views

urlpatterns = [
    path("movies/", views.MoviesListApi.as_view()),
    path("movies/<uuid:pk>/", views.MovieDetailApi.as_view()),
]
