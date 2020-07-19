pg_dump -t lockdownsf_neighborhood --schema-only lockdownsf
pg_dump -t lockdownsf_photo --schema-only lockdownsf



CREATE TABLE lockdownsf_neighborhood (
    id integer NOT NULL,
    slug character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    center_latitude numeric(9,6),
    center_longitude numeric(9,6),
    dt_inserted timestamp with time zone NOT NULL,
    dt_updated timestamp with time zone NOT NULL
);

ALTER TABLE lockdownsf_neighborhood OWNER TO eocdsbtlkjjepq;

CREATE SEQUENCE lockdownsf_neighborhood_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE lockdownsf_neighborhood_id_seq OWNER TO eocdsbtlkjjepq;

ALTER SEQUENCE lockdownsf_neighborhood_id_seq OWNED BY lockdownsf_neighborhood.id;

ALTER TABLE ONLY lockdownsf_neighborhood ALTER COLUMN id SET DEFAULT nextval('lockdownsf_neighborhood_id_seq'::regclass);

ALTER TABLE ONLY lockdownsf_neighborhood
    ADD CONSTRAINT lockdownsf_neighborhood_pkey PRIMARY KEY (id);

ALTER TABLE ONLY lockdownsf_neighborhood
    ADD CONSTRAINT lockdownsf_neighborhood_slug_key UNIQUE (slug);

CREATE INDEX lockdownsf_neighborhood_slug_72b3380e_like ON lockdownsf_neighborhood USING btree (slug varchar_pattern_ops);

CREATE TABLE lockdownsf_photo (
    uuid character varying(36) NOT NULL,
    source_file_name character varying(64) NOT NULL,
    file_format character varying(8) NOT NULL,
    dt_taken timestamp with time zone,
    dt_inserted timestamp with time zone NOT NULL,
    dt_updated timestamp with time zone NOT NULL,
    width_pixels integer NOT NULL,
    height_pixels integer NOT NULL,
    aspect_format character varying(16) NOT NULL,
    latitude numeric(9,6),
    longitude numeric(9,6),
    scene_type character varying(32) NOT NULL,
    business_type character varying(32),
    other_labels character varying(128),
    neighborhood_id integer NOT NULL,
    extracted_text_formatted character varying(4096),
    extracted_text_raw character varying(4096)
);


ALTER TABLE lockdownsf_photo OWNER TO eocdsbtlkjjepq;

ALTER TABLE ONLY lockdownsf_photo
    ADD CONSTRAINT lockdownsf_photo_pkey PRIMARY KEY (uuid);

CREATE INDEX lockdownsf_photo_aspect_format_e48e53a4 ON lockdownsf_photo USING btree (aspect_format);

CREATE INDEX lockdownsf_photo_aspect_format_e48e53a4_like ON lockdownsf_photo USING btree (aspect_format varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_business_type_c755152f ON lockdownsf_photo USING btree (business_type);

CREATE INDEX lockdownsf_photo_business_type_c755152f_like ON lockdownsf_photo USING btree (business_type varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_file_format_3cb30b68 ON lockdownsf_photo USING btree (file_format);

CREATE INDEX lockdownsf_photo_file_format_3cb30b68_like ON lockdownsf_photo USING btree (file_format varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_neighborhood_id_b5aea7b7 ON lockdownsf_photo USING btree (neighborhood_id);

CREATE INDEX lockdownsf_photo_scene_type_a6bcef47 ON lockdownsf_photo USING btree (scene_type);

CREATE INDEX lockdownsf_photo_scene_type_a6bcef47_like ON lockdownsf_photo USING btree (scene_type varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_source_file_name_0a433148 ON lockdownsf_photo USING btree (source_file_name);

CREATE INDEX lockdownsf_photo_source_file_name_0a433148_like ON lockdownsf_photo USING btree (source_file_name varchar_pattern_ops);

CREATE INDEX lockdownsf_photo_uuid_30ff3ccd_like ON lockdownsf_photo USING btree (uuid varchar_pattern_ops);

ALTER TABLE ONLY lockdownsf_photo
    ADD CONSTRAINT lockdownsf_photo_neighborhood_id_b5aea7b7_fk_lockdowns FOREIGN KEY (neighborhood_id) REFERENCES lockdownsf_neighborhood(id) DEFERRABLE INITIALLY DEFERRED;

