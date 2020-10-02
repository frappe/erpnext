import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "transaction_type")

	frappe.db.sql("update `tabTransaction Type` set selling = 1 where buying = 0 and selling = 0")

	to_update = frappe.db.sql("""
		select name, default_cost_center
		from `tabTransaction Type`
		where ifnull(default_cost_center, '') != ''
	""", as_dict=1)

	for d in to_update:
		cost_center_company = frappe.db.get_value("Cost Center", d.default_cost_center, "company")
		if cost_center_company:
			doc = frappe.get_doc("Transaction Type", d.name)

			existing = doc.get('accounts', filters={'company': cost_center_company})
			if existing:
				existing[0].cost_center = d.default_cost_center
			else:
				doc.append('accounts', {
					'company': cost_center_company,
					'cost_center': d.default_cost_center
				})

			doc.save()
