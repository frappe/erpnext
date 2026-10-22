import frappe
from frappe import qb
from frappe.query_builder.functions import IfNull
from frappe.utils import flt


def execute():
	"""Exchange gain/loss journals of a payment row stored the row's number; they now store
	its name. A number can repeat on one invoice once rows are removed, so the row whose
	gain/loss matches the journal wins, else the oldest."""
	je = qb.DocType("Journal Entry")
	gain_loss = qb.DocType("Journal Entry Account").as_("gain_loss")
	party = qb.DocType("Journal Entry Account").as_("party")
	per = qb.DocType("Payment Entry Reference")

	candidates = (
		qb.from_(je)
		.inner_join(gain_loss)
		.on(gain_loss.parent == je.name)
		.inner_join(party)
		.on((party.parent == je.name) & (party.name != gain_loss.name))
		.inner_join(per)
		.on(
			(per.parent == gain_loss.reference_name)
			& (per.reference_doctype == party.reference_type)
			& (per.reference_name == party.reference_name)
		)
		.select(
			je.name.as_("journal"),
			gain_loss.name.as_("gain_loss_line"),
			party.name.as_("party_line"),
			gain_loss.reference_detail_no.as_("row_no"),
			(gain_loss.debit + gain_loss.credit).as_("amount"),
			per.name.as_("row"),
			per.idx,
			per.exchange_gain_loss,
		)
		.where(
			(je.voucher_type == "Exchange Gain Or Loss")
			& (je.docstatus == 1)
			& (je.is_system_generated == 1)
			& (gain_loss.reference_type == "Payment Entry")
			& (IfNull(gain_loss.party, "") == "")
		)
		.orderby(per.creation)
	).run(as_dict=True)

	updates, matched = {}, set()
	for candidate in candidates:
		if candidate.row_no != str(candidate.idx) or candidate.journal in matched:
			continue
		if flt(abs(candidate.exchange_gain_loss), 2) == flt(candidate.amount, 2):
			matched.add(candidate.journal)
		elif candidate.gain_loss_line in updates:
			continue  # keep the oldest row until one with the same gain/loss turns up
		for line in (candidate.gain_loss_line, candidate.party_line):
			updates[line] = {"reference_detail_no": candidate.row}

	frappe.db.bulk_update("Journal Entry Account", updates, update_modified=False)
