import os
import requests

# List of GeoJSON file URLs
geojson_urls = [
    "https://bm-innovate.s3.amazonaws.com/2023/GIS/Street_Outlines.json",
    "https://bm-innovate.s3.amazonaws.com/2023/GIS/Street_Centerlines.json",
    "https://bm-innovate.s3.amazonaws.com/2023/GIS/Portable_Toilets.json",
    "https://bm-innovate.s3.amazonaws.com/2023/GIS/City_Extent.json",
    "https://bm-innovate.s3.amazonaws.com/2023/GIS/Promenades_Burns.json",
    "https://bm-innovate.s3.amazonaws.com/2023/GIS/CPNs.json",
]

# Directory to save the downloaded files
output_dir = "/Users/taillades/src/couch/static/burning_man_2023_geojson"
os.makedirs(output_dir, exist_ok=True)

# Download each file
for url in geojson_urls:
    filename = os.path.basename(url)
    filepath = os.path.join(output_dir, filename)
    try:
        print(f"Downloading {filename}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Saved to {filepath}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {filename}: {e}")
