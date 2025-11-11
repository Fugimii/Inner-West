# Takes in https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files
# And converts it into SQL database of only the ones surrounding the Inner West

from shapely.geometry import mapping
import geopandas as gpd
import sqlite3
import json
from pathlib import Path
import zipfile
import urllib.request

def _setup_gdf():
    url = "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files/SAL_2021_AUST_GDA2020_SHP.zip"
    zip_path = Path("SAL_2021_AUST_GDA2020_SHP.zip")
    out_dir = Path("SAL_2021_AUST_GDA2020_SHP")

    if not out_dir.exists():
        if not zip_path.exists():
            print("Downloading ZIP...")
            urllib.request.urlretrieve(url, zip_path)
        print("Extracting ZIP...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(".")
    else:
        print("Shapefile directory already present; skipping download/extract.")

    gdf = gpd.read_file("./SAL_2021_AUST_GDA2020_SHP/SAL_2021_AUST_GDA2020.shp")
    # Re-project to a projected CRS to calculate distances in meters
    gdf = gdf.to_crs(epsg=7856)

    return gdf

def _calculate_distance(row, gdf):
    center = gdf[gdf["SAL_NAME21"] == "Leichhardt (NSW)"]
    return center.geometry.centroid.distance(row.geometry.centroid, align=False).values[0]

def create_suburbs_database():
    gdf = _setup_gdf()
    print(gdf)

    con = sqlite3.connect("database.db")
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS suburbs")
    cur.execute("CREATE TABLE suburbs (suburb TEXT, center TEXT, shape TEXT)")

    # Iterate through all suburbs and find those within 7.5km of Leichhardt
    for index, row in gdf.iterrows():
        # Dataset is a little goofy
        if row["geometry"] is None:
            continue
        if _calculate_distance(row, gdf) < 7500: # 7.5km
            suburb = row["SAL_NAME21"].split(" (")[0]
            # Convert back to lat and long
            geo_geom = gpd.GeoSeries([row["geometry"]], crs=gdf.crs).to_crs(epsg=7844).iloc[0]
            center = json.dumps(mapping(geo_geom.centroid))
            shape = json.dumps(mapping(geo_geom))
            cur.execute(
                "INSERT OR IGNORE INTO suburbs (suburb, center, shape) VALUES (?, ?, ?)",
                (suburb, center, shape)
            )
    
    con.commit()
    con.close()

if __name__ == "__main__":
    create_suburbs_database()    