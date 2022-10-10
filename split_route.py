from collections import OrderedDict
from math import floor

import fiona
from pyproj import Proj, Transformer
from shapely.geometry import LineString, mapping, shape
from shapely.ops import split, substring
from shapely.ops import transform as sp_transform

# Transformer object, so split can be done in meters
trans = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
trans_back = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)

from os.path import join

# file settings

data_dir = "./data"
input_gpkg = join(data_dir, "output_trips.gpkg")
output_gpkg = join(data_dir, "output_trips2.gpkg")
gfts = join(data_dir, "gfts-210104.gpkg")

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


start_clip = get_bus_stop_shape(gfts, bus_start)[0]
end_clip = get_bus_stop_shape(gfts, bus_stop)[0]

every = 100

geom = LineString([(0, 0), (0, 80), (3, 500), (50, 532)])


def split_route(shape, every=100):
    sub_strings = []
    for length in range(0, floor(geom.length) - every, 100):
        if geom.length <= length:
            continue
        sub_geom = substring(geom, length, length + 100)
        sub_strings.append(sub_geom)
        del sub_geom
    sub_geom = substring(geom, length + 100, geom.length)
    sub_strings.append(sub_geom)
    del sub_geom
    return sub_strings


with fiona.open(input_gpkg, "r", layer="road_segments") as source:
    clipped_line = []
    sub_clipped_line = []
    meta = source.meta
    for item in source:
        trips = shape(item["geometry"])
        first_float = trips.project(start_clip, normalized=True)
        last_float = trips.project(end_clip, normalized=True)
        final = trips  # substring(trips, first_float, last_float, normalized=True)
        # print(final.wkt)
        item["geometry"] = mapping(final)
        clipped_line.append(item)

        final_utm32 = sp_transform(trans.transform, final)
        max_length = final_utm32.length
        sub_item = item.copy()
        for length in range(
            0, floor(final_utm32.length) - 100, 100
        ):  # int(final_utm32.length/split_meter), 100):
            #
            if max_length <= length:
                continue
            print(length, length + 100)
            sub_item["geometry"] = mapping(
                sp_transform(
                    trans_back.transform, substring(final_utm32, length, length + 100)
                )
            )
            sub_item["properties"]["length_start"] = length
            sub_clipped_line.append(sub_item)
            sub_item = sub_item.copy()
        print(length + 100, final_utm32.length)
        item["geometry"] = mapping(
            sp_transform(
                trans_back.transform, substring(final, length + 100, max_length)
            )
        )
        sub_item["properties"]["length_start"] = length + 100
        sub_clipped_line.append(sub_item)

with fiona.open(output_gpkg, "w", layer="trip_clipped", **meta) as dst:
    # write clipped_line list to output_gpkg
    dst.writerecords(clipped_line)

meta = {
    "driver": "GPKG",
    "schema": {
        "properties": OrderedDict([("trip", "str"), ("length_start", "int")]),
        "geometry": "LineString",
    },
    "crs": {"init": "epsg:4326"},
    "crs_wkt": 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
}
with fiona.open(output_gpkg, "w", layer="road_segments_subclipped", **meta) as dst:
    # write clipped_line list to output_gpkg
    dst.writerecords(sub_clipped_line)
