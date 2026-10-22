import frappe
from frappe import qb
from frappe.query_builder.functions import IfNull
from frappe.utils import flt


def execute():
	"""Point old gain/loss journals of payments at their reference row's name, not its number."""
	je = qb.DocType("Journal Entry")
	gain_loss = qb.DocType("Journal Entry Account").as_("gain_loss")
	party = qb.DocType("Journal Entry Account").as_("party")

	# one row per journal: the party line names the invoice, the gain/loss line the payment and row number
	journals = (
		qb.from_(je)
		.inner_join(gain_loss)
		.on(gain_loss.parent == je.name)
		.inner_join(party)
		.on((party.parent == je.name) & (party.name != gain_loss.name))
		.select(
			gain_loss.name.as_("gain_loss_line"),
			party.name.as_("party_line"),
			gain_loss.reference_name.as_("payment"),
			party.reference_type.as_("invoice_type"),
			party.reference_name.as_("invoice"),
			gain_loss.reference_detail_no.as_("row_no"),
			(gain_loss.debit + gain_loss.credit).as_("amount"),
		)
		.where(
			(je.voucher_type == "Exchange Gain Or Loss")
			& (je.docstatus == 1)
			& (je.is_system_generated == 1)
			& (gain_loss.reference_type == "Payment Entry")
			& (IfNull(gain_loss.party, "") == "")
		)
	).run(as_dict=True)
	if not journals:
		return

	rows = {}
	for row in frappe.get_all(
		"Payment Entry Reference",
		filters={"parent": ("in", list({journal.payment for journal in journals}))},
		fields=["name", "parent", "reference_doctype", "reference_name", "idx", "exchange_gain_loss"],
		order_by="creation",
	):
		rows.setdefault((row.parent, row.reference_doctype, row.reference_name, str(row.idx)), []).append(row)

	updates = {}
	for journal in journals:
		same_number = rows.get((journal.payment, journal.invoice_type, journal.invoice, journal.row_no))
		if not same_number:
			continue  # already on a row name, or no such row
		# a number repeats once rows are removed; the row whose gain/loss was booked wins, else the oldest
		row = next(
			(r for r in same_number if flt(abs(r.exchange_gain_loss), 2) == flt(journal.amount, 2)),
			same_number[0],
		)
		updates[journal.gain_loss_line] = updates[journal.party_line] = {"reference_detail_no": row.name}

	frappe.db.bulk_update("Journal Entry Account", updates, update_modified=False)
