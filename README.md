# Viridis Land Package

One file format for evidence about a piece of land, so a result from one tool can be read by
another without losing where it came from.

A Land Package is a JSON file. It holds map layers, the source of each layer, statements about
the land marked as measured, modelled, estimated, derived or stated, a list of data that could
not be retrieved, a privacy declaration, and a hash of its own content.

Format description: https://viridisconservation.com/ecosystem/land-package

## Use it

The reference implementation is one Python file with no dependencies (Python 3.9 or later).
Copy `land_package.py` into your project, or run it directly:

```
python land_package.py validate examples/example-field.json
python land_package.py from-dfm my-dfm-package.json my-land-package.json
python land_package.py to-dfm my-land-package.json my-dfm-package.json
```

In code:

```python
import land_package as lp

package = lp.read("examples/example-field.json")   # raises LandPackageError if invalid
errors, warnings = lp.validate(package)
lp.shareable(package)                               # worked out from the privacy declaration
lp.write(lp.seal(package), "out.json")              # seal() sets the content hash
```

## What a package holds

| Field | Meaning |
|---|---|
| `land_package` | Format version, `"1.0"`. |
| `name`, `created`, `generator` | What the package describes, its date, and the tool that wrote it. |
| `crs`, `units` | Always `EPSG:4326`, metres and square metres. |
| `subject` | `kind` (property, field, woodlot, landscape) and `area_m2`. |
| `privacy` | `location` (exact or generalized), `personal_data` (true or false), `consent` (holder, covered, none, not_applicable). |
| `sources` | Every dataset or method used, by id: title, url, date, license, notes. |
| `layers` | Named layers. Each has `sources` (ids) and `features` (GeoJSON Features). |
| `claims` | Statements with a `kind`. Each names a source or a method. |
| `not_retrieved` | Data the tool tried to get and could not, and what that means for the reader. Present even when empty. |
| `receipt` | Optional. Fingerprints that let a result be reproduced. |
| `extensions` | Optional. Tool-specific content, keyed by tool name. Readers keep what they do not understand. |
| `integrity` | SHA-256 of the canonical JSON of everything else. |

## Rules

- **LP1 Geometry.** GeoJSON in EPSG:4326, longitude then latitude. Out-of-range coordinates and open rings are errors.
- **LP2 Provenance.** A layer with features names at least one source that exists. A claim names a source or a method.
- **LP3 Honesty.** `not_retrieved` is always present. Claim kinds are a fixed list. A measured claim must name the source of the measurement.
- **LP4 Privacy.** The package declares location precision, personal data and consent. Whether it may be shared is worked out by the reader, never written into the file.
- **LP5 Integrity.** A package whose hash does not match its content is invalid.
- **LP6 Lossless.** A DFM Landscape Package v1 converted in and back out is identical, key order included.
- **LP7 Nothing dropped silently.** Unknown layers and extensions are preserved. An unsupported geometry type is an error.
- **LP8 Deterministic.** The same content gives the same bytes and the same hash.

`schema/land-package.schema.json` (JSON Schema 2020-12) covers structure. The cross-references
in LP2, ring closure and coordinate range in LP1, and the hash in LP5 are checked by `validate()`.

## Who uses it today

| Tool | State |
|---|---|
| Viridis land design reports | Write a Land Package with every report. |
| [Dendritic Forest Management](https://dendriticforest.com/) | Its Landscape Package v1 converts in and out without loss. The tool itself does not read or write Land Packages. |
| VergeCommon, Contour Alley Designer, Global Soil Intelligence Project, Viridis Ecological OS | Not yet. |

## Limits

- Version 1 has no raster layers and no time series.
- A package made from a DFM file that recorded no sources is valid, with a warning on every layer and the source id `unrecorded`.
- The hash shows a file has not changed since it was sealed. It does not show who made it.
- `from_arboris` builds a package from a Viridis land design model and is of use only to that tool.

## Tests

```
python -m pip install pytest jsonschema
python -m pytest -q
```

The DFM examples under `tests/fixtures/dfm/` are fictional landscapes copied unchanged from
[hdfm-framework](https://github.com/jdhart81/hdfm-framework) (MIT).

## Licence

Apache-2.0. Stewarded by Viridis LLC.
