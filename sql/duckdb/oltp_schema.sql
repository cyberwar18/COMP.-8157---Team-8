-- Same logical TPC-H schema for DuckDB. No manual secondary indexes: DuckDB relies
-- on native zone-map (min/max) metadata per column block for predicate pushdown.

DROP TABLE IF EXISTS lineitem;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS partsupp;
DROP TABLE IF EXISTS part;
DROP TABLE IF EXISTS supplier;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS nation;
DROP TABLE IF EXISTS region;

CREATE TABLE region (
    r_regionkey INTEGER PRIMARY KEY,
    r_name      VARCHAR NOT NULL,
    r_comment   VARCHAR
);

CREATE TABLE nation (
    n_nationkey INTEGER PRIMARY KEY,
    n_name      VARCHAR NOT NULL,
    n_regionkey INTEGER NOT NULL REFERENCES region(r_regionkey),
    n_comment   VARCHAR
);

CREATE TABLE customer (
    c_custkey    INTEGER PRIMARY KEY,
    c_name       VARCHAR NOT NULL,
    c_address    VARCHAR,
    c_nationkey  INTEGER NOT NULL REFERENCES nation(n_nationkey),
    c_phone      VARCHAR,
    c_acctbal    DECIMAL(15,2),
    c_mktsegment VARCHAR,
    c_comment    VARCHAR
);

CREATE TABLE supplier (
    s_suppkey   INTEGER PRIMARY KEY,
    s_name      VARCHAR NOT NULL,
    s_address   VARCHAR,
    s_nationkey INTEGER NOT NULL REFERENCES nation(n_nationkey),
    s_phone     VARCHAR,
    s_acctbal   DECIMAL(15,2),
    s_comment   VARCHAR
);

CREATE TABLE part (
    p_partkey     INTEGER PRIMARY KEY,
    p_name        VARCHAR NOT NULL,
    p_mfgr        VARCHAR,
    p_brand       VARCHAR,
    p_type        VARCHAR,
    p_size        INTEGER,
    p_container   VARCHAR,
    p_retailprice DECIMAL(15,2),
    p_comment     VARCHAR
);

CREATE TABLE partsupp (
    ps_partkey    INTEGER NOT NULL REFERENCES part(p_partkey),
    ps_suppkey    INTEGER NOT NULL REFERENCES supplier(s_suppkey),
    ps_availqty   INTEGER,
    ps_supplycost DECIMAL(15,2),
    ps_comment    VARCHAR,
    PRIMARY KEY (ps_partkey, ps_suppkey)
);

CREATE TABLE orders (
    o_orderkey      INTEGER PRIMARY KEY,
    o_custkey       INTEGER NOT NULL REFERENCES customer(c_custkey),
    o_orderstatus   VARCHAR,
    o_totalprice    DECIMAL(15,2),
    o_orderdate     DATE NOT NULL,
    o_orderpriority VARCHAR,
    o_clerk         VARCHAR,
    o_shippriority  INTEGER,
    o_comment       VARCHAR
);

CREATE TABLE lineitem (
    l_orderkey      INTEGER NOT NULL REFERENCES orders(o_orderkey),
    l_partkey       INTEGER NOT NULL REFERENCES part(p_partkey),
    l_suppkey       INTEGER NOT NULL REFERENCES supplier(s_suppkey),
    l_linenumber    INTEGER NOT NULL,
    l_quantity      DECIMAL(15,2),
    l_extendedprice DECIMAL(15,2),
    l_discount      DECIMAL(15,2),
    l_tax           DECIMAL(15,2),
    l_returnflag    VARCHAR,
    l_linestatus    VARCHAR,
    l_shipdate      DATE NOT NULL,
    l_commitdate    DATE,
    l_receiptdate   DATE,
    l_shipinstruct  VARCHAR,
    l_shipmode      VARCHAR,
    l_comment       VARCHAR,
    PRIMARY KEY (l_orderkey, l_linenumber)
);
