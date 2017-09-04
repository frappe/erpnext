import frappe
from patches.v8_10.change_default_customer_credit_days import make_payment_term, make_template


def execute():
	payment_terms = []
	supplier_types = []

	credit_days = frappe.db.sql(
		"SELECT DISTINCT `credit_days`, `credit_days_based_on`, `supplier_type` from "
		"`tabSupplier Type` where credit_days_based_on='Fixed Days' or "
		"credit_days_based_on='Last Day of the Next Month'")

	records = ((record[0], record[1], record[2]) for record in credit_days)

	for days, based_on, supplier_type in records:
		if based_on == "Fixed Days":
			pyt_term_name = 'N{0}'.format(days)
		else:
			pyt_term_name = 'EO2M'

		if not frappe.db.exists("Payment Term", pyt_term_name):
			payment_term = make_payment_term(days, based_on)
			make_template(payment_term)
		else:
			payment_term = frappe.get_doc("Payment Term", pyt_term_name)

		payment_terms.append('WHEN `supplier_name`="%s" THEN "%s"' % (supplier_type, payment_term.payment_term_name))
		supplier_types.append(supplier_type)

	begin_query_str = "UPDATE `tabSupplier` SET `payment_terms` = CASE "
	value_query_str = " ".join(payment_terms)
	cond_query_str = " ELSE `payment_terms` END WHERE "

	if supplier_types:
		frappe.db.sql(
			begin_query_str + value_query_str + cond_query_str + '`supplier_name` IN %s',
			(supplier_types,)
		)
