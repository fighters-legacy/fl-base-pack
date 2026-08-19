<!--
SPDX-FileCopyrightText: Contributors to fl-base-pack
SPDX-License-Identifier: CC-BY-4.0
-->

# Terrain data attribution

The tiles under `terrain/world/` are derived works of third-party geodata. Redistribution of this
pack must keep this attribution (both sources require it).

## Heights (`tile_*.png`)

Produced from the **Copernicus DEM GLO-30** (30 m global digital surface model):

> © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under
> COPERNICUS by the European Union and ESA; all rights reserved.

Licence: the Copernicus DEM instance COP-DEM-GLO-30 licence (free use with attribution) —
see `LICENSES/LicenseRef-Copernicus-DEM.txt` and
<https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model>.

## Land cover (`tile_*_lc.png`)

Produced from **ESA WorldCover 2021 v200** (10 m global land cover):

> © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by
> the ESA WorldCover consortium.

Licence: CC BY 4.0 — <https://esa-worldcover.org/>.

## Provenance

Built by `tools/terrain/build_nttr_theater.sh` over the theater bounds in `theaters/nttr.toml`
(35.0–38.5 N, 117.5–113.5 W), quadtree levels 6–10, with the engine's `gen_terrain_tiles.py`.
The engine's bundled coarse base (levels 0–5, GEBCO 2024) carries its own attribution in its
bundle; nothing here is derived from it.
