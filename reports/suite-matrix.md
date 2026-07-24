# PlaneKey Hash-Tensor Overlap Matrix

Generated: 2026-07-24T08:25:35.600Z
Layers: 2  Overlapping pairs: 1  Cross-layer assets: 8

Each layer is a zip (or folder source). Four overlap dimensions per pair:
`content` (exact sha256), `rgano` (structural signature — rgano style),
`paths` (filename overlap), `routes` (HTTP route overlap).

## 1. Layer inventory

| # | Layer | Files | Hashes | Rgano sigs | Paths | Routes |
|---|---|---|---|---|---|---|
| 1 | jcloudwork.zip | 404 | 395 | 391 | 404 | 0 |
| 2 | taosr.zip | 2131 | 2112 | 1765 | 2131 | 1004 |

## 2. Top overlapping pairs (rgano-structural)

| A | B | rgano | content | paths | routes | shared hashes |
|---|---|---|---|---|---|---|
| jcloudwork.zip | taosr.zip | 0.002 | 0.000 | 0.000 | 0.000 | 0 |

## 3. Cloverleaf overpass — assets crossing the most layers

| Layers carrying | Asset (sample path) | content hash |
|---|---|---|
| 1 | resources/icon.iconset/icon_128x128@2x.png | `75cd2c4d18c68314` |
| 1 | resources/icon.iconset/icon_16x16@2x.png | `f0231fbbf0a89be6` |
| 1 | resources/icon.iconset/icon_256x256@2x.png | `d1ad2694af7dc630` |
| 1 | resources/icon.iconset/icon_512x512@2x.png | `541662743bf6062c` |
| 1 | resources/logo.png | `a2f0f2e65eb78b5f` |
| 1 | resources/social-preview.png | `4caa66c1eeb2ad26` |
| 1 | tinyagentos/admin_prompts/__init__.py | `e3b0c44298fc1c14` |
| 1 | tinyagentos/scripts/install_openai-agents-sdk.sh | `8517c60bd7a2ee0e` |

## 4. Uniqueness — layers with most layer-unique assets

| Layer | Layer-unique files |
|---|---|
| taosr.zip | 2112 |
| jcloudwork.zip | 395 |
