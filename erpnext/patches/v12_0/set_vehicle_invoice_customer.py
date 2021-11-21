import frappe

def execute():
	frappe.reload_doc('vehicles', 'doctype', 'vehicle')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_delivery')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_movement')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_movement_detail')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_booking_order')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_receipt')

	invoices = frappe.db.sql("""
		select inv.name, vbo.customer, vbo.financer, vbo.customer_name, vbo.financer_name, vbo.lessee_name,
			vbo.finance_type
		from `tabVehicle Invoice` inv
		inner join `tabVehicle Booking Order` vbo on vbo.name = inv.vehicle_booking_order
		where ifnull(inv.customer, '') = ''
	""", as_dict=1)

	for d in invoices:
		values = frappe._dict()

		if d.finance_type == "Leased":
			values.customer = d.financer
			values.customer_name = d.customer_name
		elif d.finance_type == "Financed":
			values.customer = d.customer
			values.financer = d.financer
			values.customer_name = d.customer_name
			values.financer_name = d.financer_name
			values.lessee_name = d.lessee_name
		else:
			values.customer = d.customer
			values.customer_name = d.customer_name

		frappe.db.set_value("Vehicle Invoice", d.name, values, None, update_modified=False)

	# Set Invoice Customer Name
	frappe.db.sql("""
		update `tabVehicle Invoice Delivery` d
		inner join `tabVehicle Invoice` inv on inv.name = d.vehicle_invoice
		set d.invoice_customer_name = inv.customer_name
	""")

	frappe.db.sql("""
		update `tabVehicle Invoice Movement Detail` d
		inner join `tabVehicle Invoice` inv on inv.name = d.vehicle_invoice
		set d.invoice_customer_name = inv.customer_name
	""")

	# Set Booking Customer Name
	frappe.db.sql("""
		update `tabVehicle Invoice Movement Detail` d
		inner join `tabVehicle Booking Order` vbo on vbo.name = d.vehicle_booking_order
		set d.booking_customer_name = vbo.customer_name
	""")
	frappe.db.sql("""
		update `tabVehicle Receipt` d
		inner join `tabVehicle Booking Order` vbo on vbo.name = d.vehicle_booking_order
		set d.booking_customer_name = vbo.customer_name
	""")

	# Set Invoice Title
	frappe.db.sql("""
		update `tabVehicle Invoice` d
		set d.title = CONCAT_WS(' - ', d.customer_name, d.bill_no)
		where ifnull(d.customer_name, '') != '' and ifnull(d.bill_no, '') != ''
	""")
	frappe.db.sql("""
		update `tabVehicle Invoice Delivery` d
		set d.title = CONCAT_WS(' - ', d.customer_name, d.bill_no)
		where ifnull(d.customer_name, '') != '' and ifnull(d.bill_no, '') != ''
	""")
