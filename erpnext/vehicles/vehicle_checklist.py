import frappe
from frappe import _


@frappe.whitelist()
def get_default_vehicle_checklist_items(parentfield):
	if parentfield not in ['vehicle_checklist', 'customer_request_checklist']:
		frappe.throw(_("Invalid parent field"))

	vehicles_settings = frappe.get_cached_doc("Vehicles Settings", None)
	checklist_items = [d.checklist_item for d in vehicles_settings.get(parentfield)]
	return checklist_items


def validate_duplicate_checklist_items(checklist_items):
	visited = set()
	for d in checklist_items:
		if d.checklist_item in visited:
			frappe.throw(_("Row #{0}: Duplicate Checklist Item {1}").format(d.idx, frappe.bold(d.checklist_item)))

		visited.add(d.checklist_item)


def set_missing_checklist(doc, parentfield):
	if not doc.get(parentfield):
		checklist = get_default_vehicle_checklist_items(parentfield)
		for item in checklist:
			doc.append(parentfield, {'checklist_item': item, 'checklist_item_checked': 0})


def clear_empty_checklist(doc, parentfield):
	if not any([d.checklist_item_checked for d in doc.get(parentfield)]):
		doc.set(parentfield, [])
