import frappe
from frappe.query_builder import DocType


def execute():
	LH = DocType("Letter Head")
	update_letter_head_for_query = (
		frappe.qb.update(LH).set(LH.letter_head_for, "DocType").where(LH.letter_head_for.isnull())
	)

	update_letter_head_for_query.run()

	for letter_head_for in ("DocType", "Report"):
		default_exists = frappe.db.exists(
			"Letter Head",
			{
				"is_default": 1,
				"disabled": 0,
				"letter_head_for": letter_head_for,
			},
		)

		if default_exists:
			continue

		standard_letter_head = frappe.db.get_value(
			"Letter Head",
			{
				"standard": "Yes",
				"disabled": 0,
				"letter_head_for": letter_head_for,
			},
			"name",
		)

		if not standard_letter_head:
			continue

		frappe.db.set_value(
			"Letter Head",
			standard_letter_head,
			"is_default",
			1,
			update_modified=False,
		)
