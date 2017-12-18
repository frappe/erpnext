from __future__ import unicode_literals
import frappe
from frappe.utils import update_progress_bar

def execute():
	frappe.reload_doc("accounts", "doctype", "gl_entry")
	frappe.reload_doc("accounts", "doctype", "payment_entry_reference")
	frappe.reload_doc("accounts", "doctype", "journal_entry_account")
	
	print "Updating Due Date in GL Entry, Journal Entry and Payment Entry"
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		invoice_due_dates = frappe.db.sql("""select name, due_date from `tab{0}`
			where docstatus=1 order by name""".format(doctype))

		# update gle
		count = 0
		total_count = len(invoice_due_dates)
		batch_size = 1000
		
		while(count < total_count):
			update_progress_bar("Based on {0}".format(doctype), count, total_count)
			sub_set = invoice_due_dates[count:count+batch_size]
			invoices = [d[0] for d in sub_set]

			update_gl_entries(doctype, invoices, sub_set)
			update_payment_entries(doctype, invoices, sub_set)
		
			count += batch_size

def update_gl_entries(doctype, invoices, invoice_due_dates):
	when_then = get_when_then_for_gle(doctype, invoice_due_dates)

	frappe.db.sql("""
		UPDATE `tabGL Entry`
		SET due_date = CASE
			%s
			ELSE `due_date` END
		WHERE
			(
				(voucher_type = %s and voucher_no in (%s))
				or (voucher_type in ('Journal Entry', 'Payment Entry')
					and against_voucher in (%s))
			)
			and ifnull(party, '') != ''
			and ifnull(due_date, '') = ''
	""" % (when_then, '%s', ', '.join(['%s']*len(invoices)), ', '.join(['%s']*len(invoices))),
		tuple([doctype] + invoices + invoices))

def get_when_then_for_gle(doctype, data):
	cond = ""
	for d in data:
		cond += """
		 	WHEN (
				(voucher_type = '{voucher_type}' and voucher_no = '{voucher_no}')
				or (voucher_type in ('Journal Entry', 'Payment Entry')
					and against_voucher = '{voucher_no}')
			) THEN '{date}'
		""".format(voucher_type=doctype, voucher_no=frappe.db.escape(d[0]), date=d[1])

	return cond

def update_payment_entries(ref_doctype, invoices, invoice_due_dates):
	for d in (
		("Payment Entry Reference", "reference_doctype", "due_date"),
		("Journal Entry Account", "reference_type", "reference_due_date")):

		when_then = get_when_then_for_payment_entries(ref_doctype, d[1], invoice_due_dates)

		frappe.db.sql("""
			UPDATE `tab{doctype}`
			SET {due_date_field} = CASE
				{when_then}
				ELSE `{due_date_field}` END
			WHERE
				{ref_doctype_fieldname} = '{ref_doctype}'
				and reference_name in ({reference_names})
				and ifnull({due_date_field}, '') = ''
		""".format(
			doctype = d[0],
			due_date_field = d[2],
			when_then = when_then,
			ref_doctype_fieldname = d[1],
			ref_doctype = ref_doctype,
			reference_names = ', '.join(['%s']*len(invoices))
		), tuple(invoices))

def get_when_then_for_payment_entries(ref_doctype, ref_doctype_fieldname, data):
	cond = ""
	for d in data:
		cond += """
		 	WHEN {ref_doctype_fieldname} = '{ref_doctype}'
				and reference_name = '{voucher_no}'
			THEN '{date}'
		""".format(
			ref_doctype_fieldname=ref_doctype_fieldname,
			ref_doctype=ref_doctype,
			voucher_no=frappe.db.escape(d[0]),
			date=d[1])

	return cond