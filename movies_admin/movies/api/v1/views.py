from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView

from ...models import Movie


class BaseApi:
    """Base class for model Movie with reworked get_queryset logic."""
    model = Movie
    http_method_names = ['get']

    def get_queryset(self):
        """
        :return: Movie queryset filtered by pk from kwargs.
        """
        movies = Movie.objects.filter(**self.kwargs).annotate(
            actors=ArrayAgg('persons_as_movie__person__name',
                            distinct=True,
                            filter=Q(persons_as_movie__role='actor')),
            writers=ArrayAgg('persons_as_movie__person__name',
                             distinct=True,
                             filter=Q(persons_as_movie__role='writer')),
            directors=ArrayAgg('persons_as_movie__person__name',
                               distinct=True,
                               filter=Q(persons_as_movie__role='director'))).values(
            'id', 'title', 'description', 'creation_date', 'rating', 'type', 'actors', 'directors', 'writers'
        ).annotate(genres=ArrayAgg('genres__name', distinct=True))
        return movies


class MoviesListApi(BaseApi, BaseListView):
    """List of Movies."""
    paginate_by = 50

    def get_context_data(self, *, object_list=None, **kwargs):
        """Get the context for this view."""
        queryset = object_list if object_list is not None else self.get_queryset()
        page_size = self.get_paginate_by(queryset)
        if page_size:
            paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
            context = {
                'count': paginator.count,
                'total_pages': paginator.num_pages,
                'prev': page.number - 1,
                'next': page.number + 1,
                'result': list(queryset),
            }
        else:
            context = {
                'count': 0,
                'total_pages': 0,
                'prev': 0,
                'next': 0,
                'result': list(queryset),
            }
        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Return a json response.
        {
            'count': Total number of movies,
            'total_pages': Total number of pages,
            'prev': previous page,
            'next': next page,
            'result': list of Movie dictionaries
        }
        """
        return JsonResponse(context)


class MovieDetailApi(BaseApi, BaseDetailView):
    """Detail view for one Movie."""

    def render_to_response(self, context, **response_kwargs):
        """Return a Json response with fields dictionary of specific Movie."""
        return JsonResponse(context.get('object'))
