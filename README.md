# dng2jpg/d2j (0.2.0)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-GPL--3.0-491?style=flat-square" alt="License: GPL-3.0">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-6A7EC2?style=flat-square&logo=terminal&logoColor=white" alt="Platforms">
  <img src="https://img.shields.io/badge/docs-live-b31b1b" alt="Docs">
<img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
</p>

<p align="center">
<strong>Convert a DNG to a JPG with an HDR merge pipeline.</strong><br>
TODO: fill complete description.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> |
  <a href="#requirements-uv">Requirements (uv)</a> |
  <a href="#installation-uv">Installation (uv)</a> |
  <a href="#feature-highlights">Feature Highlights</a> |
  <a href="#usage">Usage</a> |
  <a href="#acknowledgments">Acknowledgments</a>
</p>

<p align="center">
<br>
🚧 <strong>DRAFT</strong>: 👾 Alpha Development 👾 - Work in Progress 🏗️ 🚧<br>
⚠️ <strong>IMPORTANT NOTICE</strong>: Created with <a href="https://github.com/Ogekuri/useReq"><strong>useReq/req</strong></a> 🤖✨ ⚠️<br>
<br>
<p>

# Feature Highlights

TODO: complete Feature Highlights


# Requirements (uv)

TODO: complete requirements


## Install with Astral uv

```bash
uv tool install dng2jpg --force --from git+https://github.com/Ogekuri/DNG2JPG.git
```

Installed CLI entrypoints:
- `dng2jpg`
- `d2j`

## Uninstall

```bash
uv tool uninstall dng2jpg
```

## Live execution with uvx

```bash
uvx --from git+https://github.com/Ogekuri/DNG2JPG.git dng2jpg --help
```

## Local execution from repository

```bash
scripts/d2j.sh --help
```

Repository launcher behavior:
- Requires `uv`.
- Must be executed from a valid Git checkout of this repository.
- Delegates to `uv run --project <repo-root> python -m dng2jpg ...`.

## Management commands

| Command | Behavior |
|---|---|
| `--help` | Prints management help first, then the full conversion help. |
| `--ver` / `--version` | Prints the installed version. |
| `--upgrade` | On Linux, runs `uv tool install dng2jpg --force --from git+https://github.com/Ogekuri/DNG2JPG.git`. On other platforms, prints the manual command instead of running it. |
| `--uninstall` | On Linux, runs `uv tool uninstall dng2jpg`. On other platforms, prints the manual command instead of running it. |

Additional observable behavior:
- Calling `dng2jpg` with no arguments prints the conversion help.
- Normal invocations perform a cached latest-release check and print only when a newer version is available or the check fails.

## Runtime contract

- **Platform**: Linux only.
- **Python**: `>=3.11`.
- **Input path**: must point to an existing `.dng` file.
- **Output path**: parent directory must already exist.
- **Value option syntax**: all value options must use `--option=value`. The separated form `--option value` is rejected.
- **Optional boolean syntax**: bare flag means `true`; explicit values accepted are `0|1|false|true|no|yes|off|on`.
- **External executable requirement**: `luminance-hdr-cli` is required only when `--hdr-merge=Luminace-HDR` is selected.
- **Metadata behavior**: when the source DNG contains EXIF metadata, the output JPG reuses it, regenerates the embedded thumbnail from the final JPG pixels, and synchronizes output file timestamps from source EXIF datetime when available.
- **Removed legacy options**: `--auto-ev=<...>` except the supported `--auto-ev-shadow-clipping`, `--auto-ev-highlight-clipping`, `--auto-ev-step`; `--auto-zero=<...>`; `--auto-zero-pct=<...>`.


# Quick Start

## Default conversion profile

When you run only:

```bash
dng2jpg input.dng output.jpg
```

the effective user-visible pipeline is:
- Exposure center: automatic.
- Exposure bracket half-span: automatic.
- RAW white-balance normalization: `MEAN`.
- Auto-brightness: disabled.
- Auto-white-balance: disabled.
- HDR backend: `OpenCV-Tonemap`.
- OpenCV-Tonemap algorithm: `reinhard`.
- Merge gamma: `auto`.
- Static postprocess defaults: `post-gamma=1`, `brightness=1`, `contrast=1`, `saturation=1`.
- Auto-levels: enabled.
- Auto-adjust: enabled.
- JPEG compression: `15`.

# Usage

## Processing pipeline overview

Ordered pipeline stages:
1. Parse CLI and validate input/output paths.
2. Read DNG metadata and detect source transfer evidence.
3. Extract one linear RAW base image with the selected RAW white-balance normalization mode.
4. Optionally run pre-merge auto-brightness.
5. Optionally run pre-merge auto-white-balance.
6. Resolve exposure center (`ev_zero`) and bracket half-span (`ev_delta`) in static or automatic mode.
7. Generate synthetic exposure brackets from the linear base image.
8. Run the selected HDR backend.
9. Apply backend-local merge gamma or tone-map handoff.
10. Run shared postprocess: static postprocess, optional auto-levels, optional auto-adjust.
11. Quantize and save the final JPG.
12. Refresh EXIF thumbnail, sync output timestamps, optionally persist debug TIFF checkpoints.

Important stage rules:
- Auto-brightness runs **before** bracket synthesis.
- Auto-white-balance runs **before** bracket synthesis.
- Standard CLI does **not** re-run auto-brightness or auto-white-balance after HDR merge.
- `OpenCV-Tonemap` consumes only the `ev_zero` frame; side brackets are not used by that backend.

## Detailed pipeline diagram

```mermaid
flowchart TD
    A[CLI invocation\ndng2jpg input.dng output.jpg [options]] --> B[Validate platform, arguments, input DNG, output directory]
    B --> C[Read EXIF and source transfer evidence]
    C --> D[Extract linear RAW base image\nRAW WB mode: GREEN | MAX | MIN | MEAN]
    D --> E{--auto-brightness}
    E -- disable --> F
    E -- enable --> E1[BT.709 luminance analysis\nscene-key classification\nReinhard auto-brightness\noptional luminance-preserving desaturation] --> F
    F --> G{--auto-white-balance}
    G -- omitted / disable --> H
    G -- Simple / GrayworldWB / IA --> G1[OpenCV xphoto gain estimation\ndomain: linear | srgb | source-auto] --> H
    G -- ColorConstancy --> G2[scikit-image color-constancy gain estimation] --> H
    G -- TTL --> G3[channel-average gray balancing] --> H
    H --> I{Exposure planning mode}
    I -- bracketing omitted + exposure omitted --> I1[auto ev_zero + auto ev_delta]
    I -- bracketing numeric + exposure omitted --> I2[auto ev_zero + static ev_delta]
    I -- bracketing auto + exposure numeric --> I3[static ev_zero + auto ev_delta]
    I -- bracketing numeric + exposure numeric --> I4[static ev_zero + static ev_delta]
    I1 --> J
    I2 --> J
    I3 --> J
    I4 --> J
    J{Backend selected}
    J -- OpenCV-Tonemap --> J1[Use ev_zero only\nIf ev_delta is auto, force 0.1 EV\nAlgorithm: drago | reinhard | mantiuk]
    J -- Luminace-HDR --> J2[Build ev_minus / ev_zero / ev_plus\nExternal luminance-hdr-cli merge + TMO]
    J -- OpenCV-Merge Debevec/Robertson --> J3[Build ev_minus / ev_zero / ev_plus\nOpenCV radiance merge\nrequires valid EXIF ExposureTime]
    J -- OpenCV-Merge Mertens --> J4[Build ev_minus / ev_zero / ev_plus\nOpenCV exposure fusion]
    J -- HDR-Plus --> J5[Build ev_minus / ev_zero / ev_plus\nHDR+ alignment + temporal/spatial merge]
    J1 --> K
    J2 --> K
    J3 --> K
    J4 --> K
    J5 --> K
    K[Merge gamma stage\n--gamma=auto or --gamma=a,b\nOpenCV-Merge optional simple tonemap\nOpenCV-Tonemap uses selected tonemap algorithm]
    K --> L[Static postprocess\npost-gamma auto or numeric\nbrightness\ncontrast\nsaturation]
    L --> M{--auto-levels}
    M -- disable --> N
    M -- enable --> M1[RawTherapee-style auto-levels\noptional highlight reconstruction\noptional out-of-gamut clipping] --> N
    N --> O{--auto-adjust}
    O -- disable --> P
    O -- enable --> O1[Selective blur\nadaptive levels\nCLAHE-luma local contrast\nsigmoidal contrast\nHSL saturation gamma\nhigh-pass overlay] --> P
    P --> Q[Clamp to display range\nJPEG quantization]
    Q --> R[Save JPG with compression level]
    R --> S[Refresh EXIF thumbnail\nSync file timestamps]
    S --> T{--debug}
    T -- disable --> U[Done]
    T -- enable --> T1[Write persistent stage TIFF checkpoints\nnext to output JPG] --> U
```

## Exposure planning modes

| `--bracketing` | `--exposure` | Effective mode | User-visible behavior |
|---|---|---|---|
| omitted | omitted | `auto ev_zero + auto ev_delta` | Full automatic planning. `ev_zero` is selected from exposure metrics; `ev_delta` is expanded iteratively until clipping thresholds are reached. |
| numeric | omitted | `auto ev_zero + static ev_delta` | The bracket half-span is fixed by the user, while the exposure center is still selected automatically. |
| `auto` | numeric | `static ev_zero + auto ev_delta` | The center EV is fixed by the user, while the bracket half-span is solved automatically. |
| numeric | numeric | `static ev_zero + static ev_delta` | Fully manual exposure planning. |

Additional rules:
- `--exposure=auto` explicitly requests automatic center selection.
- Manual `--exposure=<value>` is accepted only with `--bracketing=<value>` or explicit `--bracketing=auto`.
- Automatic center selection uses the minimum of the internally measured `ev_best`, `ev_ettr`, and `ev_detail` values.
- Automatic half-span starts from `--auto-ev-step` and expands until shadow or highlight clipping reaches the configured thresholds.
- For `OpenCV-Tonemap`, any automatic `ev_delta` request resolves to the fixed value `0.1 EV`, because side brackets are not consumed by that backend.

## Pipeline families and backend variants

| Family | Variants | Consumes | Main function from user perspective | Main algorithm family |
|---|---|---|---|---|
| `Luminace-HDR` | External tone-mapping operators such as `reinhard02`, `mantiuk08`, `drago`, `durand`, `fattal`, `ashikhmin`, others | Three synthetic brackets | Build a classic HDR image from three exposures, then tone-map it with the selected Luminance HDR operator | External `luminance-hdr-cli` merge + operator-specific tone mapping |
| `OpenCV-Merge` | `Debevec`, `Robertson`, `Mertens` | Three synthetic brackets | Merge or fuse three exposures with OpenCV | Radiance merge (`Debevec`/`Robertson`) or exposure fusion (`Mertens`) |
| `OpenCV-Tonemap` | `drago`, `reinhard`, `mantiuk` | `ev_zero` only | Tone-map a single center exposure inside OpenCV | Single-image tone mapping |
| `HDR-Plus` | one backend with proxy mode and alignment controls | Three synthetic brackets | Merge aligned frames with HDR+-style alignment and temporal/spatial accumulation | HDR+ multi-level alignment and merge |

Backend-specific notes:
- `Luminace-HDR` is the literal CLI token. It must be spelled exactly like that in commands.
- `OpenCV-Merge Debevec` and `OpenCV-Merge Robertson` require a valid source EXIF `ExposureTime`.
- `OpenCV-Merge Mertens` does not require the EXIF radiance timing path.
- `OpenCV-Tonemap` is the default backend.
- `HDR-Plus` exposes tuning knobs for scalar proxy selection, alignment search radius, and temporal weight shaping.

## CLI reference by stage

### Step 1 - Inputs and command surface

| Interface item | Meaning |
|---|---|
| `<input.dng>` | Required input DNG path. Must exist and must end with `.dng`. |
| `<output.jpg>` | Required output JPG path. Parent directory must already exist. |
| `--help` | Shows the conversion help. Top-level `dng2jpg --help` prints management help first and conversion help second. |

### Step 2 - Exposure planning and RAW bracket extraction

| Option | Meaning | Default / constraints |
|---|---|---|
| `--bracketing=<value>` | Selects the EV bracket half-span. Use `auto` for automatic solving, or a finite numeric value `>= 0` for a fixed symmetric bracket. | Omitted = automatic half-span solving. |
| `--exposure=<value>` | Selects the EV bracket center. Use `auto` for automatic center selection, or a finite numeric value for a fixed center EV. | Omitted = `auto`. Manual value is accepted only with `--bracketing=<value>` or explicit `--bracketing=auto`. |
| `--auto-ev-shadow-clipping=<0..100>` | Shadow clipping stop threshold for automatic half-span expansion. | Default: `20`. |
| `--auto-ev-highlight-clipping=<0..100>` | Highlight clipping stop threshold for automatic half-span expansion. | Default: `20`. |
| `--auto-ev-step=<value>` | Positive EV increment used during automatic half-span expansion. | Default: `0.1`. |
| `--white-balance=<GREEN\|MAX\|MIN\|MEAN>` | RAW camera white-balance normalization mode applied during linear base extraction, before any bracket arithmetic. | Allowed: `GREEN`, `MAX`, `MIN`, `MEAN`. Default: `MEAN`. |

### Step 3 - Optional white-balance stage and HDR backend selection

#### 3.1 Pre-merge white-balance stage

| Option | Meaning | Default / constraints |
|---|---|---|
| `--auto-white-balance=<mode>` | Optional pre-merge white-balance stage executed after auto-brightness and before bracket synthesis. | Allowed: `Simple`, `GrayworldWB`, `IA`, `ColorConstancy`, `TTL`, `disable`. Omitted = disabled. |
| `--white-balance-xphoto-domain=<domain>` | Estimation-domain selector used only by OpenCV xphoto white-balance modes. | Allowed: `linear`, `srgb`, `source-auto`. Default: `linear`. |

Mode meaning:
- `Simple`: OpenCV xphoto simple white-balance estimation.
- `GrayworldWB`: OpenCV xphoto gray-world estimation.
- `IA`: OpenCV xphoto IA estimation.
- `ColorConstancy`: scikit-image based color-constancy gain estimation.
- `TTL`: channel-average gray balancing.
- `disable`: explicit stage bypass.

Domain meaning for xphoto modes:
- `linear`: estimate gains from the linear EV0 image.
- `srgb`: estimate gains from an sRGB-transformed EV0 view.
- `source-auto`: choose `linear` or `srgb` from detected source transfer evidence.

#### 3.2 HDR backend selector and merge gamma

| Option | Meaning | Default / constraints |
|---|---|---|
| `--hdr-merge=<Luminace-HDR\|OpenCV-Merge\|OpenCV-Tonemap\|HDR-Plus>` | Selects the HDR backend. | Default: `OpenCV-Tonemap`. |
| `--gamma=<auto\|a,b>` | Selects the merge-output transfer stage for `OpenCV-Merge`, `OpenCV-Tonemap`, and `HDR-Plus`. | Default: `auto`. `auto` resolves from RAW/DNG metadata; `a,b` is a custom Rec.709-style transfer pair. |

#### 3.3 `OpenCV-Merge` backend

| Option | Meaning | Default / constraints |
|---|---|---|
| `--opencv-merge-algorithm=<name>` | Selects the OpenCV merge algorithm. | Allowed: `Debevec`, `Robertson`, `Mertens`. Default: `Debevec`. |
| `--opencv-merge-tonemap=<bool>` | Enables simple OpenCV gamma tone mapping on the OpenCV merge result. | Default: `true`. |
| `--opencv-merge-tonemap-gamma=<value>` | Positive gamma used by the simple OpenCV tone mapper when enabled. | Default by algorithm: `Debevec=1`, `Robertson=0.9`, `Mertens=0.8`. |

Algorithm meaning:
- `Debevec`: HDR radiance merge. Requires high-precision radiance support and valid source EXIF `ExposureTime`.
- `Robertson`: iterative HDR radiance merge. Requires high-precision radiance support and valid source EXIF `ExposureTime`.
- `Mertens`: exposure fusion. Does not use the radiance timing path.

#### 3.4 `OpenCV-Tonemap` backend

| Option | Meaning | Default / constraints |
|---|---|---|
| `--opencv-tonemap-algorithm=<drago\|reinhard\|mantiuk>` | Selects the OpenCV tone-mapping operator for `OpenCV-Tonemap`. | Default: `reinhard`. |
| `--opencv-tonemap-drago-saturation=<value>` | Drago saturation parameter. | Effective only with `--opencv-tonemap-algorithm=drago`. Default: `1`. |
| `--opencv-tonemap-drago-bias=<0..1>` | Drago bias parameter. | Effective only with `drago`. Default: `0.85`. |
| `--opencv-tonemap-reinhard-intensity=<value>` | Reinhard intensity parameter. | Effective only with `reinhard`. Default: `0`. |
| `--opencv-tonemap-reinhard-light_adapt=<0..1>` | Reinhard light adaptation parameter. | Effective only with `reinhard`. Default: `0`. |
| `--opencv-tonemap-reinhard-color_adapt=<0..1>` | Reinhard color adaptation parameter. | Effective only with `reinhard`. Default: `0`. |
| `--opencv-tonemap-mantiuk-scale=<value>` | Mantiuk scale parameter. | Effective only with `mantiuk`. Default: `0.7`. |
| `--opencv-tonemap-mantiuk-saturation=<value>` | Mantiuk saturation parameter. | Effective only with `mantiuk`. Default: `1`. |

Algorithm meaning:
- `drago`: smooth logarithmic-style compression for large dynamic range.
- `reinhard`: restrained photographic operator and the default path.
- `mantiuk`: stronger local contrast / punchier display rendering.

#### 3.5 `HDR-Plus` backend

| Option | Meaning | Default / constraints |
|---|---|---|
| `--hdrplus-proxy-mode=<name>` | Selects the scalar proxy used by HDR+ alignment and merge. | Allowed: `rggb`, `bt709`, `mean`. Default: `rggb`. |
| `--hdrplus-search-radius=<value>` | Per-layer alignment search radius. | Integer `> 0`. Default: `4`. |
| `--hdrplus-temporal-factor=<value>` | Temporal inverse-distance stretch factor. | `> 0`. Default: `8`. |
| `--hdrplus-temporal-min-dist=<value>` | Temporal weight floor. | `>= 0`. Default: `10`. |
| `--hdrplus-temporal-max-dist=<value>` | Temporal cutoff threshold. | Must be `> --hdrplus-temporal-min-dist`. Default: `300`. |

Proxy mode meaning:
- `rggb`: Bayer-energy style scalar proxy.
- `bt709`: luminance-weighted scalar proxy.
- `mean`: simple RGB average proxy.

#### 3.6 `Luminace-HDR` backend

| Option | Meaning | Default / constraints |
|---|---|---|
| `--luminance-hdr-model=<name>` | Merge model text forwarded to `luminance-hdr-cli`. | Default: `debevec`. |
| `--luminance-hdr-weight=<name>` | Weighting function text forwarded to `luminance-hdr-cli`. | Default: `flat`. |
| `--luminance-hdr-response-curve=<name>` | Response-curve selector under the repository linear contract. | Only accepted value: `linear`. |
| `--luminance-tmo=<name>` | Luminance HDR tone-mapping operator. | Default: `mantiuk08`. |
| `--tmo*=<value>` | Forwards explicit `luminance-hdr-cli --tmo*` parameters unchanged. | Effective only with `Luminace-HDR`. |

Luminance operators:

| Operator | Family / idea | Character / typical result | When to use |
|---|---|---|---|
| `ashikhmin` | Local HVS-inspired tone mapping | Natural local contrast, detail-preserving | Natural-looking local adaptation with preserved detail |
| `drago` | Adaptive logarithmic compression | Smooth, simple, highlight-friendly | Fast global compression of very wide dynamic range |
| `durand` | Bilateral base/detail decomposition | Soft local compression, photographic look | Controlled local contrast compression |
| `fattal` | Gradient-domain compression | Strong detail enhancement, dramatic HDR | Detail-heavy, stylized rendering |
| `ferradans` | Perception-inspired adaptation + local contrast | Realistic but locally adaptive | Perceptual rendering with local contrast recovery |
| `ferwerda` | Perceptually based visibility / adaptation | Vision-model oriented, scene-visibility focused | Research / perceptual-visibility oriented rendering |
| `kimkautz` | Consistent global tone reproduction | Stable, consistent, restrained | Consistent results across different HDR images |
| `pattanaik` | Human visual system adaptation model | Perceptual, adaptive, scene-aware | HVS-inspired tone mapping with rod/cone adaptation |
| `reinhard02` | Photographic tone reproduction | Natural, controllable, predictable | Best baseline when you want a relatively neutral operator |
| `reinhard05` | Visual adaptation / photoreceptor model | Natural but more adaptive than `reinhard02` | Simple controls with a perceptual / natural look |
| `mai` | Fast effective tone mapping | Clean, practical, generally easy to use | Quick all-purpose rendering with minimal tuning |
| `mantiuk06` | Contrast mapping with detail enhancement | Punchy, detailed, classic HDR look | Strong detail and local contrast enhancement |
| `mantiuk08` | Display-adaptive contrast mapping | Perceptual, display-oriented, refined | Optimizing HDR for display appearance |
| `vanhateren` | Retina-inspired visual adaptation | Vision-model based, adaptive | Retina-style perceptual adaptation experiments |
| `lischinski` | Optimization-based local tonal adjustment | Local, edge-aware, selective adjustments | Local tonal manipulation with strong edge preservation |

Luminance operator main CLI controls:

| Operator | Main CLI controls |
|---|---|
| `ashikhmin` | `--tmoAshEq2`, `--tmoAshSimple`, `--tmoAshLocal` |
| `drago` | `--tmoDrgBias` |
| `durand` | `--tmoDurSigmaS`, `--tmoDurSigmaR`, `--tmoDurBase` |
| `fattal` | `--tmoFatAlpha`, `--tmoFatBeta`, `--tmoFatColor`, `--tmoFatNoise`, `--tmoFatNew` |
| `ferradans` | `--tmoFerRho`, `--tmoFerInvAlpha` |
| `kimkautz` | `--tmoKimKautzC1`, `--tmoKimKautzC2` |
| `pattanaik` | `--tmoPatMultiplier`, `--tmoPatLocal`, `--tmoPatAutoLum`, `--tmoPatCone`, `--tmoPatRod` |
| `reinhard02` | `--tmoR02Key`, `--tmoR02Phi`, `--tmoR02Scales`, `--tmoR02Num`, `--tmoR02Low`, `--tmoR02High` |
| `reinhard05` | `--tmoR05Brightness`, `--tmoR05Chroma`, `--tmoR05Lightness` |
| `mantiuk06` | `--tmoM06Contrast`, `--tmoM06Saturation`, `--tmoM06Detail`, `--tmoM06ContrastEqual` |
| `mantiuk08` | `--tmoM08ColorSaturation`, `--tmoM08ConstrastEnh`, `--tmoM08LuminanceLvl`, `--tmoM08SetLuminance` |
| `vanhateren` | `--tmoVanHaterenPupilArea` |
| `lischinski` | `--tmoLischinskiAlpha` |

### Step 4 - Auto-brightness stage

| Option | Meaning | Default / constraints |
|---|---|---|
| `--auto-brightness=<enable\|disable>` | Enables or disables the pre-merge auto-brightness stage. | Default: `disable`. |
| `--ab-key-value=<value>` | Manual Reinhard key value `a`. | Must be `> 0`. Omit for automatic key selection. |
| `--ab-white-point-pct=<(0,100)>` | Percentile used for robust white-point compression. | Default: `99.8`. |
| `--ab-key-min=<value>` | Minimum automatic key clamp. | `> 0`. Default: `0.045`. |
| `--ab-key-max=<value>` | Maximum automatic key clamp. | `> 0`. Default: `0.72`. |
| `--ab-max-auto-boost=<value>` | Automatic key adaptation factor. | `> 0`. Default: `1.25`. |
| `--ab-enable-luminance-preserving-desat[=<bool>]` | Enables luminance-preserving anti-clipping desaturation. | Default: `true`. Bare flag means `true`. |
| `--ab-eps=<value>` | Positive numerical guard for logarithms and divisions. | Default: `1e-06`. |

User-facing effect:
- Useful when the linear RAW base is globally too dark or too bright before HDR merge.
- The stage is camera-linear and happens before any bracket generation.
- It is not repeated after HDR merge.

### Step 5 - Static postprocess stage

| Option | Meaning | Default / constraints |
|---|---|---|
| `--post-gamma=<value\|auto>` | Selects postprocess gamma behavior. | Positive float = numeric gamma. `auto` = dedicated auto-gamma stage replacing numeric gamma/brightness/contrast/saturation. |
| `--post-gamma-auto-target-gray=<value>` | Auto-gamma gray target. | Effective only when `--post-gamma=auto`. Range `(0,1)`. Default: `0.5`. |
| `--post-gamma-auto-luma-min=<value>` | Auto-gamma lower luminance guard. | Effective only when `--post-gamma=auto`. Range `(0,1)`. Default: `0.01`. |
| `--post-gamma-auto-luma-max=<value>` | Auto-gamma upper luminance guard. | Effective only when `--post-gamma=auto`. Range `(0,1)`. Default: `0.99`. |
| `--post-gamma-auto-lut-size=<value>` | Auto-gamma LUT size. | Effective only when `--post-gamma=auto`. Integer `>= 2`. Default: `256`. |
| `--brightness=<value>` | Postprocess brightness factor. | Positive float. Omitted = backend-specific default. |
| `--contrast=<value>` | Postprocess contrast factor. | Positive float. Omitted = backend-specific default. |
| `--saturation=<value>` | Postprocess saturation factor. | Positive float. Omitted = backend-specific default. |

Static postprocess defaults when omitted:

| Backend | Variant | `post-gamma / brightness / contrast / saturation` |
|---|---|---|
| `Luminace-HDR` | generic | `1 / 1 / 1 / 1` |
| `Luminace-HDR` | `reinhard02` | `0.9 / 1.3 / 0.9 / 0.7` |
| `Luminace-HDR` | `mantiuk08` | `0.9 / 0.8 / 1.2 / 1.05` |
| `OpenCV-Merge` | `Debevec` | `1 / 1.2 / 1.5 / 1` |
| `OpenCV-Merge` | `Robertson` | `1 / 1.4 / 1.4 / 1` |
| `OpenCV-Merge` | `Mertens` | `1 / 0.9 / 1.4 / 1.1` |
| `OpenCV-Tonemap` | `drago` | `1 / 1 / 1.4 / 1` |
| `OpenCV-Tonemap` | `reinhard` | `1 / 1 / 1 / 1` |
| `OpenCV-Tonemap` | `mantiuk` | `0.9 / 1 / 1.3 / 1` |
| `HDR-Plus` | generic | `0.9 / 0.9 / 1.2 / 1` |

### Step 6 - Auto-levels stage

| Option | Meaning | Default / constraints |
|---|---|---|
| `--auto-levels=<enable\|disable>` | Enables or disables auto-levels after static postprocess. | Default: `enable`. |
| `--al-clip-pct=<value>` | Histogram clipping percentage. | `>= 0`. Default: `0.02`. |
| `--al-clip-out-of-gamut[=<bool>]` | Normalizes overflowing RGB triplets after auto-levels tonal mapping and optional highlight reconstruction. | Default: `true`. Bare flag means `true`. |
| `--al-highlight-reconstruction[=<bool>]` | Enables highlight reconstruction after the auto-levels tonal transform. | Default: `false`. Bare flag means `true`. |
| `--al-highlight-reconstruction-method=<name>` | Selects the highlight reconstruction method. | Allowed: `Luminance Recovery`, `CIELab Blending`, `Blend`, `Color Propagation`, `Inpaint Opposed`. Default when omitted: `Inpaint Opposed`. |
| `--al-gain-threshold=<value>` | Gain threshold used by `Inpaint Opposed`. | `> 0`. Default: `1`. |

User-facing effect:
- This stage is enabled by default.
- It is the main automatic global tonal normalization stage after static postprocess.
- Highlight reconstruction is optional and off by default.

### Step 7 - Auto-adjust stage

| Option | Meaning | Default / constraints |
|---|---|---|
| `--auto-adjust=<enable\|disable>` | Enables or disables the final auto-adjust stage. | Default: `enable`. |
| `--aa-blur-sigma=<value>` | Selective blur sigma. | `> 0`. Default: `0.9`. |
| `--aa-blur-threshold-pct=<0..100>` | Selective blur threshold percentile. | Default: `5`. |
| `--aa-level-low-pct=<0..100>` | Low percentile for adaptive levels. | Must stay `< --aa-level-high-pct`. Default: `0.1`. |
| `--aa-level-high-pct=<0..100>` | High percentile for adaptive levels. | Must stay `> --aa-level-low-pct`. Default: `99.9`. |
| `--aa-enable-local-contrast[=<bool>]` | Enables CLAHE-luma local contrast. | Default: `true`. Bare flag means `true`. |
| `--aa-local-contrast-strength=<0..1>` | Blend factor for CLAHE-luma local contrast. | Default: `0.2`. |
| `--aa-clahe-clip-limit=<value>` | CLAHE clip limit. | `> 0`. Default: `1.6`. |
| `--aa-clahe-tile-grid-size=<rows>x<cols>` | CLAHE tile grid size. | Both dimensions `>= 1`. Default: `8x8`. |
| `--aa-sigmoid-contrast=<value>` | Sigmoidal contrast slope. | `> 0`. Default: `1.8`. |
| `--aa-sigmoid-midpoint=<0..1>` | Sigmoidal midpoint. | Default: `0.5`. |
| `--aa-saturation-gamma=<value>` | HSL saturation gamma denominator. | `> 0`. Default: `0.8`. |
| `--aa-highpass-blur-sigma=<value>` | High-pass blur sigma. | `> 0`. Default: `2`. |

User-facing effect:
- This stage is enabled by default.
- It is the final image-enhancement stage before JPEG quantization.
- It combines local contrast, contrast shaping, saturation shaping, and detail enhancement.

### Step 8 - Final JPEG, EXIF refresh, and debug artifacts

| Option | Meaning | Default / constraints |
|---|---|---|
| `--jpg-compression=<0..100>` | JPEG compression level for final save. | Default: `15`. |
| `--debug` | Persists TIFF16 checkpoints for executed float stages in the output JPG directory. | Does not change the final JPG destination. |
| `[platform]` | Runtime availability note. | Conversion command is available on Linux only. |

Debug artifact behavior:
- Files are written next to the final JPG.
- The filename prefix is the input DNG stem.
- Stage suffixes identify the pipeline checkpoint, for example bracket images, auto-brightness, auto-white-balance, HDR merge, static postprocess, auto-levels, and auto-adjust substages.

## Representative command examples

### Default pipeline

```bash
dng2jpg input.dng output.jpg
```

### Fully manual exposure center and half-span

```bash
dng2jpg input.dng output.jpg \
  --bracketing=1.5 \
  --exposure=0.0
```

### Automatic half-span around a fixed center EV

```bash
dng2jpg input.dng output.jpg \
  --bracketing=auto \
  --exposure=-0.5
```

### Pre-merge auto-brightness + auto-white-balance

```bash
dng2jpg input.dng output.jpg \
  --auto-brightness=enable \
  --auto-white-balance=GrayworldWB \
  --white-balance-xphoto-domain=linear
```

### `OpenCV-Merge` with Mertens exposure fusion

```bash
dng2jpg input.dng output.jpg \
  --hdr-merge=OpenCV-Merge \
  --opencv-merge-algorithm=Mertens
```

### `OpenCV-Tonemap` with Drago

```bash
dng2jpg input.dng output.jpg \
  --hdr-merge=OpenCV-Tonemap \
  --opencv-tonemap-algorithm=drago \
  --opencv-tonemap-drago-bias=0.9
```

### `Luminace-HDR` with `reinhard02`

```bash
dng2jpg input.dng output.jpg \
  --hdr-merge=Luminace-HDR \
  --luminance-tmo=reinhard02
```

### `HDR-Plus`

```bash
dng2jpg input.dng output.jpg \
  --hdr-merge=HDR-Plus \
  --hdrplus-proxy-mode=bt709
```

### Disable default post-merge auto stages

```bash
dng2jpg input.dng output.jpg \
  --auto-levels=disable \
  --auto-adjust=disable
```

### Persist debug checkpoints

```bash
dng2jpg input.dng output.jpg --debug
```

## `scripts/test_all_pipeline.sh` reference matrix

Purpose:
- Runs a fixed matrix of representative pipelines for one input DNG.
- Writes each result next to the input file with suffix `__<pipeline-suffix>.jpg`.
- Stops on the first failing case.

Usage:

```bash
scripts/test_all_pipeline.sh input.dng
```

Built-in cases:

| Output suffix | Equivalent options |
|---|---|
| `luminace-hdr-reinhard02` | `--hdr-merge=Luminace-HDR --luminance-tmo=reinhard02` |
| `luminace-hdr-mantiuk08` | `--hdr-merge=Luminace-HDR --luminance-tmo=mantiuk08` |
| `opencv-merge-debevec` | `--hdr-merge=OpenCV-Merge --opencv-merge-algorithm=Debevec` |
| `opencv-merge-robertson` | `--hdr-merge=OpenCV-Merge --opencv-merge-algorithm=Robertson` |
| `opencv-merge-mertens` | `--hdr-merge=OpenCV-Merge --opencv-merge-algorithm=Mertens` |
| `opencv-tonemap-drago` | `--hdr-merge=OpenCV-Tonemap --opencv-tonemap-algorithm=drago` |
| `opencv-tonemap-reinhard` | `--hdr-merge=OpenCV-Tonemap --opencv-tonemap-algorithm=reinhard` |
| `opencv-tonemap-mantiuk` | `--hdr-merge=OpenCV-Tonemap --opencv-tonemap-algorithm=mantiuk` |
| `hdr-plus` | `--hdr-merge=HDR-Plus` |
| `default-opencv-tonemap-reinhard` | no extra options; equivalent to the default pipeline |
| `auto-brightness` | `--auto-brightness=enable` |
| `auto-white-balance-Simple` | `--auto-white-balance=Simple` |
| `auto-white-balance-GrayworldWB` | `--auto-white-balance=GrayworldWB` |
| `auto-white-balance-IA` | `--auto-white-balance=IA` |
| `auto-white-balance-ColorConstancy` | `--auto-white-balance=ColorConstancy` |
| `auto-white-balance-TTL` | `--auto-white-balance=TTL` |
| `auto-levels` | `--auto-levels=enable` |
| `auto-adjust` | `--auto-adjust=enable` |

## Acknowledgements

This project directly benefits from the ideas, APIs, and reference implementations provided by:
- **HDR+** authors and contributors: <https://github.com/timothybrooks/hdr-plus/>
- **RawTherapee** authors and contributors: <https://github.com/RawTherapee/RawTherapee>
- **OpenCV** authors and contributors: <https://github.com/opencv/opencv>

## Appendix - Algorithm summary by step

### A. Exposure planning and bracket extraction

- **Automatic center EV**: evaluates multiple exposure heuristics and selects the minimum of `ev_best`, `ev_ettr`, and `ev_detail`.
- **Automatic half-span EV**: expands the bracket symmetrically in `--auto-ev-step` increments until shadow or highlight clipping reaches the configured thresholds.
- **OpenCV-Tonemap special case**: automatic half-span is reduced to a fixed `0.1 EV` because only the center frame is consumed.
- **Bracket generation**: synthetic `ev_minus`, `ev_zero`, `ev_plus` images are derived from one linear RAW base image.

### B. RAW normalization and pre-merge stages

- **RAW extraction**: neutral linear extraction through `rawpy`.
- **RAW white-balance normalization**: one of `GREEN`, `MAX`, `MIN`, `MEAN` is applied to the camera white-balance coefficients.
- **Auto-brightness**: BT.709 luminance analysis, scene-key classification, safeguarded global Reinhard tone mapping, optional luminance-preserving desaturation.
- **Auto-white-balance**:
  - `Simple`, `GrayworldWB`, `IA`: OpenCV xphoto estimation.
  - `ColorConstancy`: scikit-image based color-constancy gains.
  - `TTL`: channel-average gray balancing.

### C. HDR merge backends

- **Luminace-HDR**: external HDR merge followed by a selected tone-mapping operator from the Luminance HDR toolchain.
- **OpenCV-Merge Debevec**: radiance merge from three exposure brackets.
- **OpenCV-Merge Robertson**: iterative radiance merge from three exposure brackets.
- **OpenCV-Merge Mertens**: exposure fusion instead of radiance reconstruction.
- **OpenCV-Tonemap Drago / Reinhard / Mantiuk**: single-image tone mapping of the center frame.
- **HDR-Plus**: scalar proxy generation, multi-level alignment, temporal weighting, temporal merge, spatial merge.

### D. Post-merge processing

- **Merge gamma**: automatic metadata-driven transfer or custom `a,b` transfer pair.
- **Static postprocess**:
  - numeric mode: `gamma -> brightness -> contrast -> saturation`
  - auto mode: dedicated auto-gamma stage replacing the numeric static controls
- **Auto-levels**: RawTherapee-style histogram-driven tonal normalization with optional highlight reconstruction and optional out-of-gamut clipping.
- **Highlight reconstruction methods**: `Luminance Recovery`, `CIELab Blending`, `Blend`, `Color Propagation`, `Inpaint Opposed`.
- **Auto-adjust**: selective blur, adaptive levels, CLAHE-luma local contrast, sigmoidal contrast, HSL saturation gamma, high-pass overlay.

### E. Output stage

- **Final save**: clamp to display range, quantize to JPEG, map `--jpg-compression` to JPEG quality.
- **Metadata output**: copy source EXIF when present, regenerate the embedded thumbnail from the final JPG pixels, preserve orientation metadata, and sync output timestamps from source EXIF datetime when available.
- **Debug output**: optional persistent TIFF16 checkpoints for executed stages.

# Acknowledgments

TODO: completare