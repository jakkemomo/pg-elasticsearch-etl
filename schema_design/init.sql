-- create user jaqombo with encrypted password '12345';
-- alter user jaqombo with superuser;
-- create database movies owner jaqombo;
create schema if not exists content;
alter database movies set search_path to content;
create table if not exists content.movie (
              id uuid primary key,
              title varchar(255) not null,
              description text,
              creation_date date,
              rating float,
              certificate varchar(20),
              file_path varchar(100),
              type varchar(20) default 'movie' not null,
              created timestamptz default now(),
              modified timestamptz default now() );
create table if not exists content.person (
               id uuid primary key,
               name varchar(255) not null,
               birth_date date,
               created timestamptz default now(),
               modified timestamptz default now());
create table if not exists content.genre (
              id uuid primary key,
              name varchar(50) not null,
              description text,
              created timestamptz default now(),
              modified timestamptz default now());
create type role_type as enum ('director', 'writer', 'actor');
create table if not exists content.movie_genre_rel (
                        id uuid primary key,
                        movie_id uuid references content.movie on update cascade on delete cascade,
                        genre_id uuid references content.genre on update cascade on delete restrict,
                        created timestamptz default now(),
                        modified timestamptz default now());
create table if not exists content.movie_person_rel (
                              id uuid primary key,
                              movie_id uuid references content.movie on update cascade on delete cascade,
                              person_id uuid references content.person on update cascade on delete restrict,
                              role role_type,
                              created timestamptz default now(),
                              modified timestamptz default now());
create unique index if not exists movie_genre on content.movie_genre_rel (movie_id, genre_id);
create unique index if not exists movie_person_rel_index on content.movie_person_rel (movie_id, person_id, role);
