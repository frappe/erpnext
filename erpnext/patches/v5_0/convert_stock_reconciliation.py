import frappe, json

def execute():
	# stock reco now amendable
	frappe.db.sql("""update tabDocPerm set `amend` = 1 where parent='Stock Reconciliation' and submit = 1""")


	if frappe.db.has_column("Stock Reconciliation", "reconciliation_json"):
		for sr in frappe.db.get_all("Stock Reconciliation", ["name"],
			{"reconciliation_json": ["!=", ""]}):
			start = False
			sr = frappe.get_doc("Stock Reconciliation", sr.name)
			for item in json.loads(sr.reconciliation_json):
				if start:
					if item.get("item_code"):
						sr.append("items", {
							"item_code": item[0],
							"warehouse": item[1],
							"valuation_rate": item[3],
							"qty": item[4]
						})

				elif item[0]=="Item Code":
					start = True


			for item in sr.items:
				item.db_update()

