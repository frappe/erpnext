import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const SOURCE = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../public/js/utils/record_payment_dialog.js"
);

function load_dialog() {
  const erpnext = { accounts: {}, get_currency: () => "INR" };
  const frappe = { provide: () => {} };
  vm.runInNewContext(fs.readFileSync(SOURCE, "utf8"), { frappe, erpnext });
  return erpnext.accounts.RecordPaymentDialog;
}

describe("Record Payment dialog", () => {
  const Dialog = load_dialog();
  const payment = {
    doctype: "Payment Entry",
    company: "Test Company",
    payment_type: "Receive",
    paid_from_account_currency: "INR",
    paid_to_account_currency: "INR",
    references: [{ outstanding_amount: 400 }, { outstanding_amount: 600 }],
  };

  it("leaves payments with deductions, taxes or payment requests to the full form", () => {
    assert.equal(Dialog.supports(payment), true);
    assert.equal(
      Dialog.supports({ ...payment, deductions: [{ amount: 10 }] }),
      false
    );
    assert.equal(
      Dialog.supports({ ...payment, taxes: [{ tax_amount: 10 }] }),
      false
    );
    assert.equal(Dialog.supports({ ...payment, references: [] }), false);
    assert.equal(
      Dialog.supports({
        ...payment,
        references: [{ outstanding_amount: 10, payment_request: "PR-1" }],
      }),
      false
    );
    assert.equal(
      Dialog.supports({ ...payment, doctype: "Journal Entry" }),
      false
    );
  });

  it("supports another party currency only through a company currency account", () => {
    const usd_party = { ...payment, paid_from_account_currency: "USD" };
    assert.equal(Dialog.supports(usd_party), true);
    assert.equal(
      Dialog.supports({ ...usd_party, paid_to_account_currency: "EUR" }),
      false
    );
  });
});
