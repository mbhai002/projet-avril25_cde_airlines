--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

-- Started on 2025-11-06 11:49:01

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

-- Extension pg_trgm pour les fonctions de similarité
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 217 (class 1259 OID 85425)
-- Name: flight; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.flight (
    id bigint NOT NULL,
    flight_number character varying(20) NOT NULL,
    from_airport character varying(10) NOT NULL,
    to_airport character varying(10) NOT NULL,
    airline_code character varying(10),
    aircraft_code character varying(10),
    departure_metar_external_id text,
    arrival_taf_external_id text,
    departure_metar_fk bigint,
    arrival_taf_fk bigint,
    departure_scheduled_utc timestamp without time zone,
    departure_actual_utc timestamp without time zone,
    departure_final_utc timestamp without time zone,
    departure_terminal character varying(10),
    departure_gate character varying(10),
    arrival_scheduled_utc timestamp without time zone,
    arrival_actual_utc timestamp without time zone,
    arrival_terminal character varying(10),
    arrival_gate character varying(10),
    status character varying(200),
    status_final character varying(200),
    delay_min integer,
    delay_prob numeric(5,4),
    delay_risk_level character varying(20)
);


ALTER TABLE public.flight OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 85430)
-- Name: metar; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.metar (
    id bigint NOT NULL,
    external_id text NOT NULL,
    observation_time timestamp without time zone NOT NULL,
    raw_text text NOT NULL,
    station_id character varying(10) NOT NULL,
    wind_dir_degrees character varying(3),
    temp_c numeric(5,2),
    dewpoint_c numeric(5,2),
    wind_speed_kt smallint,
    wind_gust_kt smallint,
    visibility_statute_mi numeric(5,2),
    altim_in_hg numeric(5,2),
    sea_level_pressure_mb numeric(6,2),
    flight_category character varying(10),
    maxt_c numeric(5,2),
    mint_c numeric(5,2),
    metar_type character varying(20),
    pcp3hr_in numeric(6,3),
    pcp6hr_in numeric(6,3),
    pcp24hr_in numeric(6,3),
    precip_in numeric(6,3),
    three_hr_pressure_tendency_mb numeric(6,2),
    vert_vis_ft integer,
    wx_string character varying(255)
);


ALTER TABLE public.metar OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 85435)
-- Name: sky_condition; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sky_condition (
    id bigint NOT NULL,
    metar_fk bigint,
    taf_fk bigint,
    sky_cover character varying(50) NOT NULL,
    cloud_base_ft_agl integer,
    cloud_type character varying(50),
    condition_order smallint NOT NULL,
    CONSTRAINT chk_single_parent CHECK ((((metar_fk IS NOT NULL) AND (taf_fk IS NULL)) OR ((metar_fk IS NULL) AND (taf_fk IS NOT NULL))))
);


ALTER TABLE public.sky_condition OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 85439)
-- Name: sky_cover_reference; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sky_cover_reference (
    id bigint NOT NULL,
    code character varying(10) NOT NULL,
    description character varying(100) NOT NULL,
    description_en character varying(100) NOT NULL,
    octal_min numeric(2,1),
    octal_max numeric(2,1),
    percentage_min integer,
    percentage_max integer,
    is_special_code boolean DEFAULT false,
    sort_order integer,
    notes text
);


ALTER TABLE public.sky_cover_reference OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 85445)
-- Name: taf; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.taf (
    id bigint NOT NULL,
    external_id text NOT NULL,
    station_id character varying(10) NOT NULL,
    issue_time timestamp without time zone NOT NULL,
    bulletin_time timestamp without time zone,
    valid_time_from timestamp without time zone,
    valid_time_to timestamp without time zone,
    remarks text,
    fcst_time_from timestamp without time zone,
    fcst_time_to timestamp without time zone,
    wind_dir_degrees smallint,
    wind_speed_kt smallint,
    wind_gust_kt smallint,
    visibility_statute_mi numeric(5,2),
    vert_vis_ft integer,
    wx_string character varying(255),
    altim_in_hg numeric(5,2),
    change_indicator character varying(20),
    probability smallint,
    max_temp_c numeric(5,2),
    min_temp_c numeric(5,2),
    raw_text text NOT NULL
);


ALTER TABLE public.taf OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 85450)
-- Name: all; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public."all" AS
 SELECT f.id AS f_id,
    f.flight_number,
    f.from_airport,
    f.to_airport,
    f.airline_code,
    f.aircraft_code,
    f.departure_metar_fk,
    f.arrival_taf_fk,
    f.departure_scheduled_utc,
    f.departure_actual_utc,
    f.departure_terminal,
    f.departure_gate,
    f.arrival_scheduled_utc,
    f.arrival_actual_utc,
    f.arrival_terminal,
    f.arrival_gate,
    f.status,
    f.status_final,
    f.delay_min,
    m.observation_time,
    m.station_id AS m_station_id,
    m.wind_dir_degrees,
    m.temp_c,
    m.dewpoint_c,
    m.wind_speed_kt,
    m.wind_gust_kt,
    m.visibility_statute_mi,
    m.altim_in_hg,
    m.sea_level_pressure_mb,
    m.flight_category,
    m.maxt_c,
    m.mint_c,
    m.metar_type,
    m.pcp3hr_in,
    m.pcp6hr_in,
    m.pcp24hr_in,
    m.precip_in,
    m.three_hr_pressure_tendency_mb,
    m.vert_vis_ft,
    m.wx_string,
    msc.sky_cover AS msc_sky_cover,
    mscr.description AS msc_sky_cover_description,
    msc.cloud_base_ft_agl AS msc_cloud_base_ft_agl,
    msc.cloud_type AS msc_cloud_type,
    t.station_id AS t_station_id,
    t.issue_time,
    t.bulletin_time,
    t.valid_time_from,
    t.valid_time_to,
    t.remarks,
    t.fcst_time_from,
    t.fcst_time_to,
    t.wind_dir_degrees AS t_wind_dir_degrees,
    t.wind_speed_kt AS t_wind_speed_kt,
    t.wind_gust_kt AS t_wind_gust_kt,
    t.visibility_statute_mi AS t_visibility_statute_mi,
    t.vert_vis_ft AS t_vert_vis_ft,
    t.wx_string AS t_wx_string,
    t.altim_in_hg AS t_altim_in_hg,
    t.change_indicator,
    t.probability,
    t.max_temp_c,
    t.min_temp_c,
    tsc.sky_cover AS tsc_sky_cover,
    tscr.description AS tsc_sky_cover_description,
    tsc.cloud_base_ft_agl AS tsc_cloud_base_ft_agl,
    tsc.cloud_type AS tsc_cloud_type
   FROM ((((((public.flight f
     LEFT JOIN public.metar m ON ((f.departure_metar_fk = m.id)))
     LEFT JOIN public.sky_condition msc ON (((msc.metar_fk = m.id) AND (msc.condition_order = 1))))
     LEFT JOIN public.sky_cover_reference mscr ON (((msc.sky_cover)::text = (mscr.code)::text)))
     LEFT JOIN public.taf t ON ((f.arrival_taf_fk = t.id)))
     LEFT JOIN public.sky_condition tsc ON (((tsc.taf_fk = t.id) AND (tsc.condition_order = 1))))
     LEFT JOIN public.sky_cover_reference tscr ON (((tsc.sky_cover)::text = (tscr.code)::text)));


ALTER VIEW public."all" OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 85455)
-- Name: flight_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.flight_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.flight_id_seq OWNER TO postgres;

--
-- TOC entry 4857 (class 0 OID 0)
-- Dependencies: 223
-- Name: flight_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.flight_id_seq OWNED BY public.flight.id;


--
-- TOC entry 224 (class 1259 OID 85456)
-- Name: metar_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.metar_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.metar_id_seq OWNER TO postgres;

--
-- TOC entry 4858 (class 0 OID 0)
-- Dependencies: 224
-- Name: metar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.metar_id_seq OWNED BY public.metar.id;


--
-- TOC entry 225 (class 1259 OID 85457)
-- Name: sky_condition_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sky_condition_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sky_condition_id_seq OWNER TO postgres;

--
-- TOC entry 4859 (class 0 OID 0)
-- Dependencies: 225
-- Name: sky_condition_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sky_condition_id_seq OWNED BY public.sky_condition.id;


--
-- TOC entry 226 (class 1259 OID 85458)
-- Name: sky_cover_reference_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sky_cover_reference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sky_cover_reference_id_seq OWNER TO postgres;

--
-- TOC entry 4860 (class 0 OID 0)
-- Dependencies: 226
-- Name: sky_cover_reference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sky_cover_reference_id_seq OWNED BY public.sky_cover_reference.id;


--
-- TOC entry 227 (class 1259 OID 85459)
-- Name: taf_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.taf_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.taf_id_seq OWNER TO postgres;

--
-- TOC entry 4861 (class 0 OID 0)
-- Dependencies: 227
-- Name: taf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.taf_id_seq OWNED BY public.taf.id;


--
-- TOC entry 4665 (class 2604 OID 85460)
-- Name: flight id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.flight ALTER COLUMN id SET DEFAULT nextval('public.flight_id_seq'::regclass);


--
-- TOC entry 4666 (class 2604 OID 85461)
-- Name: metar id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metar ALTER COLUMN id SET DEFAULT nextval('public.metar_id_seq'::regclass);


--
-- TOC entry 4667 (class 2604 OID 85462)
-- Name: sky_condition id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sky_condition ALTER COLUMN id SET DEFAULT nextval('public.sky_condition_id_seq'::regclass);


--
-- TOC entry 4668 (class 2604 OID 85463)
-- Name: sky_cover_reference id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sky_cover_reference ALTER COLUMN id SET DEFAULT nextval('public.sky_cover_reference_id_seq'::regclass);


--
-- TOC entry 4670 (class 2604 OID 85464)
-- Name: taf id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.taf ALTER COLUMN id SET DEFAULT nextval('public.taf_id_seq'::regclass);


-- Completed on 2025-11-06 11:49:01

--
-- PostgreSQL database dump complete
--

--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

-- Started on 2025-11-06 11:24:12

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

--
-- TOC entry 4673 (class 2606 OID 85466)
-- Name: flight flight_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.flight
    ADD CONSTRAINT flight_pkey PRIMARY KEY (id);


--
-- TOC entry 4677 (class 2606 OID 85468)
-- Name: metar metar_external_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metar
    ADD CONSTRAINT metar_external_id_key UNIQUE (external_id);


--
-- TOC entry 4679 (class 2606 OID 85470)
-- Name: metar metar_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metar
    ADD CONSTRAINT metar_pkey PRIMARY KEY (id);


--
-- TOC entry 4683 (class 2606 OID 85472)
-- Name: sky_condition sky_condition_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sky_condition
    ADD CONSTRAINT sky_condition_pkey PRIMARY KEY (id);


--
-- TOC entry 4685 (class 2606 OID 85474)
-- Name: sky_cover_reference sky_cover_reference_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sky_cover_reference
    ADD CONSTRAINT sky_cover_reference_code_key UNIQUE (code);


--
-- TOC entry 4687 (class 2606 OID 85476)
-- Name: sky_cover_reference sky_cover_reference_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sky_cover_reference
    ADD CONSTRAINT sky_cover_reference_pkey PRIMARY KEY (id);


--
-- TOC entry 4689 (class 2606 OID 85478)
-- Name: taf taf_external_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.taf
    ADD CONSTRAINT taf_external_id_key UNIQUE (external_id);


--
-- TOC entry 4691 (class 2606 OID 85480)
-- Name: taf taf_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.taf
    ADD CONSTRAINT taf_pkey PRIMARY KEY (id);


--
-- TOC entry 4674 (class 1259 OID 85481)
-- Name: idx_flight_pending_updates; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_flight_pending_updates ON public.flight USING btree (flight_number, from_airport, to_airport) WHERE (status_final IS NULL);


--
-- TOC entry 4675 (class 1259 OID 85482)
-- Name: idx_flight_update_lookup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_flight_update_lookup ON public.flight USING btree (flight_number, from_airport, to_airport, departure_scheduled_utc);


--
-- TOC entry 4680 (class 1259 OID 85483)
-- Name: sc_metar_ord1; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX sc_metar_ord1 ON public.sky_condition USING btree (metar_fk, condition_order) WHERE (metar_fk IS NOT NULL);


--
-- TOC entry 4681 (class 1259 OID 85484)
-- Name: sc_taf_ord1; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX sc_taf_ord1 ON public.sky_condition USING btree (taf_fk, condition_order) WHERE (taf_fk IS NOT NULL);


--
-- TOC entry 4692 (class 2606 OID 85485)
-- Name: flight fk_flight_metar; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.flight
    ADD CONSTRAINT fk_flight_metar FOREIGN KEY (departure_metar_fk) REFERENCES public.metar(id);


--
-- TOC entry 4693 (class 2606 OID 85490)
-- Name: flight fk_flight_taf; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.flight
    ADD CONSTRAINT fk_flight_taf FOREIGN KEY (arrival_taf_fk) REFERENCES public.taf(id);


--
-- TOC entry 4694 (class 2606 OID 85495)
-- Name: sky_condition sky_condition_metar_fk_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sky_condition
    ADD CONSTRAINT sky_condition_metar_fk_fkey FOREIGN KEY (metar_fk) REFERENCES public.metar(id) ON DELETE CASCADE;


--
-- TOC entry 4695 (class 2606 OID 85500)
-- Name: sky_condition sky_condition_taf_fk_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sky_condition
    ADD CONSTRAINT sky_condition_taf_fk_fkey FOREIGN KEY (taf_fk) REFERENCES public.taf(id) ON DELETE CASCADE;


-- Completed on 2025-11-06 11:24:13

--
-- PostgreSQL database dump complete
--


INSERT INTO public.sky_cover_reference (code, description, description_en, octal_min, octal_max, percentage_min, percentage_max, is_special_code, sort_order, notes) VALUES
-- Codes standards de couverture
('FEW', 'Peu de nuages', 'Few clouds', 1.0, 2.0, 12, 25, FALSE, 1, 'Couverture nuageuse de 1/8 à 2/8'),
('SCT', 'Nuages épars', 'Scattered clouds', 3.0, 4.0, 37, 50, FALSE, 2, 'Couverture nuageuse de 3/8 à 4/8'),
('BKN', 'Ciel fragmenté', 'Broken clouds', 5.0, 7.0, 62, 87, FALSE, 3, 'Couverture nuageuse de 5/8 à 7/8'),
('OVC', 'Ciel couvert', 'Overcast clouds', 8.0, 8.0, 100, 100, FALSE, 4, 'Couverture nuageuse complète 8/8'),

-- Codes spéciaux
('NSC', 'Pas de nuages significatifs', 'No significant cloud cover', NULL, NULL, NULL, NULL, TRUE, 10, 'Aucun nuage en dessous de 5000 ft, mais présence possible au-dessus (non CB/TCU)'),
('SKC', 'Ciel dégagé', 'Sky clear', 0.0, 0.0, 0, 0, TRUE, 11, 'Aucune couverture nuageuse (déterminé par météorologue)'),
('NCD', 'Nuages non détectés', 'No clouds detected', NULL, NULL, NULL, NULL, TRUE, 12, 'Aucun nuage mesuré (stations météo automatiques)'),
('CLR', 'Ciel dégagé détecté', 'Clear sky detected', 0.0, 0.0, 0, 0, TRUE, 13, 'Aucune couverture nuageuse détectée en dessous de 12000 ft (stations automatiques)'),

-- Code pour visibilité verticale
('VV', 'Visibilité verticale', 'Vertical visibility', NULL, NULL, NULL, NULL, TRUE, 20, 'Visibilité verticale obscurcie, base nuageuse impossible à établir');


