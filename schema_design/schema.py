import psycopg2
from os import environ as env
from dotenv import load_dotenv

load_dotenv()

db_host = env['db_host']
db_port = env['db_port']
db_name = env['db_name']
db_user = env['db_user']
db_password = env['db_password']

CREATE_SCHEMA = '''create schema if not exists content;'''
CHANGE_SEARCH_PATH = f'''alter database {db_name} set search_path to content;'''

MOVIE_TABLE = '''create table if not exists content.movie (
              id uuid primary key,
              title varchar(255) not null,
              description text,
              creation_date date,
              rating float,
              certificate varchar(20),
              file_path varchar(100),
              type varchar(20) default 'movie' not null, 
              created timestamptz default now(),
              modified timestamptz default now() );'''

PERSON_TABLE = '''create table if not exists content.person (
               id uuid primary key,
               name varchar(255) not null,
               birth_date date,
               created timestamptz default now(),
               modified timestamptz default now());'''

GENRE_TABLE = '''create table if not exists content.genre (
              id uuid primary key,
              name varchar(50) not null,
              description text,
              created timestamptz default now(),
              modified timestamptz default now());'''

MOVIE_GENRE_REL_TABLE = '''create table if not exists content.movie_genre_rel (
                        id uuid primary key,
                        movie_id uuid references content.movie on update cascade on delete cascade,
                        genre_id uuid references content.genre on update cascade on delete restrict,
                        created timestamptz default now(),
                        modified timestamptz default now());'''

ROLE_TYPE = '''create type role_type as enum ('director', 'writer', 'actor');'''

MOVIE_PERSON_REL_TABLE = '''create table if not exists content.movie_person_rel (
                              id uuid primary key,
                              movie_id uuid references content.movie on update cascade on delete cascade,
                              person_id uuid references content.person on update cascade on delete restrict,
                              role role_type,
                              created timestamptz default now(),
                              modified timestamptz default now());'''

MOVIE_GENRE_INDEX = '''create unique index if not exists movie_genre on content.movie_genre_rel (movie_id, genre_id)'''

MOVIE_PERSON_REL_INDEX = '''create unique index if not exists movie_person_rel_index on movie_person_rel
                               (movie_id,
                                person_id,
                                role)'''

connection = psycopg2.connect(host=db_host,
                              port=db_port,
                              database=db_name,
                              user=db_user,
                              password=db_password,
                              options='-c search_path=content',
                              )

with connection:
    with connection.cursor() as _cr:
        _cr.execute(CREATE_SCHEMA)
        _cr.execute(CHANGE_SEARCH_PATH)
        _cr.execute(MOVIE_TABLE)
        _cr.execute(PERSON_TABLE)
        _cr.execute(GENRE_TABLE)
        _cr.execute(ROLE_TYPE)
        _cr.execute(MOVIE_PERSON_REL_TABLE)
        _cr.execute(MOVIE_GENRE_REL_TABLE)
        _cr.execute(MOVIE_GENRE_INDEX)
        _cr.execute(MOVIE_PERSON_REL_INDEX)

connection.close()
