import frappe


def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return

	dts = [
		'Vehicle',
		'Vehicle Booking Order',
		'Vehicle Receipt',
		'Vehicle Delivery',
		'Vehicle Invoice Receipt',
		'Vehicle Invoice Delivery',
		'Vehicle Transfer Letter',
		'Vehicle Allocation',
	]

	for dt in dts:
		frappe.reload_doctype(dt)

		frappe.db.sql("""
			update `tab{0}` t
			inner join `tabItem` vi on vi.name = t.item_code
			inner join `tabItem` mi on mi.name = vi.variant_of
			set t.variant_of = mi.name, t.variant_of_name = mi.item_name
		""".format(dt))
