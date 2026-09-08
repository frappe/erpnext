/* eslint-env node */
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

function setup(xcall) {
  class Control {
    get_model_value() {
      return this.doc.serial_no;
    }
    parse_validate_and_set_in_model(value) {
      this.doc.serial_no = value;
    }
    set_formatted_input(value) {
      this.display = value;
    }
    set_disp_area() {}
  }
  const titles = new Map();
  const handlers = {};
  const frappe = {
    xcall,
    ui: {
      form: {
        ControlSmallText: Control,
        ControlLink: Control,
        ControlText: Control,
        ControlLongText: Control,
        on: (doctype, events) => {
          handlers[doctype] = events;
        },
      },
    },
    utils: {
      get_link_title: (doctype, name) => titles.get(name),
      add_link_title: (doctype, name, value) => titles.set(name, value),
    },
  };
  vm.runInNewContext(
    readFileSync(
      path.join(__dirname, "../utils/serial_batch_input.js"),
      "utf8"
    ),
    { frappe }
  );
  const control = new frappe.ui.form.ControlSmallText();
  control.frm = {
    doctype: "Purchase Receipt",
    doc: { doctype: "Purchase Receipt" },
  };
  control.df = { parent: "Purchase Receipt Item", fieldname: "serial_no" };
  control.doc = { item_code: "ITEM-B", serial_no: "existing-id" };
  return { control, handlers, titles, frappe };
}

test("physical input resolves using the row's item, even when it resembles an existing ID", async () => {
  let request;
  const { control } = setup(async (method, args) => {
    request = args;
    return ["new-id"];
  });
  await control.parse_validate_and_set_in_model("existing-id", {});
  assert.equal(request.row.item_code, "ITEM-B");
  assert.deepEqual(Array.from(request.numbers), ["existing-id"]);
  assert.equal(control.doc.serial_no, "new-id");
  assert.equal(control.serial_number_text("new-id"), "existing-id");
});

test("programmatic ID updates do not resolve the ID as a physical number", async () => {
  const { control } = setup(() => {
    throw new Error("Unexpected lookup");
  });
  await control.parse_validate_and_set_in_model("another-id", null);
  assert.equal(control.doc.serial_no, "another-id");
});

test("saving waits for number resolution and stale responses cannot overwrite newer input", async () => {
  const responses = [];
  const { control, handlers } = setup(
    () => new Promise((resolve) => responses.push(resolve))
  );
  const first = control.parse_validate_and_set_in_model("first-number", {});
  const second = control.parse_validate_and_set_in_model("second-number", {});
  let saved = false;
  const saving = handlers[control.frm.doctype]
    .before_save(control.frm)
    .then(() => {
      saved = true;
    });
  assert.equal(saved, false);
  responses[1](["second-id"]);
  await second;
  responses[0](["first-id"]);
  await first;
  await saving;
  assert.equal(control.doc.serial_no, "second-id");
  assert.equal(saved, true);
});

test("an ambiguous scan requires a selection and cancel leaves it unresolved", async () => {
  let dialog;
  const context = {
    erpnext: { utils: {} },
    __: (text) => text,
    frappe: {
      ui: {
        Dialog: class {
          constructor(options) {
            Object.assign(this, options);
            dialog = this;
          }
          show() {}
          hide() {
            this.onhide();
          }
        },
      },
    },
  };
  vm.runInNewContext(
    readFileSync(path.join(__dirname, "../utils/barcode_scanner.js"), "utf8"),
    context
  );
  const scanner = Object.create(context.erpnext.utils.BarcodeScanner.prototype);
  const candidates = [
    { item_code: "A", barcode: "123" },
    { item_code: "A", serial_no: "id-a", serial_number: "123" },
    { item_code: "B", serial_no: "id-b", serial_number: "123" },
  ];
  const selection = scanner.select_scan_match(candidates);
  const item_field = dialog.fields[0];
  assert.equal(item_field.fieldtype, "Link");
  assert.equal(item_field.options, "Item");
  assert.deepEqual(Array.from(item_field.get_query().filters.name[1]), [
    "A",
    "B",
  ]);
  dialog.primary_action({ item_code: "B" });
  assert.equal(await selection, candidates[2]);
  assert.equal(
    await scanner.select_scan_match(candidates.slice(0, 2)),
    candidates[1]
  );
  const cancelled = scanner.select_scan_match(candidates);
  dialog.hide();
  assert.equal(await cancelled, null);
});

test("a programmatic update invalidates a pending keyboard lookup", async () => {
  let resolve;
  const { control } = setup(
    () =>
      new Promise((callback) => {
        resolve = callback;
      })
  );
  const typing = control.parse_validate_and_set_in_model("typed-number", {});
  await control.parse_validate_and_set_in_model("selected-id", null);
  resolve(["typed-id"]);
  await typing;
  assert.equal(control.doc.serial_no, "selected-id");
});

test("typed batch input uses the physical label even when the control mapped it to an old ID", async () => {
  let request;
  const { control, frappe } = setup(async (method, args) => {
    request = args;
    return { batch_nos: ["item-b-batch-id"] };
  });
  const link = new frappe.ui.form.ControlLink();
  link.frm = control.frm;
  link.doc = control.doc;
  link.get_options = () => "Batch";
  link.get_label_value = () => "physical-batch-number";
  await link.parse_validate_and_set_in_model("item-a-batch-id", {}, undefined);
  assert.equal(request.item_code, "ITEM-B");
  assert.deepEqual(Array.from(request.batch_numbers), [
    "physical-batch-number",
  ]);
  assert.equal(link.doc.serial_no, "item-b-batch-id");
  await link.parse_validate_and_set_in_model("programmatic-id", null);
  assert.equal(link.doc.serial_no, "programmatic-id");
  await link.parse_validate_and_set_in_model(
    "item-a-batch-id",
    null,
    "selected-physical-label"
  );
  assert.deepEqual(Array.from(request.batch_numbers), [
    "selected-physical-label",
  ]);
});

test("POS controls use their explicit item and form context", async () => {
  let request;
  const { control } = setup(async (method, args) => {
    request = args;
    return ["pos-serial-id"];
  });
  control.serial_batch_context = { frm: control.frm, row: control.doc };
  control.frm = undefined;
  await control.parse_validate_and_set_in_model("POS-PHYSICAL", {});
  assert.equal(request.row.item_code, "ITEM-B");
  assert.equal(control.doc.serial_no, "pos-serial-id");
});

test("report numbers display physical labels and link to internal IDs", () => {
  let linked;
  const context = {
    frappe: {
      model: { can_read: () => true },
      form: {
        formatters: {
          Link: (id, df, options) => {
            linked = { id, options };
            return options.label;
          },
        },
      },
      utils: {
        escape_html: (value) =>
          value.replaceAll("<", "&lt;").replaceAll(">", "&gt;"),
      },
    },
  };
  vm.runInNewContext(
    readFileSync(
      path.join(__dirname, "../utils/serial_batch_display.js"),
      "utf8"
    ),
    context
  );
  const format = context.frappe.form.formatters.SerialBatchNumber;
  const field = { reference_field: "serial_no", options: "Serial No" };
  assert.equal(
    format("PHYSICAL-123", field, {}, { serial_no: "internal-id" }),
    "PHYSICAL-123"
  );
  assert.equal(linked.id, "internal-id");
  assert.equal(linked.options.label, "PHYSICAL-123");
  context.frappe.model.can_read = () => false;
  assert.equal(
    format("PHYSICAL-123", field, {}, { serial_no: "internal-id" }),
    "PHYSICAL-123"
  );
  assert.equal(
    format(
      "<serial>",
      field,
      { for_print: true },
      { serial_no: "internal-id" }
    ),
    "&lt;serial&gt;"
  );
});
