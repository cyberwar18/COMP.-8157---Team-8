-- OLTP -> OLAP transformation for DuckDB (identical logical structure to MySQL version).

DROP TABLE IF EXISTS fact_lineitem_orders;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_supplier;
DROP TABLE IF EXISTS dim_part;
DROP TABLE IF EXISTS dim_date;
DROP VIEW IF EXISTS analytical_wide_view;

CREATE TABLE dim_date AS
SELECT DISTINCT l_shipdate AS date_key,
       EXTRACT(year FROM l_shipdate) AS year,
       EXTRACT(quarter FROM l_shipdate) AS quarter,
       EXTRACT(month FROM l_shipdate) AS month,
       EXTRACT(dow FROM l_shipdate) AS day_of_week
FROM lineitem
WHERE l_shipdate IS NOT NULL;

CREATE TABLE dim_customer AS
SELECT c.c_custkey, c.c_name, c.c_mktsegment, c.c_acctbal,
       n.n_name AS nation_name, r.r_name AS region_name
FROM customer c
JOIN nation n ON c.c_nationkey = n.n_nationkey
JOIN region r ON n.n_regionkey = r.r_regionkey;

CREATE TABLE dim_supplier AS
SELECT s.s_suppkey, s.s_name, s.s_acctbal,
       n.n_name AS nation_name, r.r_name AS region_name
FROM supplier s
JOIN nation n ON s.s_nationkey = n.n_nationkey
JOIN region r ON n.n_regionkey = r.r_regionkey;

CREATE TABLE dim_part AS
SELECT p_partkey, p_name, p_mfgr, p_brand, p_type, p_size, p_container, p_retailprice
FROM part;

CREATE TABLE fact_lineitem_orders AS
SELECT l.l_orderkey, l.l_linenumber, l.l_partkey, l.l_suppkey, o.o_custkey AS c_custkey,
       l.l_shipdate, o.o_orderdate, l.l_quantity, l.l_extendedprice, l.l_discount, l.l_tax,
       l.l_extendedprice * (1 - l.l_discount) AS revenue,
       o.o_orderpriority, o.o_shippriority
FROM lineitem l
JOIN orders o ON l.l_orderkey = o.o_orderkey;

CREATE VIEW analytical_wide_view AS
SELECT f.*, dc.c_name, dc.c_mktsegment, dc.nation_name AS customer_nation, dc.region_name AS customer_region,
       ds.s_name, ds.nation_name AS supplier_nation,
       dp.p_name, dp.p_brand, dp.p_type
FROM fact_lineitem_orders f
JOIN dim_customer dc ON f.c_custkey = dc.c_custkey
JOIN dim_supplier ds ON f.l_suppkey = ds.s_suppkey
JOIN dim_part dp ON f.l_partkey = dp.p_partkey;
