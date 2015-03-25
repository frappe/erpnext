import frappe, json

def execute():
	# stock reco now amendable
	frappe.db.sql("""update tabDocPerm set `amend` = 1 where parent='Stock Reconciliation' and submit = 1""")

	frappe.reload_doc("stock", "doctype", "stock_reconciliation_item")
	frappe.reload_doctype("Stock Reconciliation")
	
	if frappe.db.has_column("Stock Reconciliation", "reconciliation_json"):
		for sr in frappe.db.get_all("Stock Reconciliation", ["name"],
			{"reconciliation_json": ["!=", ""]}):
			start = False
			sr = frappe.get_doc("Stock Reconciliation", sr.name)
			for row in json.loads(sr.reconciliation_json):
				if start:
					sr.append("items", {
						"item_code": row[0],
						"warehouse": row[1],
						"qty": row[2] if len(row) > 2 else None,
						"valuation_rate": row[3] if len(row) > 3 else None
					})

				elif row[0]=="Item Code":
					start = True


			for item in sr.items:
				item.db_update()

