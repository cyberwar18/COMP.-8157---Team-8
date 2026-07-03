-- OLTP -> OLAP transformation for MySQL.
-- Star schema: fact_lineitem_orders surrounded by dim_customer, dim_supplier,
-- dim_part, dim_date. Plus a denormalized wide analytical view.

DROP TABLE IF EXISTS fact_lineitem_orders;
DROP TABLE IF EXISTS dim_customer, dim_supplier, dim_part, dim_date;
DROP VIEW IF EXISTS analytical_wide_view;

CREATE TABLE dim_date (
    date_key    DATE PRIMARY KEY,
    year        INT,
    quarter     INT,
    month       INT,
    day_of_week INT
) ENGINE=InnoDB;

INSERT INTO dim_date (date_key, year, quarter, month, day_of_week)
SELECT DISTINCT l_shipdate,
       YEAR(l_shipdate), QUARTER(l_shipdate), MONTH(l_shipdate), DAYOFWEEK(l_shipdate)
FROM lineitem
WHERE l_shipdate IS NOT NULL;

CREATE TABLE dim_customer AS
SELECT c.c_custkey, c.c_name, c.c_mktsegment, c.c_acctbal,
       n.n_name AS nation_name, r.r_name AS region_name
FROM customer c
JOIN nation n ON c.c_nationkey = n.n_nationkey
JOIN region r ON n.n_regionkey = r.r_regionkey;
ALTER TABLE dim_customer ADD PRIMARY KEY (c_custkey);

CREATE TABLE dim_supplier AS
SELECT s.s_suppkey, s.s_name, s.s_acctbal,
       n.n_name AS nation_name, r.r_name AS region_name
FROM supplier s
JOIN nation n ON s.s_nationkey = n.n_nationkey
JOIN region r ON n.n_regionkey = r.r_regionkey;
ALTER TABLE dim_supplier ADD PRIMARY KEY (s_suppkey);

CREATE TABLE dim_part AS
SELECT p_partkey, p_name, p_mfgr, p_brand, p_type, p_size, p_container, p_retailprice
FROM part;
ALTER TABLE dim_part ADD PRIMARY KEY (p_partkey);

-- Fact table: one row per lineitem, pre-joined to its order.
CREATE TABLE fact_lineitem_orders (
    l_orderkey      INT NOT NULL,
    l_linenumber    INT NOT NULL,
    l_partkey       INT NOT NULL,
    l_suppkey       INT NOT NULL,
    c_custkey       INT NOT NULL,
    l_shipdate      DATE NOT NULL,
    o_orderdate     DATE NOT NULL,
    l_quantity      DECIMAL(15,2),
    l_extendedprice DECIMAL(15,2),
    l_discount      DECIMAL(15,2),
    l_tax           DECIMAL(15,2),
    revenue         DECIMAL(15,2),
    o_orderpriority CHAR(15),
    o_shippriority  INT,
    PRIMARY KEY (l_orderkey, l_linenumber),
    KEY idx_fact_custkey (c_custkey),
    KEY idx_fact_partkey (l_partkey),
    KEY idx_fact_suppkey (l_suppkey),
    KEY idx_fact_shipdate (l_shipdate)
) ENGINE=InnoDB;

INSERT INTO fact_lineitem_orders
SELECT l.l_orderkey, l.l_linenumber, l.l_partkey, l.l_suppkey, o.o_custkey,
       l.l_shipdate, o.o_orderdate, l.l_quantity, l.l_extendedprice, l.l_discount, l.l_tax,
       l.l_extendedprice * (1 - l.l_discount) AS revenue,
       o.o_orderpriority, o.o_shippriority
FROM lineitem l
JOIN orders o ON l.l_orderkey = o.o_orderkey;

-- Denormalized wide view flattening all dimensions for columnar-scan style access.
CREATE VIEW analytical_wide_view AS
SELECT f.*, dc.c_name, dc.c_mktsegment, dc.nation_name AS customer_nation, dc.region_name AS customer_region,
       ds.s_name, ds.nation_name AS supplier_nation,
       dp.p_name, dp.p_brand, dp.p_type
FROM fact_lineitem_orders f
JOIN dim_customer dc ON f.c_custkey = dc.c_custkey
JOIN dim_supplier ds ON f.l_suppkey = ds.s_suppkey
JOIN dim_part dp ON f.l_partkey = dp.p_partkey;
