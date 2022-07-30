import frappe


def execute():
	frappe.db.sql("""
		update `tabVehicle` v
		inner join `tabItem` i on i.name = v.item_code
		set v.image = i.image
	""")

	if 'Vehicles' in frappe.get_active_domains():
			frappe.db.sql("""
				update `tabProject` p
				inner join `tabVehicle` v on v.name = p.applies_to_vehicle
				set p.image = v.image
		""")
