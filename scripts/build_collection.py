#!/usr/bin/env python3
"""Build the Tanganyika/Tanzania historical boundary collection.

The collection deliberately distinguishes direct historical GIS from reconstructed
or proxy snapshots. Proxy years are useful for historical visualization and
comparison, but are NOT presented as exact survey/cadastral boundaries.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

PRINCETON_1948 = (
    "https://figgy.princeton.edu/downloads/33071165-4dff-40fe-8c7b-927ad348e216/"
    "file/b6a04a3c-5513-4623-a029-ec4fcea97348"
)
PRINCETON_1950 = (
    "https://figgy.princeton.edu/downloads/2bdebb26-357a-4f36-ba6d-001b7a40c38b/"
    "file/3bc8468e-bba4-4598-99e6-62ce2d29936e"
)
REGIONS_1967 = (
    "https://github.com/Heed725/Tanzania-1967-Region-Shapefiles/releases/download/"
    "1967-regions/Tanzania_Regions_1967.geojson"
)

ZANZIBAR_TOKENS = {
    "KASKAZINI PEMBA",
    "KUSINI PEMBA",
    "KASKAZINI UNGUJA",
    "KUSINI UNGUJA",
    "MJINI MAGHARIBI",
    "PEMBA NORTH",
    "PEMBA SOUTH",
    "ZANZIBAR NORTH",
    "ZANZIBAR SOUTH",
    "ZANZIBAR WEST",
    "UNGUJA NORTH",
    "UNGUJA SOUTH",
}

CURRENT_REGION_NAMES = {
    "ARUSHA",
    "DAR ES SALAAM",
    "DODOMA",
    "GEITA",
    "IRINGA",
    "KAGERA",
    "KATAVI",
    "KIGOMA",
    "KILIMANJARO",
    "LINDI",
    "MANYARA",
    "MARA",
    "MBEYA",
    "MOROGORO",
    "MTWARA",
    "MWANZA",
    "NJOMBE",
    "PWANI",
    "RUKWA",
    "RUVUMA",
    "SHINYANGA",
    "SIMIYU",
    "SINGIDA",
    "SONGWE",
    "TABORA",
    "TANGA",
}


def norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.upper().replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def download(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, target)
    return target


def extract_zip(path: Path, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as zf:
        zf.extractall(out)
    return out


def first_shp(root: Path) -> Path:
    files = sorted(root.rglob("*.shp"))
    if not files:
        raise FileNotFoundError(f"No shapefile found under {root}")
    return files[0]


def clean(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    try:
        invalid = ~gdf.geometry.is_valid
        if invalid.any():
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)
    except Exception:
        pass
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    else:
        gdf = gdf.to_crs(4326)
    return gdf


def detect_col(gdf: gpd.GeoDataFrame, preferred: list[str]) -> str:
    for c in preferred:
        if c in gdf.columns:
            return c
    low = {c.lower(): c for c in gdf.columns}
    for c in preferred:
        if c.lower() in low:
            return low[c.lower()]
    raise RuntimeError(f"Could not find any of {preferred}; columns={list(gdf.columns)}")


def detect_modern_fields(gdf: gpd.GeoDataFrame) -> tuple[str, str]:
    region_candidates = ["REGION", "Region", "region", "REGION_NAME", "NAME_1", "MKOA"]
    unit_candidates = ["DISTRICT", "District", "district", "COUNCIL", "Council", "NAME_2", "WILAYA"]

    region_col = None
    for col in region_candidates:
        if col in gdf.columns:
            vals = {norm(v) for v in gdf[col].dropna().unique()}
            if len(vals & CURRENT_REGION_NAMES) >= 8:
                region_col = col
                break
    if region_col is None:
        best = (-1, None)
        for col in gdf.columns:
            if col == gdf.geometry.name:
                continue
            vals = {norm(v) for v in gdf[col].dropna().unique()}
            score = len(vals & CURRENT_REGION_NAMES)
            if score > best[0]:
                best = (score, col)
        region_col = best[1]
    if region_col is None:
        raise RuntimeError("Could not detect modern region column")

    for col in unit_candidates:
        if col in gdf.columns and col != region_col:
            return region_col, col

    for col in gdf.columns:
        if col not in {region_col, gdf.geometry.name}:
            vals = [norm(v) for v in gdf[col].dropna().unique()]
            if any("CHATO" in v or "BUKOMBE" in v or "BUSEGA" in v for v in vals):
                return region_col, col
    raise RuntimeError("Could not detect modern district/council column")


def save_layer(gdf: gpd.GeoDataFrame, year: int, stem: str, root: Path, meta: dict) -> None:
    out = root / "data" / str(year)
    dist = root / "dist"
    previews = root / "docs" / "previews"
    out.mkdir(parents=True, exist_ok=True)
    dist.mkdir(parents=True, exist_ok=True)
    previews.mkdir(parents=True, exist_ok=True)

    gdf = clean(gdf)
    shp = out / f"{stem}.shp"
    geojson = out / f"{stem}.geojson"
    gpkg = out / f"{stem}.gpkg"
    gdf.to_file(shp, driver="ESRI Shapefile", encoding="UTF-8")
    gdf.to_file(geojson, driver="GeoJSON")
    gdf.to_file(gpkg, layer=stem[:50], driver="GPKG")
    (out / f"{stem}.cpg").write_text("UTF-8\n", encoding="ascii")

    zip_path = dist / f"{stem}_Shapefile.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for ext in ["shp", "shx", "dbf", "prj", "cpg"]:
            p = out / f"{stem}.{ext}"
            if p.exists():
                zf.write(p, arcname=p.name)

    meta = dict(meta)
    meta.update({"year": year, "feature_count": int(len(gdf)), "crs": "EPSG:4326"})
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(8, 9))
    gdf.boundary.plot(ax=ax, linewidth=0.65)
    label_col = next((c for c in ["REGION", "PROVINCE", "DISTRICT", "NAME"] if c in gdf.columns), None)
    if label_col and len(gdf) <= 60:
        for _, row in gdf.iterrows():
            p = row.geometry.representative_point()
            ax.text(p.x, p.y, str(row[label_col]), fontsize=5.5, ha="center", va="center")
    ax.set_title(meta.get("title", stem))
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(previews / f"{stem}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def read_princeton_1948(work: Path) -> gpd.GeoDataFrame:
    archive = download(PRINCETON_1948, work / "sources" / "1948.zip")
    src = extract_zip(archive, work / "sources" / "1948")
    return clean(gpd.read_file(first_shp(src)))


def read_princeton_1950(work: Path) -> gpd.GeoDataFrame:
    archive = download(PRINCETON_1950, work / "sources" / "1950.zip")
    src = extract_zip(archive, work / "sources" / "1950")
    return clean(gpd.read_file(first_shp(src)))


def mainland_outline(source: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    geom = source.geometry.union_all()
    return gpd.GeoDataFrame({"NAME": ["Tanganyika area"], "geometry": [geom]}, crs=source.crs)


def lake_split_1960_61(districts: gpd.GeoDataFrame, year: int) -> gpd.GeoDataFrame:
    province_col = detect_col(districts, ["Province", "PROVINCE"])
    district_col = detect_col(districts, ["District", "DISTRICT"])
    work = districts[[province_col, district_col, "geometry"]].copy()
    work["PROVINCE"] = work[province_col].astype(str).str.strip()
    d = work[district_col].map(norm)
    p = work[province_col].map(norm)
    west_lake = d.str.contains("BUKOBA|BIHARAMULO")
    work.loc[(p == "LAKE PROVINCE") & west_lake, "PROVINCE"] = "West Lake"
    work.loc[(p == "LAKE PROVINCE") & ~west_lake, "PROVINCE"] = "Lake Province"
    out = work[["PROVINCE", "geometry"]].dissolve(by="PROVINCE", as_index=False)
    out["YEAR"] = year
    out["METHOD"] = "Reconstructed from 1950 district geometry; Lake Province split using district lineage"
    out["QUALITY"] = "reconstructed-proxy"
    out["SOURCE"] = "Princeton 1950 historical districts + documented late-colonial administrative lineage"
    return out


def read_1967(work: Path) -> gpd.GeoDataFrame:
    path = download(REGIONS_1967, work / "sources" / "Tanzania_Regions_1967.geojson")
    gdf = clean(gpd.read_file(path))
    region_col = detect_col(gdf, ["REGION_1967", "REGION"])
    out = gdf[[region_col, "geometry"]].rename(columns={region_col: "REGION"})
    return out


def modern_districts(path: Path) -> tuple[gpd.GeoDataFrame, str, str]:
    candidates = [path / "District_Unsegmented_2017.shp", path / "District_Council.shp"]
    shp = next((p for p in candidates if p.exists()), None)
    if shp is None:
        shp = first_shp(path)
    gdf = clean(gpd.read_file(shp))
    region_col, unit_col = detect_modern_fields(gdf)
    return gdf, region_col, unit_col


def assign_geita_simiyu(region: str, unit: str, default_map: dict[str, str]) -> str | None:
    if any(token == region or token in region for token in ZANZIBAR_TOKENS):
        return None
    if region == "GEITA":
        if "CHATO" in unit:
            return "WEST LAKE"
        if "BUKOMBE" in unit or "MBOGWE" in unit:
            return "SHINYANGA"
        return "MWANZA"
    if region == "SIMIYU":
        if "BUSEGA" in unit:
            return "MWANZA"
        return "SHINYANGA"
    return default_map.get(region)


def reconstruct_modern_year(
    districts: gpd.GeoDataFrame,
    region_col: str,
    unit_col: str,
    year: int,
) -> gpd.GeoDataFrame:
    common = {
        "ARUSHA": "ARUSHA",
        "MANYARA": "ARUSHA",
        "DAR ES SALAAM": "DAR ES SALAAM",
        "PWANI": "COAST",
        "DODOMA": "DODOMA",
        "IRINGA": "IRINGA",
        "NJOMBE": "IRINGA",
        "KIGOMA": "KIGOMA",
        "KILIMANJARO": "KILIMANJARO",
        "MARA": "MARA",
        "MBEYA": "MBEYA",
        "SONGWE": "MBEYA",
        "MOROGORO": "MOROGORO",
        "MTWARA": "MTWARA",
        "LINDI": "LINDI",
        "MWANZA": "MWANZA",
        "RUVUMA": "RUVUMA",
        "SHINYANGA": "SHINYANGA",
        "SINGIDA": "SINGIDA",
        "TABORA": "TABORA",
        "TANGA": "TANGA",
        "KAGERA": "WEST LAKE",
    }
    if year == 1972:
        common["RUKWA"] = "MBEYA"
        common["KATAVI"] = "TABORA"
    elif year == 1974:
        common["RUKWA"] = "RUKWA"
        common["KATAVI"] = "RUKWA"
    else:
        raise ValueError(year)

    work = districts[[region_col, unit_col, "geometry"]].copy()
    work["_REGION"] = work[region_col].map(norm)
    work["_UNIT"] = work[unit_col].map(norm)
    work["REGION"] = [assign_geita_simiyu(r, u, common) for r, u in zip(work["_REGION"], work["_UNIT"])]
    work = work[work["REGION"].notna()].copy()
    out = work[["REGION", "geometry"]].dissolve(by="REGION", as_index=False)
    out["REGION"] = out["REGION"].str.title().replace({"West Lake": "West Lake", "Dar Es Salaam": "Dar es Salaam"})
    out["YEAR"] = year
    out["METHOD"] = "Historical reconstruction from later district geometry and administrative lineage"
    out["QUALITY"] = "reconstructed"
    out["SOURCE"] = "Heed725/Tanzania_Admin_Shapefiles + Tanzanian region/district chronology"
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--modern-source", type=Path, required=True)
    args = parser.parse_args()

    root = args.output_root.resolve()
    work = root / ".build"
    work.mkdir(parents=True, exist_ok=True)

    src1948 = read_princeton_1948(work)
    src1950 = read_princeton_1950(work)

    # 1898, 1900, 1926, 1935: territorial-outline proxies only. We do not invent internal districts.
    outline = mainland_outline(src1950)
    proxy_titles = {
        1898: "German East Africa — Tanganyika-area outline, 1898 proxy",
        1900: "German East Africa — Tanganyika-area outline, 1900 proxy",
        1926: "British Tanganyika territorial outline, 1926 proxy",
        1935: "British Tanganyika territorial outline, 1935 proxy",
    }
    for year, title in proxy_titles.items():
        g = outline.copy()
        g["YEAR"] = year
        g["METHOD"] = "Territorial proxy using historical Tanganyika-area outline; no invented internal boundaries"
        g["QUALITY"] = "proxy"
        g["SOURCE"] = "Princeton 1950 Tanganyika historical geometry used as territorial reference"
        save_layer(
            g,
            year,
            f"Tanganyika_{year}_Territory_Proxy",
            root,
            {
                "title": title,
                "quality": "proxy",
                "note": "Territory-level proxy only; not an exact year-specific internal administrative map.",
            },
        )

    # 1948 direct historical province layer.
    province1948 = detect_col(src1948, ["Province", "PROVINCE", "NAME"])
    g1948 = src1948[[province1948, "geometry"]].rename(columns={province1948: "PROVINCE"})
    g1948["YEAR"] = 1948
    g1948["METHOD"] = "Direct historical GIS source"
    g1948["QUALITY"] = "direct-historical"
    g1948["SOURCE"] = "Princeton University Library historical boundaries, 1948"
    save_layer(
        g1948,
        1948,
        "Tanganyika_Provinces_1948",
        root,
        {"title": "Tanganyika Provinces, 1948", "quality": "direct-historical"},
    )

    # 1950 direct historical provinces and districts.
    pcol = detect_col(src1950, ["Province", "PROVINCE"])
    dcol = detect_col(src1950, ["District", "DISTRICT"])
    d1950 = src1950[[pcol, dcol, "geometry"]].rename(columns={pcol: "PROVINCE", dcol: "DISTRICT"})
    d1950["YEAR"] = 1950
    d1950["METHOD"] = "Direct historical GIS source"
    d1950["QUALITY"] = "direct-historical"
    d1950["SOURCE"] = "Princeton University Library historical boundaries, revised to May 1950"
    save_layer(
        d1950,
        1950,
        "Tanganyika_Districts_1950",
        root,
        {"title": "Tanganyika Districts, 1950", "quality": "direct-historical"},
    )
    p1950 = d1950[["PROVINCE", "geometry"]].dissolve(by="PROVINCE", as_index=False)
    p1950["YEAR"] = 1950
    p1950["METHOD"] = "Direct historical GIS source, dissolved by province"
    p1950["QUALITY"] = "direct-historical"
    p1950["SOURCE"] = "Princeton University Library historical boundaries, revised to May 1950"
    save_layer(
        p1950,
        1950,
        "Tanganyika_Provinces_1950",
        root,
        {"title": "Tanganyika Provinces, 1950", "quality": "direct-historical"},
    )

    # Late-colonial / independence reconstructions.
    for year in [1960, 1961]:
        g = lake_split_1960_61(src1950, year)
        save_layer(
            g,
            year,
            f"Tanganyika_Provinces_{year}_Reconstruction",
            root,
            {
                "title": f"Tanganyika Provinces, {year} reconstruction",
                "quality": "reconstructed-proxy",
            },
        )

    # 1963/64 are based on the known early regional arrangement, using the 1967 reconstruction as geometry proxy.
    g1967 = read_1967(work)
    for year in [1963, 1964]:
        g = g1967.copy()
        g["YEAR"] = year
        g["METHOD"] = "Early regional-system reconstruction using 1967 region geometry as proxy"
        g["QUALITY"] = "reconstructed-proxy"
        g["SOURCE"] = "1963 regional system chronology + Heed725 1967 reconstruction"
        save_layer(
            g,
            year,
            f"Tanzania_Mainland_Regions_{year}_Reconstruction",
            root,
            {
                "title": f"Mainland Regions, {year} reconstruction",
                "quality": "reconstructed-proxy",
            },
        )

    # 1967 existing reconstruction.
    g = g1967.copy()
    g["YEAR"] = 1967
    g["METHOD"] = "Historical reconstruction from later district geometry"
    g["QUALITY"] = "reconstructed"
    g["SOURCE"] = "Heed725/Tanzania-1967-Region-Shapefiles"
    save_layer(
        g,
        1967,
        "Tanzania_Mainland_Regions_1967",
        root,
        {"title": "Tanzania Mainland Regions, 1967", "quality": "reconstructed"},
    )

    # 1972 and 1974 district-based reconstructions.
    modern, region_col, unit_col = modern_districts(args.modern_source)
    for year in [1972, 1974]:
        g = reconstruct_modern_year(modern, region_col, unit_col, year)
        save_layer(
            g,
            year,
            f"Tanzania_Mainland_Regions_{year}_Reconstruction",
            root,
            {
                "title": f"Tanzania Mainland Regions, {year} reconstruction",
                "quality": "reconstructed",
            },
        )

    requested = [1898, 1900, 1926, 1935, 1948, 1950, 1960, 1961, 1963, 1964, 1967, 1972, 1974]
    missing = [y for y in requested if not (root / "data" / str(y)).exists()]
    if missing:
        raise RuntimeError(f"Missing output years: {missing}")

    index_rows = []
    for year in requested:
        meta = json.loads((root / "data" / str(year) / "metadata.json").read_text(encoding="utf-8"))
        index_rows.append(meta)
    pd.DataFrame(index_rows).to_csv(root / "data" / "collection_index.csv", index=False)

    print("Built snapshots:", ", ".join(map(str, requested)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
