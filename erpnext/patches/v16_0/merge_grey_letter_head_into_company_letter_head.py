import json

import frappe

OLD_LETTER_HEAD = "Company Letterhead - Grey"
LETTER_HEAD = "Company Letterhead"


def execute():
	if not frappe.db.exists("Letter Head", {"name": OLD_LETTER_HEAD, "standard": "Yes"}):
		return

	if not frappe.db.exists("Letter Head", LETTER_HEAD):
		return

	was_default = frappe.db.get_value("Letter Head", OLD_LETTER_HEAD, "is_default")
	update_print_format_layouts()
	frappe.rename_doc("Letter Head", OLD_LETTER_HEAD, LETTER_HEAD, merge=True, force=True, show_alert=False)

	if was_default:
		frappe.db.set_value("Letter Head", LETTER_HEAD, "is_default", 1)
		frappe.get_doc("Letter Head", LETTER_HEAD).set_as_default()


def update_print_format_layouts():
	for name, format_data in frappe.get_all(
		"Print Format",
		filters={"format_data": ("like", f"%{OLD_LETTER_HEAD}%")},
		fields=["name", "format_data"],
		as_list=True,
	):
		layout = json.loads(format_data)
		if isinstance(layout, dict) and layout.get("letter_head") == OLD_LETTER_HEAD:
			layout["letter_head"] = LETTER_HEAD
			frappe.db.set_value(
				"Print Format", name, "format_data", json.dumps(layout), update_modified=False
			)
