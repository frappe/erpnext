from frappe import qb


def execute():
	# Set "update_outstanding_for_self" flag in Credit/Debit Notes
	# Fetch Credit/Debit notes that does have 'return_against' but still post ledger entries against themselves.

	gle = qb.DocType("GL Entry")

	# Use hardcoded 'creation' date to isolate Credit/Debit notes created post v14 backport
	# https://github.com/frappe/erpnext/pull/39497
	creation_date = "2024-01-25"

	si = qb.DocType("Sales Invoice")

	# unset flag, as migration would have set it for all records, as the field was introduced with default '1'
	qb.update(si).set(si.update_outstanding_for_self, False).run()

	if cr_notes := (
		qb.from_(si)
		.select(si.name)
		.where(
			(si.creation.gte(creation_date))
			& (si.docstatus == 1)
			& (si.is_return.eq(True))
			& (si.return_against.notnull())
		)
		.run()
	):
		cr_notes = [x[0] for x in cr_notes]
		if docs_that_require_update := (
			qb.from_(gle)
			.select(gle.voucher_no)
			.distinct()
			.where((gle.voucher_no.isin(cr_notes)) & (gle.voucher_no == gle.against_voucher))
			.run()
		):
			docs_that_require_update = [x[0] for x in docs_that_require_update]
			qb.update(si).set(si.update_outstanding_for_self, True).where(
				si.name.isin(docs_that_require_update)
			).run()

	pi = qb.DocType("Purchase Invoice")

	# unset flag, as migration would have set it for all records, as the field was introduced with default '1'
	qb.update(pi).set(pi.update_outstanding_for_self, False).run()

	if dr_notes := (
		qb.from_(pi)
		.select(pi.name)
		.where(
			(pi.creation.gte(creation_date))
			& (pi.docstatus == 1)
			& (pi.is_return.eq(True))
			& (pi.return_against.notnull())
		)
		.run()
	):
		dr_notes = [x[0] for x in dr_notes]
		if docs_that_require_update := (
			qb.from_(gle)
			.select(gle.voucher_no)
			.distinct()
			.where((gle.voucher_no.isin(dr_notes)) & (gle.voucher_no == gle.against_voucher))
			.run()
		):
			docs_that_require_update = [x[0] for x in docs_that_require_update]
			qb.update(pi).set(pi.update_outstanding_for_self, True).where(
				pi.name.isin(docs_that_require_update)
			).run()
