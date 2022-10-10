from collections import OrderedDict
from math import ceil, floor
from os.path import join

import fiona
from pyproj import Proj, Transformer
from shapely.geometry import LineString, mapping, shape
from shapely.ops import split, substring
from shapely.ops import transform as sp_transform

# file settings

data_dir = "./data"
input_gpkg = join(data_dir, "osm_road_graph.gpkg")
output_gpkg = join(data_dir, "output-segmented.gpkg")
gfts = join(data_dir, "gfts-210104.gpkg")


# Transformer object, so split can be done in meters
trans = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
trans_back = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)


# Start Busstop id

bus_start = 827400202
bus_stop = 827000802

# Other details

split_meter = 100  # meters


def layers_available(gpkg):
    l = []
    for layer in fiona.listlayers(gpkg):
        with fiona.open(gpkg, "r", layer=layer) as source:
            l.append((layer, len(list(source))))
    return l


def get_bus_stop_shape(gfts, busstop_id):
    with fiona.open(gfts, "r", layer="stops") as source:
        geom = [
            shape(item["geometry"])
            for item in source
            if int(item["properties"]["stop_id"]) == busstop_id
        ]
        return geom


# start_clip = get_bus_stop_shape(gfts, bus_start)[0]
# end_clip = get_bus_stop_shape(gfts, bus_stop)[0]


def split_route(shape, every=100):
    sub_strings = []
    for length in range(0, floor(geom.length) - every, 100):
        if geom.length <= length:
            continue
        # print(length, length+100)
        sub_geom = substring(geom, length, length + 100)
        sub_strings.append(sub_geom)
        # print(sub_geom.length)
        del sub_geom
    # print(length+100, geom.length)
    sub_geom = substring(geom, length + 100, geom.length)
    sub_strings.append(sub_geom)
    # print(sub_geom.length)
    del sub_geom
    return sub_strings


def test_split_route():
    geom = LineString([(0, 0), (0, 80), (3, 500), (50, 532)])
    assert sum([x.length for x in split_route(shape(geom), every=100)]) == geom.length
    assert sum([x.length for x in split_route(shape(geom), every=130)]) == geom.length
    assert sum([x.length for x in split_route(shape(geom), every=122)]) == geom.length
    assert sum([x.length for x in split_route(shape(geom), every=155)]) == geom.length
    assert sum([x.length for x in split_route(shape(geom), every=105)]) == geom.length


def create_segments(geom):
    l = []
    segment_length = geom.length
    if segment_length <= 200:
        l.append(substring(geom, 0, segment_length / 2))
        l.append(substring(geom, segment_length / 2, segment_length))
    elif segment_length > 200 and segment_length <= 250:
        l.append(substring(geom, 0, (segment_length - 50) / 2))
        l.append(
            substring(
                geom,
                (segment_length - 50) / 2,
                segment_length - (segment_length - 50) / 2,
            )
        )
        l.append(
            substring(geom, segment_length - (segment_length - 50) / 2, segment_length)
        )
    elif segment_length > 250:
        rest_length = segment_length - 2 * 100
        mid_divisor = int(ceil(rest_length / 400))
        mid_length = rest_length / mid_divisor

        l.append(substring(geom, 0, 100))

        for x in range(1, mid_divisor + 1):
            # print("midter")
            # print((geom, 100+(x-1)*mid_length, 100 + x * mid_length), mid_node+x-1, mid_node+x)
            l.append(substring(geom, 100 + (x - 1) * mid_length, 100 + x * mid_length))
        l.append(substring(geom, 100 + x * mid_length, segment_length))
    return l


if __name__ == "__main__":

    # Read road graph saved in geopackage
    with fiona.open(input_gpkg, "r", layer="osm_road_graph") as source:
        source = [
            data for data in source
        ]  # if data['properties']['name'] == 'loegster_t']

    meta = {
        "driver": "GPKG",
        "schema": {
            "properties": OrderedDict([("name", "str"), ("length", "float")]),
            "geometry": "LineString",
        },
        "crs": {"init": "epsg:4326"},
        "crs_wkt": 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
    }

    with fiona.open(output_gpkg, "w", layer="osm_segmented", **meta) as sink:
        segments = []
        for item in source:
            trip = shape(item["geometry"])
            prop = item["properties"]

            trip_utm32 = sp_transform(trans.transform, trip)

            sub_item = item.copy()

            for segment in create_segments(trip_utm32):
                print(segment.length)
                new_item = {}
                new_item["properties"] = sub_item["properties"]
                new_item["geometry"] = mapping(
                    sp_transform(trans_back.transform, segment)
                )
                new_item["properties"]["length"] = segment.length
                print(new_item["properties"]["length"])
                segments.append(new_item)
                sink.write(new_item)
