import frappe

def execute():
	frappe.reload_doc("stock", "doctype", "price_list_country")
	frappe.reload_doc("accounts", "doctype", "shipping_rule_country")
	frappe.reload_doctype("Price List")
	frappe.reload_doctype("Shipping Rule")
	frappe.reload_doctype("shopping_cart", "doctype", "shopping_cart_settings")

	# for price list
	countries = frappe.db.sql_list("select name from tabCountry")

	for doctype in ("Price List", "Shipping Rule"):
		for at in frappe.db.sql("""select name, parent, territory from `tabApplicable Territory` where
			parenttype = %s """, doctype, as_dict=True):
			if at.territory in countries:
				parent = frappe.get_doc(doctype, at.parent)
				if not parent.countries:
					parent.append("countries", {"country": at.territory})
				parent.save()


	frappe.delete_doc("DocType", "Applicable Territory")
