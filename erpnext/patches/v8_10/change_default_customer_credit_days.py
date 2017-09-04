from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "payment_term")
	frappe.reload_doc("accounts", "doctype", "payment_terms_template_detail")
	frappe.reload_doc("accounts", "doctype", "payment_terms_template")

	payment_terms = []
	customers = []
	suppliers = []
	credit_days = frappe.db.sql(
		"SELECT DISTINCT `credit_days`, `credit_days_based_on`, `customer_name` from "
		"`tabCustomer` where credit_days_based_on='Fixed Days' or "
		"credit_days_based_on='Last Day of the Next Month'")

	credit_records = ((record[0], record[1], record[2]) for record in credit_days)
	for days, based_on, customer_name in credit_records:
		payment_term = make_payment_term(days, based_on)
		template = make_template(payment_term)
		payment_terms.append('WHEN `customer_name`="%s" THEN "%s"' % (customer_name, template.template_name))
		customers.append(customer_name)

	begin_query_str = "UPDATE `tabCustomer` SET `payment_terms` = CASE "
	value_query_str = " ".join(payment_terms)
	cond_query_str = " ELSE `payment_terms` END WHERE "

	if customers:
		frappe.db.sql(
			begin_query_str + value_query_str + cond_query_str + '`customer_name` IN %s',
			(customers,)
		)

	# reset
	payment_terms = []
	credit_days = frappe.db.sql(
		"SELECT DISTINCT `credit_days`, `credit_days_based_on`, `supplier_name` from "
		"`tabSupplier` where credit_days_based_on='Fixed Days' or "
		"credit_days_based_on='Last Day of the Next Month'")

	credit_records = ((record[0], record[1], record[2]) for record in credit_days)
	for days, based_on, supplier_name in credit_records:
		if based_on == "Fixed Days":
			pyt_template_name = 'Default Payment Term - N{0}'.format(days)
		else:
			pyt_template_name = 'Default Payment Term - EO2M'

		if not frappe.db.exists("Payment Term Template", pyt_template_name):
			payment_term = make_payment_term(days, based_on)
			template = make_template(payment_term)
		else:
			template = frappe.get_doc("Payment Term Template", pyt_template_name)

		payment_terms.append('WHEN `supplier_name`="%s" THEN "%s"' % (supplier_name, template.template_name))
		suppliers.append(supplier_name)

	begin_query_str = "UPDATE `tabSupplier` SET `payment_terms` = CASE "
	value_query_str = " ".join(payment_terms)
	cond_query_str = " ELSE `payment_terms` END WHERE "

	if suppliers:
		frappe.db.sql(
			begin_query_str + value_query_str + cond_query_str + '`supplier_name` IN %s',
			(suppliers,)
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
		doc.description = 'Net payable by the end of next month'.format(days)
		doc.payment_term_name = 'EO2M'

	doc.save()
	return doc
