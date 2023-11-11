# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


def set_print_templates_for_item_table(doc, settings):
	doc.print_templates = {
		"items": "templates/print_formats/includes/items.html",
	}

	doc.child_print_templates = {
		"items": {
			"qty": "templates/print_formats/includes/item_table_qty.html",
		}
	}

	doc.flags.compact_item_fields = ["description", "qty", "rate", "amount"]

	if settings.compact_item_print:
		doc.child_print_templates["items"][
			"description"
		] = "templates/print_formats/includes/item_table_description.html"
		doc.flags.format_columns = format_columns


def set_print_templates_for_taxes(doc, settings):
	doc.flags.show_inclusive_tax_in_print = doc.is_inclusive_tax()
	doc.print_templates.update(
		{
			"total": "templates/print_formats/includes/total.html",
		}
	)

	if not doc.should_show_taxes_as_table_in_print():
		doc.print_templates.update(
			{
				"taxes": "templates/print_formats/includes/taxes.html",
			}
		)


def format_columns(display_columns, compact_fields):
	compact_fields = compact_fields + ["image", "item_code", "item_name"]
	final_columns = []
	for column in display_columns:
		if column not in compact_fields:
			final_columns.append(column)
	return final_columns
