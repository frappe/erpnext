from __future__ import unicode_literals
import frappe


def execute():
	payment_terms = []
	customers = []
	credit_days = frappe.db.sql(
		"SELECT DISTINCT `credit_days`, `credit_days_based_on`, `customer_name` from "
		"`tabCustomer` where credit_days_based_on='Fixed Days' or "
		"credit_days_based_on='Last Day of the Next Month'")

	credit_records = ((record[0], record[1], record[2]) for record in credit_days)
	for days, based_on, customer_name in credit_records:
		payment_term = make_payment_term(days, based_on)
		payment_terms.append('WHEN `customer_name`="%s" THEN "%s"' % (customer_name, payment_term.payment_term_name))
		customers.append(customer_name)
		make_template(payment_term)

	begin_query_str = "UPDATE `tabCustomer` SET `payment_terms` = CASE "
	value_query_str = " ".join(payment_terms)
	cond_query_str = " ELSE `payment_terms` END WHERE "

	frappe.db.sql(
		begin_query_str + value_query_str + cond_query_str + '`customer_name` IN %s',
		(customers,)
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
	template.terms = [doc]
	template.save()


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
		doc.description = 'Net payable by the end of next month'.format(days)
		doc.payment_term_name = 'EO2M'

	doc.save()
	return doc
