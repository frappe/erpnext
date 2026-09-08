/* eslint-env node */
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

function setupScanner() {
  const items = [];
  const item_requests = [];
  const alerts = [];
  let scan_result;
  const frm = {
    doctype: "Delivery Note",
    doc: { doctype: "Delivery Note", items },
    fields_dict: {
      scan_barcode: {
        value: "",
        set_value(value) {
          this.value = value;
        },
      },
      items: { grid: { doctype: "Delivery Note Item" } },
    },
    script_manager: { trigger() {} },
  };
  const frappe = {
    flags: {},
    meta: { has_field: (doctype, field) => field !== "last_scanned_warehouse" },
    utils: { get_link_title: () => "PHYSICAL-123", add_link_title() {} },
    call: async () => ({ message: scan_result }),
    show_alert: (alert) => alerts.push(alert),
    run_serially: (tasks) =>
      tasks.reduce((pending, task) => pending.then(task), Promise.resolve()),
    model: {
      add_child: (doc, doctype) => {
        const row = {
          doctype,
          name: `row-${items.length + 1}`,
          idx: items.length + 1,
          qty: 1,
        };
        items.push(row);
        return row;
      },
      set_value: async (doctype, name, field, value) => {
        const row = items.find((item) => item.name === name);
        const values = typeof field === "string" ? { [field]: value } : field;
        const item_changed =
          values.item_code && values.item_code !== row.item_code;
        // Frappe sets all supplied fields before running their change handlers.
        Object.assign(row, values);
        if (item_changed) {
          item_requests.push({ ...row });
          // Outward item selection auto-picks stock if the scanned references were absent.
          row.serial_no ||= "auto-picked-id";
          row.batch_no ||= "auto-picked-batch";
        }
      },
    },
  };
  const context = {
    frappe,
    erpnext: { utils: {} },
    __: (text) => text,
    refresh_field() {},
    flt: Number,
  };
  vm.runInNewContext(
    readFileSync(path.join(__dirname, "../utils/barcode_scanner.js"), "utf8"),
    context
  );
  const scanner = new context.erpnext.utils.BarcodeScanner({ frm });
  const scan = (serial_no, item_code = "ITEM-A") => {
    scan_result = {
      item_code,
      serial_no,
      serial_number: "PHYSICAL-123",
      batch_no: `batch-${item_code}`,
      has_serial_no: 1,
      has_batch_no: 1,
    };
    frm.fields_dict.scan_barcode.value = "PHYSICAL-123";
    return scanner.process_scan();
  };
  return { scanner, scan, items, item_requests, alerts, frm, frappe };
}

test("one scan sets its serial and batch before item auto-selection and adds one unit", async () => {
  const { scan, items, item_requests } = setupScanner();
  await scan("scanned-id");
  assert.equal(item_requests[0].serial_no, "scanned-id");
  assert.equal(item_requests[0].batch_no, "batch-ITEM-A");
  assert.equal(item_requests[0].qty, 1);
  assert.equal(items[0].serial_no, "scanned-id");
  assert.equal(items[0].qty, 1);
});

test("rescanning the same serial does not append it or increase quantity", async () => {
  const { scan, items, alerts } = setupScanner();
  await scan("scanned-id");
  await assert.rejects(scan("scanned-id"));
  assert.equal(items.length, 1);
  assert.equal(items[0].serial_no, "scanned-id");
  assert.equal(items[0].qty, 1);
  assert.equal(alerts.at(-1).indicator, "orange");
});

test("distinct serial IDs, including prefixes, each add one unit", async () => {
  const { scan, items } = setupScanner();
  await scan("scanned-id-long");
  await scan("scanned-id");
  assert.equal(items[0].serial_no, "scanned-id-long\nscanned-id");
  assert.equal(items[0].qty, 2);
});

test("matching physical numbers on different items keep their separate serial IDs", async () => {
  const { scan, items } = setupScanner();
  await scan("item-a-id", "ITEM-A");
  await scan("item-b-id", "ITEM-B");
  assert.deepEqual(
    items.map((row) => [row.item_code, row.serial_no, row.qty]),
    [
      ["ITEM-A", "item-a-id", 1],
      ["ITEM-B", "item-b-id", 1],
    ]
  );
});

test("scanning into an empty default row starts with one unit", async () => {
  const { scan, items, frappe, frm } = setupScanner();
  frappe.model.add_child(frm.doc, "Delivery Note Item");
  await scan("scanned-id");
  assert.equal(items.length, 1);
  assert.equal(items[0].serial_no, "scanned-id");
  assert.equal(items[0].qty, 1);
});

test("the scan dialog replaces auto-selected serials with its scanned list", async () => {
  const { scanner, items, frappe, frm } = setupScanner();
  frappe.ui = {
    Dialog: class {
      constructor({ fields }) {
        this.values = Object.fromEntries(
          fields.map((field) => [field.fieldname, field.default])
        );
        this.$wrapper = { find: () => ({ css() {} }) };
      }
      set_primary_action(label, action) {
        this.primary_action = action;
      }
      get_value(field) {
        return this.values[field];
      }
      show() {}
      hide() {}
    },
  };
  const row = frappe.model.add_child(frm.doc, "Delivery Note Item");
  Object.assign(row, {
    item_code: "ITEM-A",
    serial_no: "auto-picked-id",
    batch_no: "batch-ITEM-A",
  });
  scanner.prepare_item_for_scan(
    row,
    "ITEM-A",
    null,
    "batch-ITEM-A",
    "scanned-id"
  );
  await scanner.dialog.primary_action();
  assert.equal(items[0].serial_no, "scanned-id");
  assert.equal(items[0].qty, 1);
  assert.equal(items[0].has_item_scanned, 1);
});
