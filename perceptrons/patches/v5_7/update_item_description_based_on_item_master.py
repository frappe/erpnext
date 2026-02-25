import frappe


def execute():
	name = frappe.db.sql(
		""" select name from `tabPatch Log` \
		where \
			patch like 'execute:frappe.db.sql("update `tabProduction Order` pro set description%' """
	)
	if not name:
		frappe.db.sql(
			"update `tabProduction Order` pro \
			set \
				description = (select description from tabItem where name=pro.production_item) \
			where \
				ifnull(description, '') = ''"
		)
