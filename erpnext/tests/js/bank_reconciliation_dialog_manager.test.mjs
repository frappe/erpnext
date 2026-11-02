// Unit tests for the Bank Reconciliation Tool dialog's voucher type registry.
// The desk script is evaluated in a sandbox with stubbed frappe globals; run with
// `node --test erpnext/tests/js`.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

// values built inside the sandbox carry that realm's prototypes; strip them before strict comparisons
const plain = (value) => JSON.parse(JSON.stringify(value));

const SOURCE = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../public/js/bank_reconciliation_tool/dialog_manager.js"
);

class Dialog {
  constructor(opts) {
    this.fields = opts.fields;
    this.primary_action = opts.primary_action;
    this.values = {};
    this.df_properties = {};
    this.hidden = false;
    this.shown = false;
    this.display = false;
    this.fields_dict = {};
  }
  set_df_property(fieldname, property, value) {
    this.df_properties[fieldname] = {
      ...this.df_properties[fieldname],
      [property]: value,
    };
  }
  get_value(fieldname) {
    return this.values[fieldname];
  }
  set_value(fieldname, value) {
    this.values[fieldname] = value;
  }
  set_values(values) {
    Object.assign(this.values, values);
  }
  get_values() {
    return { ...this.values };
  }
  show() {
    this.shown = true;
    this.display = true;
    this.on_page_show?.();
  }
  hide() {
    this.hidden = true;
    this.display = false;
  }
}

function load_dialog_manager({
  pre_registered = {},
  bank_transaction = null,
} = {}) {
  const calls = {
    call: [],
    xcall: [],
    alerts: [],
    msgprints: [],
    routes: [],
    synced: [],
    form_handlers: {},
  };
  const sandbox = { console };

  sandbox.frappe = {
    provide(namespace) {
      let object = sandbox;
      for (const part of namespace.split(".")) {
        object[part] = object[part] || {};
        object = object[part];
      }
    },
    call(opts) {
      calls.call.push(opts);
      if (opts.method.endsWith("get_doctypes_for_bank_reconciliation")) {
        opts.callback({ message: ["Payment Entry", "Journal Entry"] });
      } else if (opts.method === "frappe.client.get_value") {
        opts.callback({ message: bank_transaction });
      }
    },
    xcall(method, args) {
      calls.xcall.push({ method, args });
      return Promise.resolve(sandbox.xcall_result);
    },
    ui: {
      Dialog,
      form: {
        on(doctype, handlers) {
          calls.form_handlers[doctype] = handlers;
        },
      },
    },
    model: {
      sync(message) {
        calls.synced.push(message);
        return [message];
      },
    },
    set_route: (...route) => calls.routes.push(route),
    show_alert: (message) => calls.alerts.push(message),
    msgprint: (message) => calls.msgprints.push(message),
    throw(message) {
      throw new Error(message);
    },
    scrub: (text) => text.toLowerCase().replace(/ /g, "_"),
    boot: {
      party_account_types: { Customer: "Receivable", Supplier: "Payable" },
    },
  };
  sandbox.__ = (text, args = []) =>
    text.replace(/\{(\d+)\}/g, (_, index) => args[index]);
  sandbox.$ = Object.assign(() => ({}), {
    each: (items, fn) => items.forEach((item, index) => fn(index, item)),
  });
  sandbox.format_currency = (value) => String(value);
  sandbox.erpnext = {
    accounts: { bank_reconciliation: { voucher_types: { ...pre_registered } } },
  };

  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(SOURCE, "utf8"), sandbox, {
    filename: SOURCE,
  });

  const registry = sandbox.erpnext.accounts.bank_reconciliation;
  const dialog_manager = new registry.DialogManager(
    "_Test Company",
    "HDFC - _TC",
    "2024-05-01",
    "2024-05-31"
  );
  return { calls, sandbox, registry, dialog_manager };
}

function loan_repayment_type(overrides = {}) {
  return {
    is_applicable: (bank_transaction) => bank_transaction.deposit > 0,
    get_fields: () => [
      { fieldname: "against_loan", fieldtype: "Link", options: "Loan" },
    ],
    create: () => Promise.resolve({}),
    ...overrides,
  };
}

const deposit = {
  name: "ACC-BTN-0001",
  deposit: 500,
  withdrawal: 0,
  date: "2024-05-05",
  description: "NEFT",
};
const withdrawal = {
  name: "ACC-BTN-0002",
  deposit: 0,
  withdrawal: 500,
  date: "2024-05-05",
};

describe("voucher table rendering", () => {
  it("waits for the first opening, then refreshes the table when already shown", () => {
    const { dialog_manager, sandbox } = load_dialog_manager();
    const wrapper = {};
    const proposals_wrapper = { get: () => wrapper };
    const renders = [];
    sandbox.frappe.DataTable = class {
      constructor(element, options) {
        assert.equal(dialog_manager.dialog.display, true);
        assert.equal(element, wrapper);
        renders.push(options.data);
        this.rowmanager = { checkMap: [] };
      }
      refresh(data) {
        assert.equal(dialog_manager.dialog.display, true);
        renders.push(data);
      }
    };
    dialog_manager.columns = ["Voucher", "Amount"];
    dialog_manager.data = [["ACC-JV-2026-00007", 500]];

    dialog_manager.get_datatable(proposals_wrapper);

    assert.equal(dialog_manager.datatable, undefined);
    assert.equal(renders.length, 0);

    dialog_manager.dialog.show();

    assert.deepEqual(renders, [dialog_manager.data]);
    assert.equal(dialog_manager.dialog.on_page_show, null);
    const table = dialog_manager.datatable;
    table.rowmanager.checkMap = [1];
    dialog_manager.data = [["ACC-JV-2026-00008", 250]];
    dialog_manager.get_datatable(proposals_wrapper);

    assert.equal(dialog_manager.datatable, table);
    assert.equal(renders.length, 2);
    assert.deepEqual(renders[1], dialog_manager.data);
    assert.deepEqual(plain(table.rowmanager.checkMap), []);
  });
});

describe("voucher type registry", () => {
  it("keeps types registered before the bundle loaded, after the built-in ones", () => {
    const custom = loan_repayment_type();
    const { registry } = load_dialog_manager({
      pre_registered: { "Loan Repayment": custom },
    });

    assert.deepEqual(plain(Object.keys(registry.voucher_types)), [
      "Payment Entry",
      "Journal Entry",
      "Loan Repayment",
    ]);
    assert.equal(registry.voucher_types["Loan Repayment"], custom);
  });

  it("offers every type until a transaction is loaded, then filters by is_applicable", () => {
    const { dialog_manager } = load_dialog_manager({
      pre_registered: { "Loan Repayment": loan_repayment_type() },
    });

    assert.deepEqual(plain(dialog_manager.get_document_types()), [
      "Payment Entry",
      "Journal Entry",
      "Loan Repayment",
    ]);

    dialog_manager.bank_transaction = deposit;
    assert.deepEqual(plain(dialog_manager.get_document_types()), [
      "Payment Entry",
      "Journal Entry",
      "Loan Repayment",
    ]);

    dialog_manager.bank_transaction = withdrawal;
    assert.deepEqual(plain(dialog_manager.get_document_types()), [
      "Payment Entry",
      "Journal Entry",
    ]);
  });

  it("rewrites the Document Type options per transaction and resets a value that is no longer offered", () => {
    const { dialog_manager } = load_dialog_manager({
      pre_registered: { "Loan Repayment": loan_repayment_type() },
      bank_transaction: { ...withdrawal },
    });
    dialog_manager.dialog.set_value("document_type", "Loan Repayment");

    dialog_manager.show_dialog("ACC-BTN-0002", () => {});

    assert.equal(
      dialog_manager.dialog.df_properties.document_type.options,
      "Payment Entry\nJournal Entry"
    );
    assert.equal(
      dialog_manager.dialog.get_value("document_type"),
      "Payment Entry"
    );
    assert.equal(dialog_manager.dialog.get_value("posting_date"), "2024-05-05");
    assert.ok(dialog_manager.dialog.shown);
  });

  it("keeps the chosen Document Type when the transaction still allows it", () => {
    const { dialog_manager } = load_dialog_manager({
      pre_registered: { "Loan Repayment": loan_repayment_type() },
      bank_transaction: { ...deposit },
    });
    dialog_manager.dialog.set_value("document_type", "Loan Repayment");

    dialog_manager.show_dialog("ACC-BTN-0001", () => {});

    assert.equal(
      dialog_manager.dialog.get_value("document_type"),
      "Loan Repayment"
    );
  });

  it("adds a registered type's fields to the dialog ahead of the transaction details", () => {
    let received = null;
    const custom = loan_repayment_type({
      get_fields: (dm) => {
        received = dm;
        return [
          { fieldname: "against_loan", fieldtype: "Link", options: "Loan" },
        ];
      },
    });
    const { dialog_manager } = load_dialog_manager({
      pre_registered: { "Loan Repayment": custom },
    });

    const fieldnames = dialog_manager.dialog.fields.map(
      (field) => field.fieldname
    );
    assert.equal(received, dialog_manager);
    assert.ok(fieldnames.includes("against_loan"));
    assert.ok(
      fieldnames.indexOf("against_loan") > fieldnames.indexOf("cost_center")
    );
    assert.ok(
      fieldnames.indexOf("against_loan") < fieldnames.indexOf("details_section")
    );
  });
});

describe("create_voucher", () => {
  it("submits through the registered type and reconciles the dialog", async () => {
    const created = [];
    const reconciled_transaction = {
      name: "ACC-BTN-0001",
      unallocated_amount: 0,
    };
    const custom = loan_repayment_type({
      create: (...args) => {
        created.push(args);
        return Promise.resolve(reconciled_transaction);
      },
    });
    const { calls, dialog_manager } = load_dialog_manager({
      pre_registered: { "Loan Repayment": custom },
    });
    const updated = [];
    dialog_manager.bank_transaction = deposit;
    dialog_manager.update_dt_cards = (transaction) => updated.push(transaction);
    const values = {
      action: "Create Voucher",
      document_type: "Loan Repayment",
      against_loan: "LOAN-0001",
    };

    await dialog_manager.reconciliation_dialog_primary_action(values);

    assert.deepEqual(created, [[dialog_manager, values, false]]);
    assert.deepEqual(updated, [reconciled_transaction]);
    assert.match(calls.alerts[0], /ACC-BTN-0001 added as Loan Repayment/);
    assert.ok(dialog_manager.dialog.hidden);
    assert.deepEqual(calls.routes, []);
  });

  it("opens the draft in full page and reconciles it once the form is submitted", async () => {
    const draft = {
      doctype: "Loan Repayment",
      name: "new-loan-repayment-1",
      __islocal: 1,
    };
    const custom = loan_repayment_type({
      create: () => Promise.resolve(draft),
    });
    const { calls, dialog_manager } = load_dialog_manager({
      pre_registered: { "Loan Repayment": custom },
    });
    dialog_manager.bank_transaction = deposit;
    dialog_manager.dialog.set_values({
      action: "Create Voucher",
      document_type: "Loan Repayment",
    });

    await dialog_manager.edit_in_full_page();

    assert.deepEqual(calls.synced, [draft]);
    assert.deepEqual(calls.routes, [
      ["Form", "Loan Repayment", "new-loan-repayment-1"],
    ]);
    assert.equal(dialog_manager.dialog.hidden, false);
    assert.deepEqual(calls.alerts, []);

    const handlers = calls.form_handlers["Loan Repayment"];
    assert.ok(
      handlers,
      "registered types get the after-submit reconciliation hooks"
    );
    const frm = {
      doctype: "Loan Repayment",
      doc: { name: "new-loan-repayment-1" },
    };
    handlers.before_save(frm);
    frm.doc.name = "LM-REP-0001";
    handlers.after_save(frm);
    handlers.on_submit(frm);

    const reconcile = calls.call.at(-1);
    assert.match(reconcile.method, /reconcile_vouchers$/);
    assert.deepEqual(plain(reconcile.args), {
      bank_transaction_name: "ACC-BTN-0001",
      vouchers: [
        { payment_doctype: "Loan Repayment", payment_name: "LM-REP-0001" },
      ],
      is_new_voucher: true,
    });

    handlers.on_submit(frm);
    assert.equal(
      calls.call.at(-1),
      reconcile,
      "a voucher is only reconciled once"
    );
  });

  it("passes allow_edit through to the built-in server methods", async () => {
    const { calls, sandbox, dialog_manager } = load_dialog_manager();
    sandbox.xcall_result = {
      doctype: "Payment Entry",
      name: "new-payment-entry-1",
    };
    dialog_manager.bank_transaction = deposit;

    await dialog_manager.create_voucher(
      {
        document_type: "Payment Entry",
        party_type: "Customer",
        party: "_Test Customer",
      },
      true
    );
    await dialog_manager.create_voucher(
      {
        document_type: "Journal Entry",
        journal_entry_type: "Bank Entry",
        second_account: "Debtors - _TC",
      },
      true
    );

    const [payment_entry, journal_entry] = calls.xcall;
    assert.match(payment_entry.method, /create_payment_entry_bts$/);
    assert.equal(payment_entry.args.allow_edit, true);
    assert.equal(payment_entry.args.bank_transaction_name, "ACC-BTN-0001");
    assert.equal(payment_entry.args.company_bank_account, "HDFC - _TC");
    assert.match(journal_entry.method, /create_journal_entry_bts$/);
    assert.equal(journal_entry.args.allow_edit, true);
    assert.equal(journal_entry.args.entry_type, "Bank Entry");
    assert.equal(journal_entry.args.second_account, "Debtors - _TC");
    assert.ok(
      calls.form_handlers["Payment Entry"] &&
        calls.form_handlers["Journal Entry"]
    );
  });

  it("refuses a document type that is not registered", () => {
    const { dialog_manager } = load_dialog_manager();
    dialog_manager.bank_transaction = deposit;

    assert.throws(
      () => dialog_manager.create_voucher({ document_type: "Sales Invoice" }),
      /Cannot create Sales Invoice from a Bank Transaction/
    );
  });
});
