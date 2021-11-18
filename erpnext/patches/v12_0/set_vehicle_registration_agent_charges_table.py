import frappe
from frappe.utils import flt


def execute():
	if 'Vehicles' not in frappe.get_active_domains():
		return
	if not frappe.db.has_column("Vehicle Registration Order", "agent_commission"):
		return
	if not frappe.db.has_column("Vehicle Registration Order", "agent_license_plate_charges"):
		return

	frappe.reload_doc('vehicles', 'doctype', 'vehicle_registration_order')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_registration_component')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_pricing_component')

	registration_charges_component = get_component_name('Registration Charges')
	license_plate_component = get_component_name('Customer License Plate Charges', 'License Plate')

	names = frappe.get_all("Vehicle Registration Order")
	names = [d.name for d in names]
	for name in names:
		doc = frappe.get_doc("Vehicle Registration Order", name)

		agent_commission = flt(frappe.db.get_value(doc.doctype, doc.name, 'agent_commission'))
		agent_license_plate_charges = flt(frappe.db.get_value(doc.doctype, doc.name, 'agent_license_plate_charges'))
		if agent_commission:
			row = doc.append('agent_charges')
			row.component = registration_charges_component
			row.component_amount = agent_commission
			row.db_insert()

		if agent_license_plate_charges:
			row = doc.append('agent_charges')
			row.component = license_plate_component
			row.component_amount = agent_license_plate_charges
			row.component_type = 'License Plate'
			row.db_insert()


def get_component_name(component_name, registration_component_type=None):
	existing = frappe.db.get_value("Vehicle Pricing Component",
		filters={"name": component_name})
	if existing:
		return existing

	if registration_component_type:
		existing = frappe.db.get_value("Vehicle Pricing Component",
			filters={"component_type": "Registration", "registration_component_type": registration_component_type})
		if existing:
			return existing

	doc = frappe.new_doc("Vehicle Pricing Component")
	doc.component_type = "Registration"
	doc.registration_component_type = registration_component_type
	doc.insert()

	return doc.name
