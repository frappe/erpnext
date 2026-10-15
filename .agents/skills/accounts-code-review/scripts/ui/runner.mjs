// Playwright runner for accounts-code-review. review.py starts it; do not run it by hand.
//
//   node runner.mjs <workdir> <run id> <side: base|head> <target: UB|UH> <base url>
//
// Runs every scenario in <workdir>/ui.spec.mjs against one side's UI company and
// writes runs/<id>/ui/<side>.json (structured state, compared by verdict.py) and
// runs/<id>/ui/<side>/*.png (screenshots, for people only, never compared).

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [workdir, runId, side, target, baseUrl] = process.argv.slice(2);
const rundir = path.join(workdir, "runs", runId);
const outdir = path.join(rundir, "ui");
const shotdir = path.join(outdir, side);
fs.mkdirSync(shotdir, { recursive: true });

const require = createRequire(path.join(workdir, ".ui", "package.json"));
const { chromium } = require("playwright");
const targets = JSON.parse(
  fs.readFileSync(path.join(rundir, "ui-targets", `${target}.json`), "utf8")
);
const password = fs
  .readFileSync(path.join(workdir, ".ui-password"), "utf8")
  .trim();
const user = JSON.parse(
  fs.readFileSync(path.join(rundir, "ui-user.json"), "utf8")
).email;
const spec = (
  await import(pathToFileURL(path.join(workdir, "ui.spec.mjs")).href)
).default;

// ------------------------------------------------------------------ normalize

const names = { ...targets.names };
const alternatives = Object.keys(names).sort((a, b) => b.length - a.length);
const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const pattern = alternatives.length
  ? new RegExp(
      alternatives.map((n) => `(?<![\\w-])${escape(n)}(?![\\w-])`).join("|"),
      "g"
    )
  : null;
const abbrSuffix = ` - ${targets.abbr}`;
const VOLATILE = new Set([
  "name",
  "creation",
  "modified",
  "owner",
  "modified_by",
  "parent",
  "doctype",
  "parenttype",
  "parentfield",
  "__islocal",
  "__unsaved",
  "__last_sync_on",
  "balance",
  "balance_in_account_currency",
]);

function norm(value) {
  if (Array.isArray(value)) return value.map(norm);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort())
      if (!VOLATILE.has(key)) out[key] = norm(value[key]);
    return out;
  }
  if (typeof value === "string") {
    if (value in names) return names[value];
    let s = pattern ? value.replace(pattern, (m) => names[m]) : value;
    return s.split(abbrSuffix).join("");
  }
  if (typeof value === "number") return Math.round(value * 1e6) / 1e6;
  return value;
}

const sortRows = (rows) =>
  [...rows].sort((a, b) => (JSON.stringify(a) < JSON.stringify(b) ? -1 : 1));

// ------------------------------------------------------------------ page state

function readState() {
  const visible = (el) =>
    !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const text = (el) => (el ? el.innerText.trim().replace(/\s+/g, " ") : null);
  const LAYOUT = new Set([
    "Section Break",
    "Column Break",
    "Tab Break",
    "Fold",
    "Heading",
  ]);
  const TIME = new Set(["Time", "Datetime"]);
  const out = {
    route:
      window.frappe && frappe.get_route
        ? frappe.get_route().join("/")
        : location.pathname,
    title: text(document.querySelector(".page-head .title-text")),
    indicator: text(
      [...document.querySelectorAll(".page-head .indicator-pill")].find(visible)
    ),
    buttons: [
      ...document.querySelectorAll(
        ".page-head .page-actions button, .page-head .page-actions a.btn, .form-inner-toolbar button"
      ),
    ]
      .filter(visible)
      .map(text)
      .filter(Boolean)
      .sort(),
    dialogs: [...document.querySelectorAll(".modal.show")]
      .filter(visible)
      .map((m) => ({
        title: text(m.querySelector(".modal-title")),
        body: text(m.querySelector(".modal-body"))?.slice(0, 500) ?? null,
      })),
    alerts: [...document.querySelectorAll("#alert-container .alert")]
      .filter(visible)
      .map(text),
  };
  if (window.cur_frm && cur_frm.doc && out.route.startsWith("Form")) {
    const fields = {};
    for (const field of cur_frm.fields || []) {
      const df = field.df || {};
      if (!df.fieldname || LAYOUT.has(df.fieldtype)) continue;
      let value = cur_frm.doc[df.fieldname];
      if (TIME.has(df.fieldtype) && value) value = "<time>";
      if (Array.isArray(value)) value = value.map((row) => ({ ...row }));
      fields[df.fieldname] = {
        visible: visible(field.wrapper),
        read_only: field.disp_status === "Read",
        reqd: !!df.reqd,
        value: value === undefined ? null : value,
      };
    }
    out.form = {
      form_of: cur_frm.doctype,
      docstatus: cur_frm.doc.docstatus,
      unsaved: !!cur_frm.is_dirty(),
      fields,
    };
  }
  if (
    window.frappe &&
    frappe.query_report &&
    out.route.startsWith("query-report")
  ) {
    out.report = {
      columns: (frappe.query_report.columns || []).map((c) => c.fieldname),
      rows: frappe.query_report.data || [],
    };
  }
  return out;
}

// ------------------------------------------------------------------ helpers

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(
    () => !window.frappe || !frappe.request || !frappe.request.ajax_count,
    null,
    { timeout: 60000 }
  );
  await page.evaluate(
    () =>
      new Promise((r) =>
        window.frappe && frappe.after_ajax ? frappe.after_ajax(r) : r()
      )
  );
  await page.waitForFunction(
    () =>
      !document.querySelector(
        ".freeze-message-container:not(.hide), #freeze.in"
      ),
    null,
    { timeout: 60000 }
  );
  await page.evaluate(
    () =>
      new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
  );
}

const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");

function makeUi(page, record, scenarioId) {
  const ui = {
    page,
    /** The site's name for a scenario label: [doctype, name]. */
    doc(label) {
      const entry = targets.registry[label];
      if (!entry) throw new Error(`unknown scenario label: ${label}`);
      return entry;
    },
    async openDoc(label) {
      const [doctype, name] = ui.doc(label);
      await page.goto(
        `${baseUrl}/app/${slug(doctype)}/${encodeURIComponent(name)}`
      );
      await page.waitForFunction(
        (n) => window.cur_frm && cur_frm.doc && cur_frm.doc.name === n,
        name,
        { timeout: 60000 }
      );
      await settle(page);
    },
    async openNew(doctype) {
      await page.goto(`${baseUrl}/app/${slug(doctype)}/new`);
      await page.waitForFunction(
        () => window.cur_frm && cur_frm.doc && cur_frm.doc.__islocal,
        null,
        { timeout: 60000 }
      );
      await settle(page);
    },
    async openList(doctype, filters = {}) {
      const qs = new URLSearchParams(filters).toString();
      await page.goto(`${baseUrl}/app/${slug(doctype)}${qs ? `?${qs}` : ""}`);
      await settle(page);
    },
    async openReport(reportName, filters = {}) {
      const qs = new URLSearchParams({
        company: targets.company,
        ...filters,
      }).toString();
      await page.goto(
        `${baseUrl}/app/query-report/${encodeURIComponent(reportName)}?${qs}`
      );
      await page.waitForFunction(
        () => window.frappe && frappe.query_report && frappe.query_report.data,
        null,
        { timeout: 120000 }
      );
      await settle(page);
    },
    /** Set a form field the way a user's input does, then wait for every trigger. */
    async setValue(fieldname, value) {
      await page.evaluate(
        ([f, v]) => cur_frm.set_value(f, v),
        [fieldname, value]
      );
      await settle(page);
    },
    /** Click a visible button or link by its exact text. */
    async click(text) {
      await page
        .getByRole("button", { name: text, exact: true })
        .or(page.getByRole("link", { name: text, exact: true }))
        .filter({ visible: true })
        .first()
        .click();
      await settle(page);
    },
    /** Open a toolbar group (for example "Create") and click an item in it. */
    async clickMenu(group, item) {
      await ui.click(group);
      await page
        .locator(".dropdown-menu.show")
        .getByText(item, { exact: true })
        .first()
        .click();
      await settle(page);
    },
    async save() {
      await page.keyboard.press(
        process.platform === "darwin" ? "Meta+S" : "Control+S"
      );
      await settle(page);
    },
    /** Record the page's state under a name, and a screenshot for people. */
    async capture(name) {
      const state = norm(await page.evaluate(readState));
      if (state.report) state.report.rows = sortRows(state.report.rows);
      record.captures[name] = state;
      await page.screenshot({
        path: path.join(shotdir, `${scenarioId}--${name}.png`),
        fullPage: true,
        animations: "disabled",
      });
    },
  };
  return ui;
}

// ------------------------------------------------------------------ main

const browser = await chromium.launch();
const login = await browser.newContext({ baseURL: baseUrl });
const res = await login.request.post(`${baseUrl}/api/method/login`, {
  form: { usr: user, pwd: password },
});
if (!res.ok()) throw new Error(`login failed: ${res.status()}`);
const storageState = await login.storageState();
await login.close();

const results = {};
for (const scenario of spec) {
  const record = {
    title: scenario.title,
    captures: {},
    console_errors: [],
    failed_requests: [],
    error: null,
  };
  const context = await browser.newContext({
    storageState,
    viewport: { width: 1366, height: 900 },
    locale: "en-US",
    timezoneId: "UTC",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  page.on(
    "console",
    (m) =>
      m.type() === "error" &&
      record.console_errors.push(norm(m.text()).slice(0, 300))
  );
  page.on("pageerror", (e) =>
    record.console_errors.push(norm(String(e.message)).slice(0, 300))
  );
  page.on("response", (r) => {
    if (r.status() >= 400)
      record.failed_requests.push(
        `${r.status()} ${norm(new URL(r.url()).pathname)}`
      );
  });
  try {
    await scenario.run(makeUi(page, record, scenario.id));
  } catch (e) {
    record.error = norm(String(e.message)).split("\n")[0].slice(0, 300);
    await page
      .screenshot({
        path: path.join(shotdir, `${scenario.id}--error.png`),
        fullPage: true,
      })
      .catch(() => {});
  }
  record.console_errors = [...new Set(record.console_errors)].sort();
  record.failed_requests = [...new Set(record.failed_requests)].sort();
  results[scenario.id] = record;
  await context.close();
}
await browser.close();
fs.writeFileSync(
  path.join(outdir, `${side}.json`),
  JSON.stringify(results, null, 1)
);
console.log(`UI_OK ${side} ${Object.keys(results).length} scenarios`);
