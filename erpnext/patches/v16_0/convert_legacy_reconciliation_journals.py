import frappe


def execute():
	"""Migrate legacy reconciliation journals to the unified bridge voucher type.

	Before the payment-reconciliation refactor, settling an invoice against a
	credit/debit note minted a system-generated Journal Entry of voucher_type
	"Credit Note"/"Debit Note" (the old `reconcile_dr_cr_note`). The refactor
	replaced that with the "Reconciliation Journal" bridge, and document cancellation
	now unwinds those bridges via `unwind_reconciliation` instead of the
	dedicated `cancel_system_generated_credit_debit_notes` shim (now removed).

	Relabel the existing legacy JEs to "Reconciliation Journal" so cancelling a linked
	invoice/note still unwinds them. Scoped to `is_system_generated` rows so manually
	created Credit/Debit Note JEs are untouched. Only submitted (docstatus 1) rows
	matter — cancelled ones have nothing left to unwind, and the affected reports only
	look at submitted rows.
	"""
	je = frappe.qb.DocType("Journal Entry")
	legacy = (
		frappe.qb.from_(je)
		.select(je.name)
		.where(
			(je.is_system_generated == 1)
			& (je.docstatus == 1)
			& (je.voucher_type.isin(["Credit Note", "Debit Note"]))
		)
	).run(pluck=True)
	if not legacy:
		return

	frappe.qb.update(je).set(je.voucher_type, "Reconciliation Journal").where(je.name.isin(legacy)).run()

	# GL rows copy the journal's type into voucher_subtype; keep them in step
	gle = frappe.qb.DocType("GL Entry")
	(
		frappe.qb.update(gle)
		.set(gle.voucher_subtype, "Reconciliation Journal")
		.where((gle.voucher_type == "Journal Entry") & gle.voucher_no.isin(legacy))
	).run()
