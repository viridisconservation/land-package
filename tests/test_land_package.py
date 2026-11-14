"""Viridis Land Package v1: invariants LP1 to LP8."""
import copy, json, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import land_package as lp  # noqa: E402

FIXTURES = sorted((Path(__file__).parent / "fixtures" / "dfm").glob("*.json"))
EXAMPLE = ROOT / "examples" / "example-field.json"
SCHEMA = ROOT / "schema" / "land-package.schema.json"


def _example():
    return json.loads(EXAMPLE.read_text())


def _errors(package):
    return lp.validate(package)[0]


def _resealed(package, mutate):
    changed = copy.deepcopy(package)
    mutate(changed)
    return lp.seal(changed)


def test_the_example_is_valid_sealed_and_written_canonically():
    package = _example()
    assert lp.validate(package) == ([], [])
    assert lp.dumps(package) == EXAMPLE.read_text()          # LP8
    assert lp.seal(package) == package                        # LP5
    assert lp.shareable(package) is True


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_lp6_dfm_package_round_trips_byte_for_byte(path):
    dfm = json.loads(path.read_text())["package"]
    package = lp.from_dfm(dfm)
    assert _errors(package) == []
    assert json.dumps(lp.to_dfm(package)) == json.dumps(dfm)
    assert lp.from_dfm(dfm) == package


def test_dfm_without_recorded_sources_is_flagged_not_hidden():
    package = lp.from_dfm(json.loads(FIXTURES[0].read_text())["package"])
    errors, warnings = lp.validate(package)
    assert errors == [] and warnings and all("not recorded" in w for w in warnings)
    assert lp.UNRECORDED_SOURCE in package["sources"]


def test_dfm_parcels_make_the_package_personal_data():
    dfm = json.loads(FIXTURES[0].read_text())["package"]
    package = lp.from_dfm(dfm)
    assert package["privacy"]["personal_data"] is bool(dfm["layers"]["parcels"])
    assert lp.shareable(package) is False


def test_conversion_refuses_what_it_cannot_do_without_loss():
    dfm = json.loads(FIXTURES[0].read_text())["package"]
    with pytest.raises(lp.LandPackageError):
        lp.from_dfm({"dfm_package": "2.0"})
    with pytest.raises(lp.LandPackageError):
        lp.from_dfm(dict(dfm, crs="EPSG:3857"))
    grown = _resealed(lp.from_dfm(dfm), lambda p: p["layers"].__setitem__("soil", {"sources": [], "features": []}))
    with pytest.raises(lp.LandPackageError, match="would be lost"):
        lp.to_dfm(grown)
    with pytest.raises(lp.LandPackageError):
        lp.to_dfm(_example())


def test_lp4_shareable_is_derived_and_never_written():
    package = _example()
    assert "shareable is derived" in " ".join(_errors(_resealed(package, lambda p: p["privacy"].__setitem__("shareable", True))))
    assert lp.shareable(_resealed(package, lambda p: p["privacy"].__setitem__("personal_data", True))) is False
    assert lp.shareable(_resealed(package, lambda p: p["privacy"].__setitem__("consent", "none"))) is False


def test_lp5_the_hash_detects_any_change():
    package = _example()
    for mutate in (lambda p: p["claims"][0].__setitem__("value", 1),
                   lambda p: p["layers"]["boundary"]["features"][0]["geometry"]["coordinates"][0][1].__setitem__(0, -72.7481),
                   lambda p: p.__setitem__("name", "Other")):
        tampered = copy.deepcopy(package)
        mutate(tampered)
        assert any("LP5" in e for e in _errors(tampered))
        assert _errors(lp.seal(tampered)) == []


def test_write_and_read_round_trip_and_write_refuses_invalid(tmp_path):
    package = _example()
    path = lp.write(package, tmp_path / "p.json")
    assert lp.read(path) == package
    with pytest.raises(lp.LandPackageError):
        lp.write(dict(package, crs="EPSG:3857"), tmp_path / "bad.json")


def _set_geom(geom):
    return lambda p: p["layers"]["boundary"]["features"][0].__setitem__("geometry", geom)


MUTATIONS = [
    (lambda p: p.__setitem__("crs", "EPSG:3857"), "LP1"),
    (lambda p: p["units"].__setitem__("length", "ft"), "LP1"),
    (_set_geom({"type": "Point", "coordinates": [44.25, -172.75]}), "outside longitude and latitude"),
    (_set_geom({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]}), "not closed"),
    (_set_geom({"type": "GeometryCollection", "geometries": []}), "LP7"),
    (_set_geom({"type": "LineString", "coordinates": [[0, 0]]}), "at least 2"),
    (lambda p: p["layers"]["treeRows"].__setitem__("sources", []), "names no source"),
    (lambda p: p["layers"]["treeRows"].__setitem__("sources", ["nowhere"]), "not in sources"),
    (lambda p: p["sources"]["row-model"].pop("title"), "needs a title"),
    (lambda p: p["claims"][0].__setitem__("kind", "certified"), "LP3"),
    (lambda p: p["claims"][2].pop("method"), "source or a method"),
    (lambda p: p["claims"][2].update(kind="measured"), "measured claim must name"),
    (lambda p: p["claims"][1].pop("unit"), "needs a unit"),
    (lambda p: p["claims"][1].__setitem__("id", p["claims"][0]["id"]), "unique id"),
    (lambda p: p.pop("not_retrieved"), "missing field: not_retrieved"),
    (lambda p: p["not_retrieved"].append({"source": "Flood", "status": "ok", "consequence": "x"}), "LP3"),
    (lambda p: p["privacy"].__setitem__("consent", "assumed"), "LP4"),
    (lambda p: p["subject"].__setitem__("kind", "planet"), "subject.kind"),
    (lambda p: p.__setitem__("notes", "x"), "unknown top-level field"),
    (lambda p: p["layers"].__setitem__("bad name", {"sources": [], "features": []}), "layer name"),
]


@pytest.mark.parametrize("mutate,needle", MUTATIONS)
def test_validator_refuses(mutate, needle):
    errors = _errors(_resealed(_example(), mutate))
    assert any(needle in e for e in errors), errors


def test_lp7_unknown_layers_and_extensions_are_kept():
    package = _example()
    assert "soilSamples" in package["layers"] and "example" in package["extensions"]
    extra = _resealed(package, lambda p: p["extensions"].__setitem__("other", {"k": [1, 2]}))
    assert _errors(extra) == [] and extra["extensions"]["other"] == {"k": [1, 2]}


def test_schema_agrees_with_the_validator():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    v = jsonschema.Draft202012Validator(schema)
    assert list(v.iter_errors(_example())) == []
    for path in FIXTURES:
        assert list(v.iter_errors(lp.from_dfm(json.loads(path.read_text())["package"]))) == []
    props = schema["properties"]
    assert props["claims"]["items"]["properties"]["kind"]["enum"] == list(lp.CLAIM_KINDS)
    assert props["privacy"]["properties"]["consent"]["enum"] == list(lp.CONSENT)
    assert sorted(props) == sorted(lp._REQUIRED + lp._OPTIONAL)
    for mutate in (lambda p: p.__setitem__("crs", "EPSG:3857"), lambda p: p.pop("not_retrieved"),
                   lambda p: p["privacy"].__setitem__("shareable", True)):
        assert list(v.iter_errors(_resealed(_example(), mutate)))


def test_command_line(tmp_path, capsys):
    assert lp.main(["validate", str(EXAMPLE)]) == 0
    assert "VALID: Land Package 1.0" in capsys.readouterr().out
    out, back = tmp_path / "lp.json", tmp_path / "dfm.json"
    assert lp.main(["from-dfm", str(FIXTURES[0]), str(out)]) == 0
    assert lp.main(["to-dfm", str(out), str(back)]) == 0
    assert json.loads(back.read_text()) == json.loads(FIXTURES[0].read_text())["package"]
    broken = _example(); broken["name"] = "changed"
    out.write_text(json.dumps(broken))
    assert lp.main(["validate", str(out)]) == 1
    assert lp.main([]) == 2


def test_canonical_form_matches_javascript_on_recorded_vectors():
    import struct
    vectors = json.loads((Path(__file__).parent / "fixtures" / "canonical_vectors.json").read_text())
    for hexed, want in vectors["numbers"]:
        assert lp.canonical(struct.unpack("<d", bytes.fromhex(hexed))[0]) == want
    for value, want in vectors["strings"]:
        assert lp.canonical(value) == want
    assert lp.canonical(vectors["object"]["value"]) == vectors["object"]["text"]
    assert lp.canonical(26600.0) == "26600" == lp.canonical(26600)
    for bad in (float("nan"), float("inf"), 2 ** 60, {1: "x"}, object()):
        with pytest.raises(ValueError):
            lp.canonical(bad)


def test_recorded_parity_cases_are_current():
    """The verdicts the JavaScript validator is tested against are this validator's verdicts."""
    cases = json.loads((Path(__file__).parent / "fixtures" / "parity_cases.json").read_text())["cases"]
    assert len(cases) >= 30
    for case in cases:
        errors, warnings = lp.validate(case["package"])
        assert (errors, warnings, lp.shareable(case["package"])) == (case["errors"], case["warnings"], case["shareable"]), case["name"]
