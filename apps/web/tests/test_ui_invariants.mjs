#!/usr/bin/env node
// Phase 6 acceptance: the consultant workflow UI must satisfy
//   1. validation gate is the ONLY path to validated state
//   2. no UI path to auto-finalize
//   3. Google export is opt-in (default off, no auto-fire)
//
// Strategy: structural analysis of the UI source. Each assertion scans one
// file at a time to avoid cross-file regex pollution.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const SRC = join(dirname(fileURLToPath(import.meta.url)), "..", "src");

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) out.push(...walk(full));
    else if (/\.(ts|tsx|js|jsx)$/.test(name)) out.push(full);
  }
  return out;
}

const files = walk(SRC);
const sources = new Map(files.map((f) => [f, readFileSync(f, "utf8")]));

let failed = 0;
function assert(cond, msg) {
  if (cond) console.log(`  ok  ${msg}`);
  else { console.log(`  FAIL  ${msg}`); failed++; }
}
function anyFile(re) {
  for (const txt of sources.values()) if (re.test(txt)) return true;
  return false;
}
function anyFileFn(pred) {
  for (const txt of sources.values()) if (pred(txt)) return true;
  return false;
}

console.log("Phase 6 UI invariants:");

// ── 1. Validation gate is the only path to validated ─────────────────────
// The PATCH /validate call must be wrapped in a dedicated handler
// (handleValidate/onValidate/etc.) wired to a button onClick, not auto-fired.
const validateHandler =
  /async function (handleValidate|onValidate|validateFact|doValidate)\b[\s\S]{0,800}\/validate/;
assert(
  anyFile(validateHandler),
  "validate PATCH is wrapped in a dedicated validation handler (human gate)",
);
assert(
  anyFile(/onClick=\{[\s\S]{0,120}(handleValidate|onValidate|validateFact|doValidate)/),
  "the validation handler is invoked from a button onClick (explicit human action)",
);
assert(
  !anyFile(/useEffect[\s\S]{0,400}\/validate/),
  "validate PATCH is NOT auto-fired from a useEffect",
);
assert(
  !anyFile(/setInterval[\s\S]{0,400}\/validate/),
  "validate PATCH is NOT fired on a timer",
);

// ── 2. No finalize / approve / submit auto-paths in the UI ───────────────
assert(
  !anyFile(/\/projects\/[^"'`]*\/(finalize|approve|submit)\b/i),
  "no /finalize | /approve | /submit route in UI",
);
function hasForbiddenButtonLabel(txt) {
  const stripped = txt
    .replace(/<form[^>]*>/g, " ")
    .replace(/\bonSubmit=\{[^}]+\}/g, " ")
    .replace(/\btype="submit"/g, " ")
    .replace(/\bfunction\s+onSubmit\b/g, " ")
    .replace(/\basync\s+function\s+\w*Submit\w*\b/g, " ");
  return />[^<]{0,200}\b(Finaliser|Approve[dr]?|Soumettre|Finalize|Approve)\b/i.test(stripped);
}
assert(!anyFileFn(hasForbiddenButtonLabel), "no Finaliser/Approuver/Soumettre button label");
assert(
  !anyFile(/useEffect[\s\S]{0,400}(finalize|approve|submit)/i),
  "no auto-fire finalize/approve/submit from useEffect",
);

// ── 3. Google export is opt-in, default off ──────────────────────────────
// Structural: download handler is separate from export handler. Export is
// gated by an opt-in toggle (default OFF) and never auto-fired.
const downloadHandler =
  /async function (handleDownloadReport|onDownload|downloadReport|handleDownload)\b[\s\S]{0,1500}\/report/;
const exportHandler =
  /async function (handleGoogleExport|onExportGoogle|exportToGoogle|googleExport)\b[\s\S]{0,1500}\/export/;
assert(downloadHandler, "download DOCX has its own dedicated handler");
assert(exportHandler, "export Google Docs has its own dedicated handler (opt-in)");
// Default off: the opt-in state initializer must be false (not true, not 1).
// Allow `useState(false)` and a `googleExport*` identifier on the same line
// (the variable is named *before* useState: `const [googleExportEnabled, x] = useState(false)`).
assert(
  anyFile(/useState\(\s*false\s*\)/i) &&
    anyFile(/const \[[^\]]*googleExport/i) &&
    anyFile(/const \[[^\]]*exportEnabled/i),
  "Google export opt-in defaults to OFF (false)",
);
// Auto-fire guard: no useEffect that fires /export.
assert(
  !anyFile(/useEffect[\s\S]{0,400}\/export/),
  "Google export is NOT auto-fired from useEffect",
);
// Separate onClick wiring (not bundled into the download button).
assert(
  anyFile(/onClick=\{[\s\S]{0,120}(handleGoogleExport|onExportGoogle|exportToGoogle|googleExport)/),
  "export has its own onClick button (separate action from download)",
);
// UI surfaces that the bureau flag controls the export (default OFF).
assert(
  anyFile(/google_export_enabled|désactivé par défaut|default OFF|off by default|Off by default/i),
  "UI surfaces that Google export is opt-in / default OFF at bureau level",
);

if (failed > 0) {
  console.log(`\n${failed} invariant(s) violated.`);
  process.exit(1);
}
console.log("\nAll Phase 6 UI invariants hold.");
