import frappe
from frappe import qb
from frappe.query_builder.custom import ConstantColumn


def get_advance_doctypes() -> list:
	return frappe.get_hooks("advance_payment_receivable_doctypes") + frappe.get_hooks(
		"advance_payment_payable_doctypes"
	)


def get_payments_with_so_po_reference() -> list:
	advance_payment_entries = []
	advance_doctypes = get_advance_doctypes()
	per = qb.DocType("Payment Entry Reference")
	payments_with_reference = (
		qb.from_(per)
		.select(per.parent)
		.distinct()
		.where(per.reference_doctype.isin(advance_doctypes) & per.docstatus.eq(1))
		.run()
	)
	if payments_with_reference:
		pe = qb.DocType("Payment Entry")
		advance_payment_entries = (
			qb.from_(pe)
			.select(ConstantColumn("Payment Entry").as_("doctype"))
			.select(pe.name)
			.where(pe.name.isin(payments_with_reference) & pe.docstatus.eq(1))
			.run(as_dict=True)
		)

	return advance_payment_entries


def get_journals_with_so_po_reference() -> list:
	advance_journal_entries = []
	advance_doctypes = get_advance_doctypes()
	jea = qb.DocType("Journal Entry Account")
	journals_with_reference = (
		qb.from_(jea)
		.select(jea.parent)
		.distinct()
		.where(jea.reference_type.isin(advance_doctypes) & jea.docstatus.eq(1))
		.run()
	)
	if journals_with_reference:
		je = qb.DocType("Journal Entry")
		advance_journal_entries = (
			qb.from_(je)
			.select(ConstantColumn("Journal Entry").as_("doctype"))
			.select(je.name)
			.where(je.name.isin(journals_with_reference) & je.docstatus.eq(1))
			.run(as_dict=True)
		)

	return advance_journal_entries


def make_advance_ledger_entries(vouchers: list):
	for x in vouchers:
		frappe.get_doc(x.doctype, x.name).make_advance_payment_ledger_entries()


def execute():
	"""
	Description:
	Create Advance Payment Ledger Entry for all Payments made against Sales / Purchase Orders
	"""
	frappe.db.truncate("Advance Payment Ledger Entry")
	payment_entries = get_payments_with_so_po_reference()
	make_advance_ledger_entries(payment_entries)

	journals = get_journals_with_so_po_reference()
	make_advance_ledger_entries(journals)
