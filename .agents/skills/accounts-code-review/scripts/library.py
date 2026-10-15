"""Fixed scenario library. Every review runs every scenario, in every variant.

Each scenario has fixed inputs (DATE, amounts, rates) and two hooks:
build(lab) creates and submits its documents; legacy(lab) acts on them later
(cancel, return, pay, reconcile). Wrap an action whose success or failure is
itself behavior in lab.attempt(), so a blocked action is recorded, not fatal.

Adding a scenario changes every later review's baseline: append to SCENARIOS,
never reorder or edit one in place.
"""

import frappe
from pr_ledger import DATE, EUR_PAYMENT_RATE, EUR_RATE

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.controllers.sales_and_purchase_return import make_return_doc


def _si(lab, label, rows, customer=None, debit_to=None, currency=None, rate=1, taxes=None, **extra):
	ctx = lab.ctx
	doc = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": ctx.company,
			"customer": customer or ctx.customer,
			"debit_to": debit_to or ctx.receivable,
			"currency": currency or ctx.currency,
			"conversion_rate": rate,
			"set_posting_time": 1,
			"posting_date": DATE,
			"due_date": DATE,
			"cost_center": ctx.cost_center,
			"items": [
				{
					"item_code": item,
					"qty": qty,
					"rate": price,
					"income_account": ctx.income,
					"cost_center": ctx.cost_center,
					"warehouse": ctx.warehouse,
				}
				for item, qty, price in rows
			],
			"taxes": taxes or [],
			**extra,
		}
	).insert()
	doc.submit()
	return lab.reg(label, doc)


def _pi(lab, label, rows):
	ctx = lab.ctx
	doc = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": ctx.company,
			"supplier": ctx.supplier,
			"credit_to": ctx.payable,
			"currency": ctx.currency,
			"conversion_rate": 1,
			"set_posting_time": 1,
			"posting_date": DATE,
			"due_date": DATE,
			"bill_date": DATE,
			"cost_center": ctx.cost_center,
			"items": [
				{
					"item_code": item,
					"qty": qty,
					"rate": price,
					"expense_account": ctx.expense,
					"cost_center": ctx.cost_center,
				}
				for item, qty, price in rows
			],
		}
	).insert()
	doc.submit()
	return lab.reg(label, doc)


def _pay(lab, label, dt, dn, amount=None, source_rate=None):
	pe = get_payment_entry(dt, dn, party_amount=amount, bank_account=lab.ctx.bank, reference_date=DATE)
	pe.posting_date = pe.reference_date = DATE
	pe.reference_no = label
	if amount is not None:
		pe.references[0].allocated_amount = amount
	if source_rate:
		pe.source_exchange_rate = source_rate
		pe.received_amount = pe.base_received_amount = pe.paid_amount * source_rate
	pe.insert()
	pe.submit()
	return lab.reg(label, pe)


def _return(lab, label, label_against, qty=None):
	ret = make_return_doc(*lab.registry[label_against][:1], lab.registry[label_against][1])
	ret.posting_date = DATE
	ret.set_posting_time = 1
	if qty is not None:
		for row in ret.items:
			row.qty = -qty
	ret.insert()
	ret.submit()
	return lab.reg(label, ret)


def _cancel(lab, label):
	lab.attempt(f"cancel-{label}", lambda: lab.get(label).cancel())


# ---------------------------------------------------------------- scenarios


def si_basic(lab):
	_si(lab, "si_basic", [(lab.ctx.service_item, 2, 100)])


def si_basic_legacy(lab):
	_cancel(lab, "si_basic")


def si_tax(lab):
	taxes = [{"charge_type": "On Net Total", "account_head": lab.ctx.tax, "description": "Tax", "rate": 10}]
	_si(lab, "si_tax", [(lab.ctx.service_item, 1, 1000)], taxes=taxes)


def si_tax_legacy(lab):
	lab.attempt("return-si_tax", lambda: _return(lab, "si_tax_return", "si_tax"))


def pi_basic(lab):
	_pi(lab, "pi_basic", [(lab.ctx.service_item, 3, 50)])


def pi_basic_legacy(lab):
	lab.attempt(
		"pay-pi_basic", lambda: _pay(lab, "pi_basic_payment", "Purchase Invoice", lab.registry["pi_basic"][1])
	)


def partial_payment(lab):
	si = _si(lab, "pp_invoice", [(lab.ctx.service_item, 1, 500)])
	_pay(lab, "pp_payment", "Sales Invoice", si.name, amount=200)


def partial_payment_legacy(lab):
	_cancel(lab, "pp_payment")


def advance_reconcile(lab):
	ctx = lab.ctx
	pe = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": ctx.company,
			"posting_date": DATE,
			"party_type": "Customer",
			"party": ctx.customer,
			"paid_from": ctx.receivable,
			"paid_to": ctx.bank,
			"paid_amount": 300,
			"received_amount": 300,
			"reference_no": "advance",
			"reference_date": DATE,
		}
	).insert()
	pe.submit()
	lab.reg("adv_payment", pe)
	_si(lab, "adv_invoice", [(ctx.service_item, 1, 300)])


def advance_reconcile_legacy(lab):
	def reconcile():
		pr = frappe.new_doc("Payment Reconciliation")
		pr.update(
			{
				"company": lab.ctx.company,
				"party_type": "Customer",
				"party": lab.ctx.customer,
				"receivable_payable_account": lab.ctx.receivable,
				"from_invoice_date": DATE,
				"to_invoice_date": DATE,
				"from_payment_date": DATE,
				"to_payment_date": DATE,
			}
		)
		pr.get_unreconciled_entries()
		invoices = [r.as_dict() for r in pr.invoices if r.invoice_number == lab.registry["adv_invoice"][1]]
		payments = [r.as_dict() for r in pr.payments if r.reference_name == lab.registry["adv_payment"][1]]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

	lab.attempt("reconcile-adv", reconcile)


def credit_note_partial(lab):
	_si(lab, "cn_invoice", [(lab.ctx.service_item, 2, 100)])
	_return(lab, "cn_return", "cn_invoice", qty=1)


def credit_note_partial_legacy(lab):
	_cancel(lab, "cn_return")
	_cancel(lab, "cn_invoice")


def je_basic(lab):
	ctx = lab.ctx
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": ctx.company,
			"posting_date": DATE,
			"accounts": [
				{"account": ctx.expense, "debit_in_account_currency": 75, "cost_center": ctx.cost_center},
				{"account": ctx.cash, "credit_in_account_currency": 75, "cost_center": ctx.cost_center},
			],
		}
	).insert()
	je.submit()
	lab.reg("je_basic", je)


def je_basic_legacy(lab):
	_cancel(lab, "je_basic")


def fx_invoice(lab):
	ctx = lab.ctx
	si = _si(
		lab,
		"fx_invoice",
		[(ctx.service_item, 1, 100)],
		customer=ctx.customer_eur,
		debit_to=ctx.receivable_eur,
		currency=ctx.foreign_currency,
		rate=EUR_RATE,
		selling_price_list=None,
	)
	_pay(lab, "fx_payment", "Sales Invoice", si.name, source_rate=EUR_PAYMENT_RATE)


def fx_invoice_legacy(lab):
	_cancel(lab, "fx_payment")


def stock_sale(lab):
	ctx = lab.ctx
	pr = frappe.get_doc(
		{
			"doctype": "Purchase Receipt",
			"company": ctx.company,
			"supplier": ctx.supplier,
			"currency": ctx.currency,
			"conversion_rate": 1,
			"set_posting_time": 1,
			"posting_date": DATE,
			"items": [
				{
					"item_code": ctx.stock_item,
					"qty": 10,
					"rate": 20,
					"warehouse": ctx.warehouse,
					"cost_center": ctx.cost_center,
				}
			],
		}
	).insert()
	pr.submit()
	lab.reg("stock_receipt", pr)
	_si(lab, "stock_invoice", [(ctx.stock_item, 4, 50)], update_stock=1)


def stock_sale_legacy(lab):
	lab.attempt("return-stock_invoice", lambda: _return(lab, "stock_return", "stock_invoice", qty=1))


def scenario(id, title, flows, build, legacy):
	return {"id": id, "title": title, "flows": flows, "build": build, "legacy": legacy}


SCENARIOS = [
	scenario(
		"si_basic",
		"Sales invoice, 2 x 100, later cancelled",
		["posting", "cancel"],
		si_basic,
		si_basic_legacy,
	),
	scenario(
		"si_tax",
		"Sales invoice, 1 x 1000 with 10% tax, later fully returned",
		["posting", "taxes", "returns"],
		si_tax,
		si_tax_legacy,
	),
	scenario(
		"pi_basic",
		"Purchase invoice, 3 x 50, later paid in full",
		["posting", "allocation"],
		pi_basic,
		pi_basic_legacy,
	),
	scenario(
		"partial_payment",
		"Sales invoice of 500 with a payment of 200, payment later cancelled",
		["allocation", "cancel"],
		partial_payment,
		partial_payment_legacy,
	),
	scenario(
		"advance_reconcile",
		"Advance payment of 300 before an invoice of 300, later reconciled",
		["allocation", "reconciliation"],
		advance_reconcile,
		advance_reconcile_legacy,
	),
	scenario(
		"credit_note_partial",
		"Sales invoice, 2 x 100, with a credit note for 1; both later cancelled",
		["returns", "cancel"],
		credit_note_partial,
		credit_note_partial_legacy,
	),
	scenario(
		"je_basic",
		"Journal entry, expense 75 against cash, later cancelled",
		["posting", "cancel"],
		je_basic,
		je_basic_legacy,
	),
	scenario(
		"fx_invoice",
		"Foreign-currency invoice at rate 1.1, paid at rate 1.2 (exchange gain), payment later cancelled",
		["multi_currency", "allocation", "cancel"],
		fx_invoice,
		fx_invoice_legacy,
	),
	scenario(
		"stock_sale",
		"Purchase receipt of 10 stock items, sales invoice with stock update for 4, later 1 returned",
		["stock_gl", "returns"],
		stock_sale,
		stock_sale_legacy,
	),
]
FLOWS = sorted({flow for s in SCENARIOS for flow in s["flows"]} | {"reports"})
