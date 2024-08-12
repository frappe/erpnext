import frappe
from frappe import qb


def execute():
	sinv = qb.DocType("Sales Invoice")
	pos_returns_without_self = (
		qb.from_(sinv)
		.select(sinv.name)
		.where(
			sinv.docstatus.eq(1)
			& sinv.is_pos.eq(1)
			& sinv.is_return.eq(1)
			& sinv.return_against.notnull()
			& sinv.update_outstanding_for_self.eq(0)
		)
		.run()
	)
	if pos_returns_without_self:
		pos_returns_without_self = [x[0] for x in pos_returns_without_self]

		gle = qb.DocType("GL Entry")
		gl_against_references = (
			qb.from_(gle)
			.select(gle.voucher_no, gle.against_voucher)
			.where(
				gle.voucher_no.isin(pos_returns_without_self)
				& gle.against_voucher.notnull()
				& gle.against_voucher.eq(gle.voucher_no)
				& gle.is_cancelled.eq(0)
			)
			.run()
		)

		_vouchers = list(set([x[0] for x in gl_against_references]))
		invoice_return_against = (
			qb.from_(sinv)
			.select(sinv.name, sinv.return_against)
			.where(sinv.name.isin(_vouchers) & sinv.return_against.notnull())
			.orderby(sinv.name)
			.run()
		)

		valid_references = set(invoice_return_against)
		actual_references = set(gl_against_references)

		invalid_references = actual_references.difference(valid_references)

		if invalid_references:
			# Repost Accounting Ledger
			pos_for_reposting = (
				qb.from_(sinv)
				.select(sinv.company, sinv.name)
				.where(sinv.name.isin([x[0] for x in invalid_references]))
				.run(as_dict=True)
			)
			for x in pos_for_reposting:
				ral = frappe.new_doc("Repost Accounting Ledger")
				ral.company = x.company
				ral.append("vouchers", {"voucher_type": "Sales Invoice", "voucher_no": x.name})
				ral.save().submit()
