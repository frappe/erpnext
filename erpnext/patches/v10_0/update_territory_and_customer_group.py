import frappe
from frappe.model.rename_doc import get_fetch_fields

def execute():
	ignore_doctypes = ["Lead", "Opportunity", "POS Profile", "Tax Rule", "Pricing Rule"]
	customers = frappe.get_all('Customer', fields=["name", "territory", "customer_group"])

	territory_fetch = get_fetch_fields('Customer', 'Territory', ignore_doctypes)
	customer_group_fetch = get_fetch_fields('Customer', 'Customer Group', ignore_doctypes)

	batch_size = 1000
	for i in range(0, len(customers), batch_size):
		batch_customers = customers[i:i + batch_size]
		for source_fieldname, linked_doctypes_info in [["customer_group", customer_group_fetch], ["territory", territory_fetch]]:
			for d in linked_doctypes_info:
				when_then = []
				for customer in batch_customers:
					when_then.append('''
						WHEN `{master_fieldname}` = "{docname}" and {linked_to_fieldname} != "{value}"
						THEN "{value}"
					'''.format(
						master_fieldname=d["master_fieldname"],
						linked_to_fieldname=d["linked_to_fieldname"],
						docname=frappe.db.escape(customer.name).encode("utf-8"),
						value=frappe.db.escape(customer.get(source_fieldname)).encode("utf-8")))
				
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
