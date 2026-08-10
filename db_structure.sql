--
-- PostgreSQL database dump
--

\restrict wioeNkGcGQWQaXXdxZdceiL4iuo588rGsRYRNBqRFHktuVb37P8cS1qmL5g06sz

-- Dumped from database version 15.18 (Debian 15.18-1.pgdg13+1)
-- Dumped by pg_dump version 15.18 (Debian 15.18-1.pgdg13+1)

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
-- Name: fraud_scores; Type: TABLE; Schema: public; Owner: ecomuser
--

CREATE TABLE public.fraud_scores (
    id integer NOT NULL,
    order_id character varying(100),
    customer_email character varying(200),
    amount double precision,
    rule_score integer,
    ml_score integer,
    final_score integer,
    status character varying(50),
    reasons text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.fraud_scores OWNER TO ecomuser;

--
-- Name: fraud_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: ecomuser
--

CREATE SEQUENCE public.fraud_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.fraud_scores_id_seq OWNER TO ecomuser;

--
-- Name: fraud_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ecomuser
--

ALTER SEQUENCE public.fraud_scores_id_seq OWNED BY public.fraud_scores.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: ecomuser
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    order_id character varying(100),
    customer_email character varying(200),
    customer_name character varying(200),
    amount double precision,
    quantity integer,
    payment_method character varying(50),
    is_new_customer boolean,
    card_country character varying(10),
    shipping_country character varying(10),
    products text,
    order_timestamp timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.orders OWNER TO ecomuser;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: ecomuser
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.orders_id_seq OWNER TO ecomuser;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ecomuser
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: product_reviews; Type: TABLE; Schema: public; Owner: ecomuser
--

CREATE TABLE public.product_reviews (
    id integer NOT NULL,
    product_name character varying(500),
    review_text text,
    rating double precision,
    textblob_score double precision,
    textblob_sentiment character varying(20),
    vader_score double precision,
    vader_sentiment character varying(20),
    final_sentiment character varying(20),
    analyzed_at timestamp without time zone DEFAULT now(),
    wp_comment_id integer
);


ALTER TABLE public.product_reviews OWNER TO ecomuser;

--
-- Name: product_reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: ecomuser
--

CREATE SEQUENCE public.product_reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.product_reviews_id_seq OWNER TO ecomuser;

--
-- Name: product_reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ecomuser
--

ALTER SEQUENCE public.product_reviews_id_seq OWNED BY public.product_reviews.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: ecomuser
--

CREATE TABLE public.products (
    id integer NOT NULL,
    product_name character varying(500),
    category character varying(100),
    price double precision,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.products OWNER TO ecomuser;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: ecomuser
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_id_seq OWNER TO ecomuser;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ecomuser
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: recommendations; Type: TABLE; Schema: public; Owner: ecomuser
--

CREATE TABLE public.recommendations (
    id integer NOT NULL,
    source_product character varying(500),
    recommended_product character varying(500),
    category character varying(100),
    price character varying(50),
    similarity_score double precision,
    rank integer,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.recommendations OWNER TO ecomuser;

--
-- Name: recommendations_id_seq; Type: SEQUENCE; Schema: public; Owner: ecomuser
--

CREATE SEQUENCE public.recommendations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.recommendations_id_seq OWNER TO ecomuser;

--
-- Name: recommendations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ecomuser
--

ALTER SEQUENCE public.recommendations_id_seq OWNED BY public.recommendations.id;


--
-- Name: stock_levels; Type: TABLE; Schema: public; Owner: ecomuser
--

CREATE TABLE public.stock_levels (
    id integer NOT NULL,
    product_id integer,
    product_name character varying(500),
    stock_level integer,
    status character varying(20),
    checked_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stock_levels OWNER TO ecomuser;

--
-- Name: stock_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: ecomuser
--

CREATE SEQUENCE public.stock_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_levels_id_seq OWNER TO ecomuser;

--
-- Name: stock_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ecomuser
--

ALTER SEQUENCE public.stock_levels_id_seq OWNED BY public.stock_levels.id;


--
-- Name: fraud_scores id; Type: DEFAULT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.fraud_scores ALTER COLUMN id SET DEFAULT nextval('public.fraud_scores_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: product_reviews id; Type: DEFAULT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.product_reviews ALTER COLUMN id SET DEFAULT nextval('public.product_reviews_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: recommendations id; Type: DEFAULT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.recommendations ALTER COLUMN id SET DEFAULT nextval('public.recommendations_id_seq'::regclass);


--
-- Name: stock_levels id; Type: DEFAULT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.stock_levels ALTER COLUMN id SET DEFAULT nextval('public.stock_levels_id_seq'::regclass);


--
-- Name: fraud_scores fraud_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.fraud_scores
    ADD CONSTRAINT fraud_scores_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: product_reviews product_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.product_reviews
    ADD CONSTRAINT product_reviews_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: recommendations recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.recommendations
    ADD CONSTRAINT recommendations_pkey PRIMARY KEY (id);


--
-- Name: stock_levels stock_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT stock_levels_pkey PRIMARY KEY (id);


--
-- Name: stock_levels unique_product_id; Type: CONSTRAINT; Schema: public; Owner: ecomuser
--

ALTER TABLE ONLY public.stock_levels
    ADD CONSTRAINT unique_product_id UNIQUE (product_id);


--
-- PostgreSQL database dump complete
--

\unrestrict wioeNkGcGQWQaXXdxZdceiL4iuo588rGsRYRNBqRFHktuVb37P8cS1qmL5g06sz

