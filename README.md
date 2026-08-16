# Tanganyika / Tanzania Historical Shapefile Collection

A reproducible historical GIS collection for selected administrative snapshots of the territory that became Tanganyika and later mainland Tanzania.

## Included snapshots

| Snapshot | Administrative context | Build status / method |
|---|---|---|
| 1898 | German East Africa — Tanganyika-area territorial outline | historical-territory approximation |
| 1900 | German East Africa — Tanganyika-area territorial outline | historical-territory approximation |
| 1926 | British Tanganyika | territorial outline; district chronology documented |
| 1935 | British Tanganyika | territorial outline; district chronology documented |
| 1948 | Tanganyika provinces | **direct historical GIS source** from Princeton University Library |
| 1950 | Tanganyika provinces + districts | **direct historical GIS source** from Princeton University Library |
| 1960 | late-colonial Tanganyika | reconstruction/proxy based on the 1950 historical district geometry |
| 1961 | Tanganyika at independence | reconstruction/proxy based on late-colonial historical district geometry |
| 1963 | early post-independence regions | reconstruction based on the 1963 regional system |
| 1964 | Union-era mainland regions | reconstruction based on the early regional system |
| 1967 | mainland Tanzania regions | imported from `Heed725/Tanzania-1967-Region-Shapefiles` |
| 1972 | mainland Tanzania regional snapshot | reconstructed from historical parentage and modern source boundaries |
| 1974 | mainland Tanzania regional snapshot incl. Rukwa | reconstructed from historical parentage and modern source boundaries |

> **Accuracy note:** 1948 and 1950 are direct historical GIS datasets. The other years are either historical reconstructions or territorial proxies, and every generated layer contains `METHOD`, `QUALITY`, and `SOURCE` fields so it is not mistaken for an official survey boundary.

## Output formats

Every build writes as many of the following as apply:

- ESRI Shapefile (`.shp/.shx/.dbf/.prj/.cpg`) packaged as ZIP
- GeoJSON
- GeoPackage (`.gpkg`)
- preview PNG
- per-snapshot metadata JSON

Outputs are placed under:

```text
data/<year>/
dist/
docs/previews/
```

## Quick use in QGIS

Download the ZIP for the year you need from **Releases**, extract it, and add the `.shp` using **Layer → Add Layer → Add Vector Layer**. GeoPackage is recommended when available because it avoids Shapefile field-name limits.

## Historical source hierarchy

### Direct historical GIS sources

**1948** — Princeton University Library / NYU Spatial Data Repository, *Tanzania conflated historical administrative boundaries, 1948*. This is a historical province layer produced by conflating modern geometry with a scanned British Colonial Office map.

**1950** — Princeton University Library / NYU Spatial Data Repository, *Tanzania extracted historical administrative boundaries, 1950*. It contains province and district polygons extracted from a British Colonial Office map whose administrative boundaries were revised to May 1950.

These Princeton datasets are licensed **CC BY-NC-SA 4.0**. Derived outputs in this repository that depend on those datasets must preserve attribution and the same non-commercial share-alike conditions.

### Legal / archival chronology

The Tanzanian Regions and Districts legislation records district proclamations beginning in **1926**, with further changes through 1935, 1959, 1961, 1963, 1972, 1973 and 1974. The Establishment of Regions Proclamation states that the regional system took effect on **15 October 1963**, with amendments in 1964, 1971 and 1974.

The National Archives of Tanzania also preserves German administration records (1890–1918), Tanganyika Secretariat records (1919–1960), and provincial/district administrative archives. These are the correct primary archival sources for improving the proxy years in future digitization work.

## Important interpretation rules

- `QUALITY=direct-historical` means geometry comes from a historical GIS source.
- `QUALITY=reconstructed` means a historical boundary was rebuilt from later GIS geometry and documented administrative lineage.
- `QUALITY=proxy` means the layer is useful for historical visualization but should **not** be treated as an exact cadastral or survey reconstruction.
- `1898` and `1900` in this collection refer to the **Tanganyika-area component** of German East Africa, not a full German East Africa empire layer including Rwanda and Burundi.

## Repository structure

```text
Tanganyika-Shapefile-Collection/
├── .github/workflows/build-historical-collection.yml
├── scripts/build_collection.py
├── metadata/snapshots.csv
├── requirements.txt
├── .pre-commit-config.yaml
├── data/                  # generated
├── dist/                  # generated release packages
├── docs/previews/         # generated preview maps
└── README.md
```

## Run locally

```bash
python -m pip install -r requirements.txt
python scripts/build_collection.py
```

The GitHub Actions workflow performs the full build automatically, validates every requested year, packages the results and publishes/updates the `historical-boundaries` GitHub Release.

## Requested time series

```text
1898 → 1900 → 1926 → 1935 → 1948 → 1950 → 1960 → 1961 → 1963 → 1964 → 1967 → 1972 → 1974
```

This collection is intended to improve over time as exact year-specific scanned maps and archival boundary descriptions are digitized.
