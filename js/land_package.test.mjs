// Run with: node --test js/land_package.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { canonical, contentSha256, shareable, summarize, validate } from "./land_package.mjs";

const read = (path) => JSON.parse(readFileSync(new URL(`../${path}`, import.meta.url), "utf8"));

test("the JavaScript validator gives the Python validator's verdict on every recorded case", async () => {
  const { cases } = read("tests/fixtures/parity_cases.json");
  assert.ok(cases.length >= 25);
  for (const c of cases) {
    const { errors, warnings } = await validate(c.package);
    assert.deepEqual(errors, c.errors, c.name);
    assert.deepEqual(warnings, c.warnings, c.name);
    assert.equal(shareable(c.package), c.shareable, c.name);
  }
});

test("canonical form matches the recorded vectors and the hash matches the example", async () => {
  const vectors = read("tests/fixtures/canonical_vectors.json");
  for (const [hex, want] of vectors.numbers) {
    const value = new Float64Array(new Uint8Array(hex.match(/../g).map((b) => parseInt(b, 16))).buffer)[0];
    assert.equal(canonical(value), want);
  }
  for (const [value, want] of vectors.strings) assert.equal(canonical(value), want);
  assert.equal(canonical(vectors.object.value), vectors.object.text);
  assert.throws(() => canonical(NaN));
  const example = read("examples/example-field.json");
  assert.equal(await contentSha256(example), example.integrity.content_sha256);
});

test("summarize reports layers, claims by kind, missing data and privacy", () => {
  const s = summarize(read("examples/example-field.json"));
  assert.equal(s.layers.length, 3);
  assert.deepEqual(s.claimsByKind, { measured: 1, modelled: 1, estimated: 1, derived: 0, stated: 0 });
  assert.equal(s.notRetrieved.length, 1);
  assert.equal(s.shareable, true);
  assert.deepEqual(s.extensions, ["example"]);
});
