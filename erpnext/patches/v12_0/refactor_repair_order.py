import frappe
from frappe.utils import cint


def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return

	frappe.reload_doc("vehicles", "doctype", "vehicle_receipt")
	frappe.reload_doc("vehicles", "doctype", "vehicle_delivery")
	frappe.reload_doc("vehicles", "doctype", "vehicle_workshop")
	frappe.reload_doc("vehicles", "doctype", "vehicle_service_receipt")
	frappe.reload_doc("vehicles", "doctype", "vehicle_gate_pass")
	frappe.reload_doc("projects", "doctype", "project")

	# Project Type to Vehicle Workshop
	project_types = frappe.db.sql_list("select distinct project_type from `tabProject` where ifnull(project_type) != ''")
	for project_type in project_types:
		doc = frappe.new_doc("Vehicle Workshop")
		doc.vehicle_workshop_name = project_type
		doc.insert()

	# Insert Project Type Other if not exists and change project types to Other
	if not frappe.db.exists("Project Type", "Other"):
		doc = frappe.new_doc("Project Type")
		doc.project_type = "Other"
		doc.insert()

	frappe.db.sql("update `tabProject` set vehicle_workshop = project_type")
	for project_type in project_types:
		frappe.db.sql("update `tabProject` set project_type = 'Other' where project_type = %s", project_type)

	# Remove Project Types which were converted to Vehicle Workshop
	for project_type in project_types:
		frappe.delete_doc("Project Type", project_type)

	# Vehicle Receipt/Delivery to Vehicle Service Receipt/Vehicle Gate Pass
	vrecs = []
	vdels = []

	get_fields = ['name', 'project', 'vehicle', 'customer', 'docstatus', 'posting_date', 'posting_time', 'creation', 'modified']
	copy_fields = ['project', 'posting_date', 'posting_time', 'vehicle']
	vtrn_filters = {'project': ['is', 'set'], 'docstatus': 1}

	if frappe.db.has_column('Vehicle Receipt', 'project'):
		vrec_fields = get_fields + ["'Vehicle Receipt' as doctype"]
		vrecs = frappe.get_all("Vehicle Receipt", fields=vrec_fields, filters=vtrn_filters)
	if frappe.db.has_column('Vehicle Delivery', 'project'):
		vdel_fields = get_fields + ["'Vehicle Delivery' as doctype"]
		vdels = frappe.get_all("Vehicle Delivery", fields=vdel_fields, filters=vtrn_filters)

	vtrns = vrecs + vdels
	vtrns_desc = sorted(vtrns, key=lambda d: (d.posting_date, d.posting_time, d.modified), reverse=True)
	vtrns_asc = sorted(vtrns, key=lambda d: (d.posting_date, d.posting_time, d.modified), reverse=False)

	# Cancel Vehicle Receipt/Deliveries
	for d in vtrns_desc:
		frappe.get_doc(d.doctype, d.name).cancel()

	# Create Vehicle Service Receipts and Vehicle Gate Passes
	for d in vtrns_asc:
		new_doctype = "Vehicle Service Receipt" if d.doctype == "Vehicle Receipt" else "Vehicle Gate Pass"

		doc = frappe.new_doc(new_doctype)
		doc.set_posting_time = 1
		for f in copy_fields:
			doc.set(f, d.get(f))

		if doc.doctype == "Vehicle Gate Pass":
			project = frappe.get_doc("Project", d.project)
			sales_invoice = project.get_invoice_for_vehicle_gate_pass()
			if sales_invoice:
				doc.sales_invoice = sales_invoice

		doc.insert()
		doc.submit()

	# Change Vehicle Status Received to In Workshop
	frappe.db.sql("update `tabProject` set vehicle_status = 'In Workshop' where vehicle_status = 'Received'")
