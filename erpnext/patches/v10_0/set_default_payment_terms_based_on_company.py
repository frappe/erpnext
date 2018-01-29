from __future__ import unicode_literals
import frappe
from erpnext.patches.v8_10.change_default_customer_credit_days import make_payment_term, make_template

def execute():
	frappe.reload_doc("setup", "doctype", "company")

	credit_records = frappe.db.sql("""
		SELECT DISTINCT `credit_days`, `credit_days_based_on`, `name`
		from `tabCompany`
		where
			(credit_days_based_on='Fixed Days' and credit_days is not null)
			or credit_days_based_on='Last Day of the Next Month'
	""", as_dict=1)

	for d in credit_records:
		template = create_payment_terms_template(d)

		frappe.db.sql("""
			update `tabCompany`
			set `payment_terms` = %s
			where name = %s
		""", (template, d.name))

def create_payment_terms_template(data):
	if data.credit_days_based_on == "Fixed Days":
		pyt_template_name = 'Default Payment Term - N{0}'.format(data.credit_days)
	else:
		pyt_template_name = 'Default Payment Term - EO2M'

	if not frappe.db.exists("Payment Terms Template", pyt_template_name):
		payment_term = make_payment_term(data.credit_days, data.credit_days_based_on)
		template = make_template(payment_term)
	else:
		template = frappe.get_doc("Payment Terms Template", pyt_template_name)
	return template