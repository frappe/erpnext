import frappe


def execute():
	if 'Vehicles' not in frappe.get_active_domains():
			return

	frappe.reload_doc("vehicles", "doctype", "vehicle_log")

	invalid_serial_no_names = frappe.db.sql("""
		select name, vehicle
		from `tabSerial No`
		where ifnull(vehicle, '') != '' and vehicle != name
	""", as_dict=1)
	for d in invalid_serial_no_names:
		print("Renaming Serial No {0} -> {1}".format(d.name, d.vehicle))
		frappe.rename_doc("Serial No", d.name, d.vehicle, force=1)

	print("Updating Vehicle Details Fields in Vehicle Log")
	frappe.db.sql("""
		update `tabVehicle Log` log
		inner join `tabVehicle` v on v.name = log.vehicle
		set log.vehicle_chassis_no = v.chassis_no,
			log.vehicle_engine_no = v.engine_no,
			log.vehicle_license_plate = v.license_plate,
			log.vehicle_color = v.color
	""")

	print("Setting Project as Reference in Vehicle Log")
	frappe.db.sql("""
		update `tabVehicle Log`
		set reference_type = 'Project', reference_name = project
		where ifnull(project, '') != '' and ifnull(reference_name, '') = '' 
	""")

	print("Updating Vehicle Receipt and Vehicle Delivery as reference")
	if frappe.db.has_column('Vehicle Receipt', 'vehicle_log'):
		vehicle_receipt_logs = frappe.db.sql("""
			select name, vehicle_log from `tabVehicle Receipt` where ifnull(vehicle_log, '') != ''
		""", as_dict=1)
	else:
		vehicle_receipt_logs = []

	for d in vehicle_receipt_logs:
		frappe.db.set_value("Vehicle Log", d.vehicle_log, {
			'reference_type': 'Vehicle Receipt', 'reference_name': d.name
		}, None, update_modified=False)

	if frappe.db.has_column('Vehicle Delivery', 'vehicle_log'):
		vehicle_delivery_logs = frappe.db.sql("""
			select name, vehicle_log from `tabVehicle Delivery` where ifnull(vehicle_log, '') != ''
		""", as_dict=1)
	else:
		vehicle_delivery_logs = []

	for d in vehicle_delivery_logs:
		frappe.db.set_value("Vehicle Log", d.vehicle_log, {
			'reference_type': 'Vehicle Delivery', 'reference_name': d.name
		}, None, update_modified=False)

	print("Deleting Vehicle Logs")
	doctypes = (
		'Vehicle Receipt', 'Vehicle Delivery',
		'Vehicle Transfer Letter', 'Vehicle Registration Receipt',
		'Vehicle Service Receipt', 'Vehicle Gate Pass',
	)
	frappe.db.sql("""
		delete from `tabVehicle Log`
		where reference_type in %s
	""", [doctypes])

	frappe.reload_doc("vehicles", "doctype", "vehicle_receipt")
	frappe.reload_doc("vehicles", "doctype", "vehicle_delivery")
	frappe.reload_doc("vehicles", "doctype", "vehicle_registration_receipt")
	frappe.reload_doc("vehicles", "doctype", "vehicle_transfer_letter")
	frappe.reload_doc("vehicles", "doctype", "vehicle_gate_pass")
	frappe.reload_doc("vehicles", "doctype", "vehicle_service_receipt")
	for dt in doctypes:
		print("Making Vehicle Logs for {0}".format(dt))
		docs = frappe.get_all(dt, filters={"docstatus": 1})
		for d in docs:
			doc = frappe.get_doc(dt, d.name)
			doc.make_vehicle_log(do_not_update_customer=True)
			doc.clear_cache()

	print("Updating Vehicle Customers")
	vehicles = frappe.get_all("Vehicle")
	for d in vehicles:
		sr_no = frappe.get_doc("Serial No", d.name)
		last_sle = sr_no.get_last_sle()
		sr_no.set_party_details(last_sle.get("purchase_sle"), last_sle.get("delivery_sle"))

		changes = {
			'customer': sr_no.customer,
			'customer_name': sr_no.customer_name,
			'vehicle_owner': sr_no.vehicle_owner,
			'vehicle_owner_name': sr_no.vehicle_owner_name,
		}
		frappe.db.set_value("Serial No", d.name, changes, None, update_modified=False)
		frappe.db.set_value("Vehicle", d.name, changes, None, update_modified=False)

		sr_no.clear_cache()
