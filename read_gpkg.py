import fiona
from shapely.geometry import shape

input_file = "data/output_trips.gpkg"

for layername in fiona.listlayers(input_file):
    with fiona.open(input_file, "r", layer=layername) as source:
        meta = source.meta
        print(layername, len(source))  # 45 for road_segments

for layername in fiona.listlayers(input_file):
    with fiona.open(input_file, "r", layer=layername) as source:
        meta = source.meta
        print(layername, len(source))  # 45 for road_segments
        for item in source:
            if item["properties"].get("trip", False) == "trip_01_gps.csv":
                print(item["properties"])

            print(trips.wkt)  # print as WellKnownText
            print(list(trips.coords))
