import frappe
from frappe import _


@frappe.whitelist()
def get_default_vehicle_checklist_items():
	vehicles_settings = frappe.get_cached_doc("Vehicles Settings", None)
	checklist_items = [d.checklist_item for d in vehicles_settings.vehicle_checklist_items]
	return checklist_items


def validate_duplicate_checklist_items(checklist_items):
	visited = set()
	for d in checklist_items:
		if d.checklist_item in visited:
			frappe.throw(_("Row #{0}: Duplicate Checklist Item {1}").format(d.idx, frappe.bold(d.checklist_item)))

		visited.add(d.checklist_item)


def set_missing_checklist(doc):
	if not doc.vehicle_checklist:
		checklist = get_default_vehicle_checklist_items()
		for item in checklist:
			doc.append("vehicle_checklist", {'checklist_item': item, 'checklist_item_checked': 0})


def clear_empty_checklist(doc):
	if not any([d.checklist_item_checked for d in doc.get('vehicle_checklist')]):
		doc.set('vehicle_checklist', [])
