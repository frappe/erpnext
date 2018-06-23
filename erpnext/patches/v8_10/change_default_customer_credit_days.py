from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("selling", "doctype", "customer")
	frappe.reload_doc("buying", "doctype", "supplier")
	frappe.reload_doc("setup", "doctype", "supplier_type")
	frappe.reload_doc("accounts", "doctype", "payment_term")
	frappe.reload_doc("accounts", "doctype", "payment_terms_template_detail")
	frappe.reload_doc("accounts", "doctype", "payment_terms_template")

	payment_terms = []
	records = []
	for doctype in ("Customer", "Supplier", "Supplier Type"):
		credit_days = frappe.db.sql("""
			SELECT DISTINCT `credit_days`, `credit_days_based_on`, `name`
			from `tab{0}`
			where
				((credit_days_based_on='Fixed Days' or credit_days_based_on is null)
					and credit_days is not null)
				or credit_days_based_on='Last Day of the Next Month'
		""".format(doctype))

		credit_records = ((record[0], record[1], record[2]) for record in credit_days)
		for days, based_on, party_name in credit_records:
			if based_on == "Fixed Days":
				pyt_template_name = 'Default Payment Term - N{0}'.format(days)
			else:
				pyt_template_name = 'Default Payment Term - EO2M'

			if not frappe.db.exists("Payment Terms Template", pyt_template_name):
				payment_term = make_payment_term(days, based_on)
				template = make_template(payment_term)
			else:
				template = frappe.get_doc("Payment Terms Template", pyt_template_name)

			payment_terms.append('WHEN `name`="%s" THEN "%s"' % (frappe.db.escape(party_name), template.template_name))
			records.append(frappe.db.escape(party_name))

		begin_query_str = "UPDATE `tab{0}` SET `payment_terms` = CASE ".format(doctype)
		value_query_str = " ".join(payment_terms)
		cond_query_str = " ELSE `payment_terms` END WHERE "

		if records:
			frappe.db.sql(
				begin_query_str + value_query_str + cond_query_str + '`name` IN %s',
				(records,)
			)


def make_template(payment_term):
	doc = frappe.new_doc('Payment Terms Template Detail')
	doc.payment_term = payment_term.payment_term_name
	doc.due_date_based_on = payment_term.due_date_based_on
	doc.invoice_portion = payment_term.invoice_portion
	doc.description = payment_term.description
	doc.credit_days = payment_term.credit_days
	doc.credit_months = payment_term.credit_months

	template = frappe.new_doc('Payment Terms Template')
	template.template_name = 'Default Payment Term - {0}'.format(payment_term.payment_term_name)
	template.append('terms', doc)
	template.save()

	return template


def make_payment_term(days, based_on):
	based_on_map = {
		'Fixed Days': 'Day(s) after invoice date',
		'Last Day of the Next Month': 'Month(s) after the end of the invoice month'
	}

	doc = frappe.new_doc('Payment Term')
	doc.due_date_based_on = based_on_map.get(based_on)
	doc.invoice_portion = 100

	if based_on == 'Fixed Days':
		doc.credit_days = days
		doc.description = 'Net payable within {0} days'.format(days)
		doc.payment_term_name = 'N{0}'.format(days)
	else:
		doc.credit_months = 1
		doc.description = 'Net payable by the end of next month'
		doc.payment_term_name = 'EO2M'

	doc.save()
	return doc
