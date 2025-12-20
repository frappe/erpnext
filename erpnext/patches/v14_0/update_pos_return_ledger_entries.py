import frappe
from frappe import qb

from erpnext.accounts.utils import update_voucher_outstanding


def get_valid_against_voucher_ref(pos_returns):
	sinv = qb.DocType("Sales Invoice")
	res = (
		qb.from_(sinv)
		.select(sinv.name, sinv.return_against)
		.where(sinv.name.isin(pos_returns) & sinv.return_against.notnull())
		.orderby(sinv.name)
		.run(as_dict=True)
	)
	return res


def build_dict_of_valid_against_reference(pos_returns):
	_against_ref_dict = frappe._dict()
	res = get_valid_against_voucher_ref(pos_returns)
	for x in res:
		_against_ref_dict[x.name] = x.return_against
	return _against_ref_dict


def fix_incorrect_against_voucher_ref(affected_pos_returns):
	if affected_pos_returns:
		valid_against_voucher_dict = build_dict_of_valid_against_reference(affected_pos_returns)

		gle = qb.DocType("GL Entry")
		gles_with_invalid_against = (
			qb.from_(gle)
			.select(gle.name, gle.voucher_no)
			.where(
				gle.voucher_no.isin(affected_pos_returns)
				& gle.against_voucher.notnull()
				& gle.against_voucher.eq(gle.voucher_no)
				& gle.is_cancelled.eq(0)
			)
			.run(as_dict=True)
		)
		# Update GL
		if gles_with_invalid_against:
			for gl in gles_with_invalid_against:
				frappe.db.set_value(
					"GL Entry",
					gl.name,
					"against_voucher",
					valid_against_voucher_dict[gl.voucher_no],
				)

		# Update Payment Ledger
		ple = qb.DocType("Payment Ledger Entry")
		for x in affected_pos_returns:
			qb.update(ple).set(ple.against_voucher_no, valid_against_voucher_dict[x]).where(
				ple.voucher_no.eq(x) & ple.delinked.eq(0)
			).run()


def get_pos_returns_with_invalid_against_ref():
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

		if gl_against_references:
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
				return [x[0] for x in invalid_references]
	return None


def update_outstanding_for_affected(affected_pos_returns):
	if affected_pos_returns:
		sinv = qb.DocType("Sales Invoice")
		pos_with_accounts = (
			qb.from_(sinv)
			.select(sinv.return_against, sinv.debit_to, sinv.customer)
			.where(sinv.name.isin(affected_pos_returns))
			.run(as_dict=True)
		)

		for x in pos_with_accounts:
			update_voucher_outstanding("Sales Invoice", x.return_against, x.debit_to, "Customer", x.customer)


def execute():
	affected_pos_returns = get_pos_returns_with_invalid_against_ref()
	fix_incorrect_against_voucher_ref(affected_pos_returns)
	update_outstanding_for_affected(affected_pos_returns)
