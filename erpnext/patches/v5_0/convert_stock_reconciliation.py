import frappe, json

def execute():
	# stock reco now amendable
	frappe.db.sql("""update tabDocPerm set `amend` = 1 where parent='Stock Reconciliation' and submit = 1""")

	if frappe.db.has_column("Stock Reconciliation", "reconciliation_json"):
		for sr in frappe.db.get_all("Stock Reconciliation", ["name"],
			{"reconciliation_json": ["!=", ""]}):
			sr = frappe.get_doc("Stock Reconciliation", sr.name)
			for item in json.loads(sr.reconciliation_json):
				sr.append("items", {
					"item_code": item.item_code,
					"warehouse": item.warehouse,
					"valuation_rate": item.valuation_rate,
					"qty": item.qty
				})

			for item in sr.items:
				item.db_update()

