-- Raw TPC-H transactional schema for MySQL (InnoDB).
-- Clustered PK B-Tree + secondary indexes on high-cardinality join/filter columns.

DROP TABLE IF EXISTS lineitem, orders, customer, supplier, partsupp, part, nation, region;

CREATE TABLE region (
    r_regionkey INT PRIMARY KEY,
    r_name      CHAR(25) NOT NULL,
    r_comment   VARCHAR(152)
) ENGINE=InnoDB;

CREATE TABLE nation (
    n_nationkey INT PRIMARY KEY,
    n_name      CHAR(25) NOT NULL,
    n_regionkey INT NOT NULL,
    n_comment   VARCHAR(152),
    FOREIGN KEY (n_regionkey) REFERENCES region(r_regionkey)
) ENGINE=InnoDB;

CREATE TABLE customer (
    c_custkey    INT PRIMARY KEY,
    c_name       VARCHAR(25) NOT NULL,
    c_address    VARCHAR(40),
    c_nationkey  INT NOT NULL,
    c_phone      CHAR(15),
    c_acctbal    DECIMAL(15,2),
    c_mktsegment CHAR(10),
    c_comment    VARCHAR(117),
    KEY idx_customer_nationkey (c_nationkey),
    FOREIGN KEY (c_nationkey) REFERENCES nation(n_nationkey)
) ENGINE=InnoDB;

CREATE TABLE supplier (
    s_suppkey   INT PRIMARY KEY,
    s_name      CHAR(25) NOT NULL,
    s_address   VARCHAR(40),
    s_nationkey INT NOT NULL,
    s_phone     CHAR(15),
    s_acctbal   DECIMAL(15,2),
    s_comment   VARCHAR(101),
    KEY idx_supplier_nationkey (s_nationkey),
    FOREIGN KEY (s_nationkey) REFERENCES nation(n_nationkey)
) ENGINE=InnoDB;

CREATE TABLE part (
    p_partkey     INT PRIMARY KEY,
    p_name        VARCHAR(55) NOT NULL,
    p_mfgr        CHAR(25),
    p_brand       CHAR(10),
    p_type        VARCHAR(25),
    p_size        INT,
    p_container   CHAR(10),
    p_retailprice DECIMAL(15,2),
    p_comment     VARCHAR(23)
) ENGINE=InnoDB;

CREATE TABLE partsupp (
    ps_partkey    INT NOT NULL,
    ps_suppkey    INT NOT NULL,
    ps_availqty   INT,
    ps_supplycost DECIMAL(15,2),
    ps_comment    VARCHAR(199),
    PRIMARY KEY (ps_partkey, ps_suppkey),
    KEY idx_partsupp_suppkey (ps_suppkey),
    FOREIGN KEY (ps_partkey) REFERENCES part(p_partkey),
    FOREIGN KEY (ps_suppkey) REFERENCES supplier(s_suppkey)
) ENGINE=InnoDB;

CREATE TABLE orders (
    o_orderkey      INT PRIMARY KEY,
    o_custkey       INT NOT NULL,
    o_orderstatus   CHAR(1),
    o_totalprice    DECIMAL(15,2),
    o_orderdate     DATE NOT NULL,
    o_orderpriority CHAR(15),
    o_clerk         CHAR(15),
    o_shippriority  INT,
    o_comment       VARCHAR(79),
    KEY idx_orders_custkey (o_custkey),
    KEY idx_orders_orderdate (o_orderdate),
    FOREIGN KEY (o_custkey) REFERENCES customer(c_custkey)
) ENGINE=InnoDB;

CREATE TABLE lineitem (
    l_orderkey      INT NOT NULL,
    l_partkey       INT NOT NULL,
    l_suppkey       INT NOT NULL,
    l_linenumber    INT NOT NULL,
    l_quantity      DECIMAL(15,2),
    l_extendedprice DECIMAL(15,2),
    l_discount      DECIMAL(15,2),
    l_tax           DECIMAL(15,2),
    l_returnflag    CHAR(1),
    l_linestatus    CHAR(1),
    l_shipdate      DATE NOT NULL,
    l_commitdate    DATE,
    l_receiptdate   DATE,
    l_shipinstruct  CHAR(25),
    l_shipmode      CHAR(10),
    l_comment       VARCHAR(44),
    PRIMARY KEY (l_orderkey, l_linenumber),
    KEY idx_lineitem_partkey (l_partkey),
    KEY idx_lineitem_suppkey (l_suppkey),
    KEY idx_lineitem_shipdate (l_shipdate),
    FOREIGN KEY (l_orderkey) REFERENCES orders(o_orderkey),
    FOREIGN KEY (l_partkey) REFERENCES part(p_partkey),
    FOREIGN KEY (l_suppkey) REFERENCES supplier(s_suppkey)
) ENGINE=InnoDB;
