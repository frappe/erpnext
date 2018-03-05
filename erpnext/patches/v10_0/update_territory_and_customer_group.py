import frappe
from frappe.model.rename_doc import get_fetch_fields

def execute():
	ignore_doctypes = ["Lead", "Opportunity", "POS Profile", "Tax Rule", "Pricing Rule"]
	customers = frappe.get_all('Customer', fields=["name", "customer_group"])

	customer_group_fetch = get_fetch_fields('Customer', 'Customer Group', ignore_doctypes)

	batch_size = 1000
	for i in range(0, len(customers), batch_size):
		batch_customers = customers[i:i + batch_size]
		for d in customer_group_fetch:
			when_then = []
			for customer in batch_customers:
				when_then.append('''
					WHEN `{master_fieldname}` = "{docname}" and {linked_to_fieldname} != "{value}"
					THEN "{value}"
				'''.format(
					master_fieldname=d["master_fieldname"],
					linked_to_fieldname=d["linked_to_fieldname"],
					docname=frappe.db.escape(frappe.as_unicode(customer.name)),
					value=frappe.db.escape(frappe.as_unicode(customer.get("customer_group")))))

			frappe.db.sql("""
				update
					`tab{doctype}`
				set
					{linked_to_fieldname} = CASE {when_then_cond}  ELSE `{linked_to_fieldname}` END
			""".format(
				doctype = d['doctype'],
				when_then_cond=" ".join(when_then),
				linked_to_fieldname=d.linked_to_fieldname
			))
