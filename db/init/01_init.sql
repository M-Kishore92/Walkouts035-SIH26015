-- PostGIS Extension Initialization & Schema Setup
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table constraints and spatial indexing optimizations
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET work_mem = '64MB';
