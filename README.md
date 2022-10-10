# busstoette

Dette repository består af kode stumper der bruges til opdelingen og split af ruter på busnettet

## Help sql

Get buffer a 100 meters around end points

```
select st_buffer(st_transform(st_startpoint(geom), 25832), 100) as geom_buf, *  from "osm rute 57 - rå"
```

```
DROP materialized view IF EXISTS rute_57_splits;
create materialized view rute_57_splits as
with basis as (
	SELECT id,
	st_transform(geom, 25832) as geom,
	fid, osm_id, members, attributes, tags, tag_name, tag_value, name
	FROM public.rute_osm_rute_57
--	WHERE tags = 'Syd'
), grund as (
	SELECT
		id, geom, cast(st_length(geom) as float) as length, osm_id, tags
	FROM basis
), lengthy as (
	select
		id, length, 100/length as frac, osm_id, tags, geom
	from grund where length > 200
), length_ends_and_mids as (
	select
		*, ST_LineSubstring(geom, 0::float, frac) as line
	from lengthy
	UNION ALL
	SELECT
		*, ST_LineSubstring(geom, 1-frac, 1) as line
 	from lengthy
	UNION ALL
	SELECT
		*, ST_LineSubstring(geom, frac, 1-frac) as line
 	from lengthy
	UNION ALL
	SELECT
		id, length, 100/length as frac, osm_id, tags, geom,
		geom as line
 	from grund where length <= 200
)
SELECT
    id, frac, osm_id, tags,
    st_transform(geom, 4326) as geom,
    st_transform(line, 4326) as line, st_length(line) as length
FROM length_ends_and_mids;

```
