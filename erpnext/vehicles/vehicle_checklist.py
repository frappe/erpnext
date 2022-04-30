import frappe
from frappe import _
from frappe.utils import cint
from six import string_types


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


def set_updated_checklist(doc, parentfield):
	def add_row(row, is_custom=0):
		if isinstance(row, string_types):
			row = frappe._dict({'checklist_item': d})

		if row.checklist_item in existing_items:
			new_row = existing_items[row.checklist_item]
			new_row.checklist_item_checked = 0
			new_row.is_custom_checklist_item = cint(is_custom)
			doc.get(parentfield).append(new_row)
		else:
			doc.append(parentfield, {'checklist_item': row.checklist_item, 'checklist_item_checked': 0,
				'is_custom_checklist_item': cint(is_custom)})

	checked_items = [d.checklist_item for d in doc.get(parentfield) if d.get('checklist_item_checked')]
	custom_items = [d for d in doc.get(parentfield) if d.get('is_custom_checklist_item')]
	existing_items = {d.checklist_item: d for d in doc.get(parentfield)}

	updated_checklist = get_default_vehicle_checklist_items(parentfield)
	doc.set(parentfield, [])

	# Add settings items first
	for d in updated_checklist:
		add_row(d)

	# Add previously set custom items
	for d in custom_items:
		if d.checklist_item not in [e.checklist_item for e in doc.get(parentfield)]:
			add_row(d, is_custom=1)

	# Add checked items that are now removed
	for d in checked_items:
		if d not in [e.checklist_item for e in doc.get(parentfield)]:
			add_row(d, is_custom=1)

	# Reset idx and set checked
	for i, d in enumerate(doc.get(parentfield)):
		d.idx = i + 1
		if d.checklist_item in checked_items:
			d.checklist_item_checked = 1


def clear_empty_checklist(doc, parentfield):
	if not any([d.checklist_item_checked for d in doc.get(parentfield)]):
		doc.set(parentfield, [])
