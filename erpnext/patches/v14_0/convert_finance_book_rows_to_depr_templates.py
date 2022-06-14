# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if not frappe.db.table_exists("Asset") or not frappe.db.table_exists("Asset Finance Book"):
		return

	if not frappe.db.count("Asset") or not frappe.db.count("Asset Finance Book"):
		return

	fb_rows = frappe.db.sql(
		"""select parent, finance_book, depreciation_method, total_number_of_depreciations, frequency_of_depreciation, rate_of_depreciation
		from `tabAsset Finance Book`
		order by parent
		""",
		as_dict=1,
	)
	frappe.reload_doctype("Asset Finance Book")

	count = 0
	frequency_in_months = {
		1: "Monthly",
		2: "Every 2 months",
		3: "Quarterly",
		4: "Every 4 months",
		5: "Every 5 months",
		6: "Half-Yearly",
		7: "Every 7 months",
		8: "Every 8 months",
		9: "Every 9 months",
		10: "Every 10 months",
		11: "Every 11 months",
		12: "Yearly",
	}

	parent = ""
	for fb in fb_rows:
		if fb.parent != parent:
			parent = fb["parent"]
			asset = frappe.get_doc("Asset", parent)
			asset.finance_books = []

		count += 1
		template = create_new_depr_template(fb, count, frequency_in_months)
		asset.append(
			"finance_books", {"finance_book": fb.finance_book, "depreciation_template": template}
		)


def create_new_depr_template(fb, count, frequency_in_months):
	template = frappe.new_doc("Depreciation Template")
	template.template_name = "Depreciation Template " + str(count)
	template.depreciation_method = fb.depreciation_method
	template.frequency_of_depreciation = frequency_in_months[fb.frequency_of_depreciation]
	template.asset_life, template.asset_life_unit = get_asset_life(fb)
	template.rate_of_depreciation = fb.rate_of_depreciation
	template.save()

	return template.name


def get_asset_life(fb):
	asset_life = fb.frequency_of_depreciation * fb.total_number_of_depreciations

	if asset_life % 12 == 0:
		return asset_life / 12, "Years"
	else:
		return asset_life, "Months"
