#!/usr/bin/env node
// Phase 6 acceptance: the consultant workflow UI must satisfy
//   1. validation gate is the ONLY path to validated state
//   2. no UI path to auto-finalize
//   3. Google export is opt-in (default off, no auto-fire)
//
// Strategy: structural analysis of the UI source. Each assertion scans one
// file at a time to avoid cross-file regex pollution (e.g. an `</main>` `>`
// in one file spanning into `onSubmit` text in the next).

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
  if (cond) {
    console.log(`  ok  ${msg}`);
  } else {
    console.log(`  FAIL  ${msg}`);
    failed++;
  }
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
assert(
  anyFile(/async function onValidate[\s\S]{0,500}\/validate/),
  "validate PATCH is wrapped in a dedicated onValidate handler (human gate)",
);
assert(
  anyFile(/onClick=\{[\s\S]{0,80}onValidate/),
  "the onValidate handler is invoked from a button onClick (explicit human action)",
);
assert(
  !anyFile(/useEffect[\s\S]{0,400}\/validate/),
  "validate PATCH is NOT auto-fired from a useEffect",
);
assert(
  !anyFile(/setInterval[\s\S]{0,400}\/validate/),
  "validate PATCH is NOT fired on a timer",
);
assert(anyFile(/reviewer_note/), "validate call carries the consultant's reviewer_note (UI trust boundary)");

// ── 2. No finalize / approve / submit auto-paths in the UI ───────────────
assert(
  !anyFile(/\/projects\/[^"'`]*\/(finalize|approve|submit)\b/i),
  "no /finalize | /approve | /submit route in UI",
);
// Forbidden button labels. Strip JSX attributes (`onSubmit=`, `type="submit"`,
// `onSubmit={handler}`) and identifier names before scanning for label text.
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
assert(
  anyFile(/async function onDownload[\s\S]{0,800}downloadFile[\s\S]{0,400}\/report/),
  "download DOCX has its own onDownload handler",
);
assert(
  anyFile(/async function onExportGoogle[\s\S]{0,500}\/export/),
  "export Google Docs has its own onExportGoogle handler (opt-in)",
);
// Bound the onDownload body to its own function — extract via balanced-brace
// approximation: from `async function onDownload(` to the next top-level `\n  }`
// at column 2.
function bodyOf(name) {
  for (const txt of sources.values()) {
    const re = new RegExp(
      "async function " + name + "\\([^)]*\\)\\s*\\{([\\s\\S]*?)\\n  \\}",
    );
    const m = txt.match(re);
    if (m) return m[1];
  }
  return "";
}
const downloadBody = bodyOf("onDownload");
assert(
  downloadBody.length > 0 && !/\/export/.test(downloadBody),
  "export is NOT bundled into the download handler",
);
assert(
  anyFile(/onClick=\{[\s\S]{0,80}onDownload/) &&
    anyFile(/onClick=\{[\s\S]{0,80}onExportGoogle/),
  "download and export each have their own onClick button (separate actions)",
);
assert(
  anyFile(/google_export_enabled|désactivé par défaut|default OFF/i),
  "UI surfaces that Google export is opt-in / default OFF at bureau level",
);
assert(
  !anyFile(/useEffect[\s\S]{0,400}\/export/),
  "Google export is NOT auto-fired from useEffect",
);

if (failed > 0) {
  console.log(`\n${failed} invariant(s) violated.`);
  process.exit(1);
}
console.log("\nAll Phase 6 UI invariants hold.");
