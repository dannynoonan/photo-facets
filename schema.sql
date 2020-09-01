pg_dump -t lockdownsf_user --schema-only lockdownsf
pg_dump -t lockdownsf_tag --schema-only lockdownsf
pg_dump -t lockdownsf_album --schema-only lockdownsf
pg_dump -t lockdownsf_photo --schema-only lockdownsf


--
-- PostgreSQL database dump
--

-- Dumped from database version 12.3
-- Dumped by pg_dump version 12.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;



--
-- Name: lockdownsf_user; Type: TABLE; Schema: public
--

CREATE TABLE public.lockdownsf_user (
    id integer NOT NULL,
    email character varying(512) NOT NULL,
    dt_inserted timestamp with time zone NOT NULL,
    dt_last_login timestamp with time zone NOT NULL,
    status character varying(64) NOT NULL
);

CREATE SEQUENCE public.lockdownsf_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.lockdownsf_user_id_seq OWNED BY public.lockdownsf_user.id;

ALTER TABLE ONLY public.lockdownsf_user ALTER COLUMN id SET DEFAULT nextval('public.lockdownsf_user_id_seq'::regclass);

ALTER TABLE ONLY public.lockdownsf_user
    ADD CONSTRAINT lockdownsf_user_email_5f008051_uniq UNIQUE (email);

ALTER TABLE ONLY public.lockdownsf_user
    ADD CONSTRAINT lockdownsf_user_pkey PRIMARY KEY (id);

CREATE INDEX lockdownsf_user_email_5f008051_like ON public.lockdownsf_user USING btree (email varchar_pattern_ops);

CREATE INDEX lockdownsf_user_status_788d36aa ON public.lockdownsf_user USING btree (status);

CREATE INDEX lockdownsf_user_status_788d36aa_like ON public.lockdownsf_user USING btree (status varchar_pattern_ops);


--
-- Name: lockdownsf_tag; Type: TABLE; Schema: public
--

CREATE TABLE public.lockdownsf_tag (
    id integer NOT NULL,
    name character varying(256) NOT NULL,
    dt_inserted timestamp with time zone NOT NULL,
    status character varying(64) NOT NULL,
    owner_id integer NOT NULL
);

CREATE SEQUENCE public.lockdownsf_tag_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.lockdownsf_tag_id_seq OWNED BY public.lockdownsf_tag.id;

ALTER TABLE ONLY public.lockdownsf_tag ALTER COLUMN id SET DEFAULT nextval('public.lockdownsf_tag_id_seq'::regclass);

ALTER TABLE ONLY public.lockdownsf_tag
    ADD CONSTRAINT lockdownsf_tag_name_owner_id_212acceb_uniq UNIQUE (name, owner_id);

ALTER TABLE ONLY public.lockdownsf_tag
    ADD CONSTRAINT lockdownsf_tag_pkey PRIMARY KEY (id);

CREATE INDEX lockdownsf_tag_name_60448326 ON public.lockdownsf_tag USING btree (name);

CREATE INDEX lockdownsf_tag_name_60448326_like ON public.lockdownsf_tag USING btree (name varchar_pattern_ops);

CREATE INDEX lockdownsf_tag_owner_id_2baa417b ON public.lockdownsf_tag USING btree (owner_id);

CREATE INDEX lockdownsf_tag_status_79822f3a ON public.lockdownsf_tag USING btree (status);

CREATE INDEX lockdownsf_tag_status_79822f3a_like ON public.lockdownsf_tag USING btree (status varchar_pattern_ops);

ALTER TABLE ONLY public.lockdownsf_tag
    ADD CONSTRAINT lockdownsf_tag_owner_id_2baa417b_fk_lockdownsf_user_id FOREIGN KEY (owner_id) REFERENCES public.lockdownsf_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: lockdownsf_album; Type: TABLE; Schema: public
--

CREATE TABLE public.lockdownsf_album (
    id integer NOT NULL,
    external_id character varying(500),
    name character varying(500) NOT NULL,
    center_latitude numeric(9,6),
    center_longitude numeric(9,6),
    dt_inserted timestamp with time zone NOT NULL,
    dt_updated timestamp with time zone NOT NULL,
    status character varying(64) NOT NULL,
    map_zoom_level integer NOT NULL,
    owner_id integer NOT NULL,
    photos_having_gps integer NOT NULL
);

CREATE SEQUENCE public.lockdownsf_album_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.lockdownsf_album_id_seq OWNED BY public.lockdownsf_album.id;

ALTER TABLE ONLY public.lockdownsf_album ALTER COLUMN id SET DEFAULT nextval('public.lockdownsf_album_id_seq'::regclass);

ALTER TABLE ONLY public.lockdownsf_album
    ADD CONSTRAINT lockdownsf_album_external_id_9dc6f017_uniq UNIQUE (external_id);

ALTER TABLE ONLY public.lockdownsf_album
    ADD CONSTRAINT lockdownsf_album_pkey PRIMARY KEY (id);

CREATE INDEX lockdownsf_album_external_id_9dc6f017_like ON public.lockdownsf_album USING btree (external_id varchar_pattern_ops);

CREATE INDEX lockdownsf_album_owner_id_d37e660e ON public.lockdownsf_album USING btree (owner_id);

CREATE INDEX lockdownsf_album_status_c78fd288 ON public.lockdownsf_album USING btree (status);

CREATE INDEX lockdownsf_album_status_c78fd288_like ON public.lockdownsf_album USING btree (status varchar_pattern_ops);

ALTER TABLE ONLY public.lockdownsf_album
    ADD CONSTRAINT lockdownsf_album_owner_id_d37e660e_fk_lockdownsf_user_id FOREIGN KEY (owner_id) REFERENCES public.lockdownsf_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: lockdownsf_photo; Type: TABLE; Schema: public
--

CREATE TABLE public.lockdownsf_photo (
    id integer NOT NULL,
    external_id character varying(500),
    file_name character varying(256) NOT NULL,
    mime_type character varying(128) NOT NULL,
    description character varying(500),
    dt_taken timestamp with time zone,
    dt_inserted timestamp with time zone NOT NULL,
    dt_updated timestamp with time zone NOT NULL,
    latitude numeric(9,6),
    longitude numeric(9,6),
    extracted_text_display character varying(16000),
    status character varying(64) NOT NULL,
    album_id integer,
    owner_id integer NOT NULL,
    extracted_text_search character varying(16000)
);

CREATE SEQUENCE public.lockdownsf_photo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.lockdownsf_photo_id_seq OWNED BY public.lockdownsf_photo.id;

ALTER TABLE ONLY public.lockdownsf_photo ALTER COLUMN id SET DEFAULT nextval('public.lockdownsf_photo_id_seq'::regclass);

ALTER TABLE ONLY public.lockdownsf_photo
    ADD CONSTRAINT lockdownsf_photo_external_id_52e9f522_uniq UNIQUE (external_id);

ALTER TABLE ONLY public.lockdownsf_photo
    ADD CONSTRAINT lockdownsf_photo_pkey PRIMARY KEY (id);

CREATE INDEX lockdownsf_photo_album_id_54476c79 ON public.lockdownsf_photo USING btree (album_id);

CREATE INDEX lockdownsf_photo_external_id_52e9f522_like ON public.lockdownsf_photo USING btree (external_id varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_file_name_0eb06ffe ON public.lockdownsf_photo USING btree (file_name);

CREATE INDEX lockdownsf_photo_file_name_0eb06ffe_like ON public.lockdownsf_photo USING btree (file_name varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_mime_type_d64100ff ON public.lockdownsf_photo USING btree (mime_type);

CREATE INDEX lockdownsf_photo_mime_type_d64100ff_like ON public.lockdownsf_photo USING btree (mime_type varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_owner_id_ebba5d1a ON public.lockdownsf_photo USING btree (owner_id);

CREATE INDEX lockdownsf_photo_status_28e6cf6d ON public.lockdownsf_photo USING btree (status);

CREATE INDEX lockdownsf_photo_status_28e6cf6d_like ON public.lockdownsf_photo USING btree (status varchar_pattern_ops);

ALTER TABLE ONLY public.lockdownsf_photo
    ADD CONSTRAINT lockdownsf_photo_album_id_54476c79_fk_lockdownsf_album_id FOREIGN KEY (album_id) REFERENCES public.lockdownsf_album(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY public.lockdownsf_photo
    ADD CONSTRAINT lockdownsf_photo_owner_id_ebba5d1a_fk_lockdownsf_user_id FOREIGN KEY (owner_id) REFERENCES public.lockdownsf_user(id) DEFERRABLE INITIALLY DEFERRED;
