import frappe

from erpnext.stock.doctype.quality_inspection.quality_inspection import (
	format_reading,
	get_reading_number_format,
	get_reading_separators,
	parse_reading,
)

FIELDS = [f"reading_{i}" for i in range(1, 11)]


def execute():
	"""Convert numeric readings to the stored format, parsed in the number format of who last saved them."""
	separators = {}
	start = 0
	while rows := frappe.get_all(
		"Quality Inspection Reading",
		{"numeric": 1, "manual_inspection": 0},
		["name", "modified_by", *FIELDS],
		order_by="name",
		start=start,
		page_length=10000,
	):
		frappe.db.bulk_update(
			"Quality Inspection Reading", get_updates(rows, separators), update_modified=False
		)
		start += len(rows)


def get_updates(rows, separators):
	updates = {}
	for row in rows:
		if row.modified_by not in separators:
			separators[row.modified_by] = get_reading_separators(get_reading_number_format(row.modified_by))

		for field in FIELDS:
			number = parse_reading(row[field] or "", *separators[row.modified_by])
			if number is not None and format_reading(number) != row[field]:
				updates.setdefault(row.name, {})[field] = format_reading(number)

	return updates
