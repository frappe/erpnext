import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const SOURCE = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../accounts/doctype/bisect_accounting_statements/bisect_accounting_statements.js"
);

// the shape of frappe.datetime.add_days, which returns moment().format(): ISO with the local offset
function add_days(value, days) {
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return `${date.toISOString().slice(0, 10)}T00:00:00+05:30`;
}

function heatmap_days(doc) {
  let handlers;
  let config;
  const frappe = {
    datetime: { add_days },
    ui: {
      form: { on: (doctype, events) => (handlers = events) },
      chart: (wrapper, chart_config) => (config = chart_config),
    },
  };
  vm.runInNewContext(fs.readFileSync(SOURCE, "utf8"), { frappe });
  handlers.render_heatmap({ doc, get_field: () => ({ $wrapper: {} }) });
  return JSON.parse(JSON.stringify(config.data));
}

const selected = (days) =>
  days.filter((day) => day.bisecting).map((day) => day.date);

describe("Bisect Accounting Statements heatmap", () => {
  it("draws every day of the range and the selection, both ends included", () => {
    const days = heatmap_days({
      from_date: "2026-01-01 00:00:00",
      to_date: "2026-06-30 00:00:00",
      current_from_date: "2026-02-01 00:00:00",
      current_to_date: "2026-03-31 00:00:00",
    });
    assert.equal(days.length, 181);
    assert.equal(days.at(-1).date, "2026-06-30");
    const bisecting = selected(days);
    assert.equal(bisecting.length, 59);
    assert.deepEqual(
      [bisecting[0], bisecting.at(-1)],
      ["2026-02-01", "2026-03-31"]
    );
  });

  it("marks a one-day selection", () => {
    const days = heatmap_days({
      from_date: "2026-01-01 00:00:00",
      to_date: "2026-01-31 00:00:00",
      current_from_date: "2026-01-15 00:00:00",
      current_to_date: "2026-01-15 00:00:00",
    });
    assert.deepEqual(selected(days), ["2026-01-15"]);
  });

  it("draws no days before the range is set", () => {
    assert.deepEqual(heatmap_days({}), []);
  });
});
