--drop materialized view rute_split_alg;
--drop table if exists rute_split_alg;
--INSERT INTO rute_split_alg3 as
with basis as (
	SELECT
        id,
        rute_nr,
		tags,
        st_transform(geom, 25832) as geom,
        zone -- 1 = byzone
    FROM ruter where upper(tags) != 'MIDT' and id = 275
), basis2 as (
	SELECT
		id,
		rute_nr,
		tags,
		geom,
		zone,
		st_length(geom) as total_length,
		CASE WHEN zone = 1
		    THEN
		        100
		    ELSE
		        200
		END as dist_endings,
		CASE WHEN zone = 1
		    THEN
		        300
		    ELSE
		        300
		END as max_length
	FROM basis
), end_frac as (
	SELECT
		id,
		geom, zone,
		rute_nr, tags,
		total_length,
		CASE WHEN dist_endings <= total_length and (dist_endings/total_length) < 0.5
		    THEN
		        dist_endings/total_length
		    ELSE
		        0.5
		END as dist_frac,
		max_length
	FROM basis2
), first_cut as (
	SELECT id,
	rute_nr,
	tags,
	dist_frac,
    ST_LineSubstring(geom, 0.0, dist_frac) as new_geom,
    --st_astext(ST_LineSubstring(geom, 0.0, dist_frac)),
    'start' as ending,
    max_length
    FROM end_frac
	UNION ALL
	select id, rute_nr, tags,dist_frac,
        ST_LineSubstring(geom, 1-dist_frac, 1) as new_geom, 'end' as ending, max_length FROM end_frac
	UNION ALL
	select id, rute_nr, tags,dist_frac,
        ST_LineSubstring(geom, dist_frac, 1-dist_frac) as new_geom, 'mid' as ending, max_length FROM end_frac
), first_cut_length AS (
    SELECT
        *, st_length(new_geom) as new_length
    FROM first_cut
), count_segments as (
    SELECT
        id, rute_nr, tags, dist_frac,
         new_geom, ending,
         max_length, new_length,
         CEIL(new_length/max_length)::int as no_segments

    FROM first_cut_length WHERE ST_GeometryType(new_geom) != 'ST_Point'
), segmenting as (
    select
        id,
        rute_nr,
        tags,
        dist_frac,
        new_geom,
        new_length,
        ending,
        max_length,
        no_segments,
        CASE WHEN ending = 'mid'
            THEN
                1/no_segments::numeric
            ELSE
                0::numeric
        END as new_dist_frac,

        CASE WHEN ending = 'mid'
            THEN
                new_length/no_segments::numeric
            ELSE
                0::numeric
        END as segment_length
    FROm count_segments
), basic as (
    SELECT
        id,
        rute_nr,
        tags,
        dist_frac,
        new_geom,
        new_length,
        ending,
        max_length,
        no_segments,
        new_dist_frac,
        segment_length
    from segmenting
), segments as (
    SELECT
        id,
        rute_nr,
        tags,
        dist_frac,
        new_geom,
        new_length,
        ending,
        max_length,
        no_segments,
        new_dist_frac,
        segment_length,
        1 as segment_id
    FROM
        basic
    WHERE ending != 'mid'
    UNION all
    SELECT
        id,
        rute_nr,
        tags,
        dist_frac,
        new_geom,
        new_length,
        ending,
        max_length,
        no_segments,
        new_dist_frac,
        segment_length,
        generate_series(1, no_segments) as segment_id
    FROM basic
    WHERE ending = 'mid'
), fractions as (
    SELECT
        id,
        rute_nr,
        tags,
        dist_frac,
        new_geom,
        ending,
        new_length,
        max_length,
        no_segments,
        new_dist_frac,
        segment_length,
        segment_id,
        ((segment_id-1)*new_dist_frac)::numeric as from_frac,
        CASE WHEN segment_id = no_segments
            THEN 1
            ELSE (segment_id*new_dist_frac)::numeric
        END as to_frac
    FROM segments
)
select
        id,
        rute_nr,
        tags,
        dist_frac,
        st_transform(ST_LineSubstring(new_geom, from_frac, to_frac), 4326) as new_geom,
        st_astext(st_transform(ST_LineSubstring(new_geom, from_frac, to_frac), 4326)) as as_text,
        ending,
        st_length(ST_LineSubstring(new_geom, from_frac, to_frac)) as split_length,
        new_length,
        max_length,
        no_segments,
        new_dist_frac,
        from_frac,
        to_frac,
        segment_length,
        segment_id
 from fractions
order by id, segment_id
