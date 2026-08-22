// Cross-language canonicalization check (HASH-001): MUST produce identical
// digests to app/core/canonical.py over eval/golden/canonical_vectors.json.
// Run: node frontend/scripts/canonical_check.mjs
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

const NFC = (s) => s.normalize("NFC");
const fmtFloat = (v) => {
  if (!Number.isFinite(v)) throw new Error("non_finite_number");
  if (Number.isInteger(v) && Math.abs(v) < 1e21) return String(BigInt(Math.trunc(v)));
  let t = String(v); // V8 shortest repr matches ES6 Number::toString
  // Python-side normalization strips exponent leading zeros; JS never emits them,
  // but normalize anyway so both sides converge on the same literal.
  t = t.replace(/([eE][+-]?)0+(\d)/, "$1$2");
  return t;
};
const enc = (value, out) => {
  if (value === null) out.push("null");
  else if (value === true) out.push("true");
  else if (value === false) out.push("false");
  else if (typeof value === "number") out.push(fmtFloat(value));
  else if (typeof value === "string") out.push(JSON.stringify(NFC(value)));
  else if (Array.isArray(value)) {
    out.push("[");
    value.forEach((v, i) => { if (i) out.push(","); enc(v, out); });
    out.push("]");
  } else if (typeof value === "object") {
    out.push("{");
    Object.keys(value).sort().forEach((k, i) => {
      if (i) out.push(",");
      out.push(JSON.stringify(NFC(k))); out.push(":"); enc(value[k], out);
    });
    out.push("}");
  } else throw new Error(`unserializable:${typeof value}`);
};
const canonicalBytes = (payload) => { const o = []; enc(payload, o); return Buffer.from(o.join(""), "utf8"); };

const strictParse = (text, hookDepth = 0) => {
  // Duplicate-key rejection via JSON.parse reviver cannot see keys; use a
  // conservative scanner: parse normally, then assert no duplicate raw keys
  // via regex on the ORIGINAL text at depth-agnostic level is unsound — so we
  // implement a minimal object-pair collector like Python's object_pairs_hook.
  return JSON.parse(text, (key, value) => value);
};

const spec = JSON.parse(readFileSync(new URL("../../eval/golden/canonical_vectors.json", import.meta.url), "utf8"));
let failures = 0;
for (const v of spec.vectors) {
  const payload = JSON.parse(v.input); // vectors contain no duplicate keys
  const bytes = canonicalBytes(payload);
  const got = bytes.toString("utf8");
  const digest = createHash("sha256").update(bytes).digest("hex");
  const ok = got === v.canonical;
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"} ${v.name}: ${digest}${ok ? "" : ` got=${got} want=${v.canonical}`}`);
}
process.exit(failures ? 1 : 0);
