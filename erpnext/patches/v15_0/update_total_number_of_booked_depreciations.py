import frappe

from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_depr_schedule,
)


def execute():
	if frappe.db.has_column("Asset Finance Book", "total_number_of_booked_depreciations"):
		assets = frappe.get_all(
			"Asset", filters={"docstatus": 1}, fields=["name", "opening_number_of_booked_depreciations"]
		)

		for asset in assets:
			asset_doc = frappe.get_doc("Asset", asset.name)

			for fb_row in asset_doc.get("finance_books"):
				depr_schedule = get_depr_schedule(asset.name, "Active", fb_row.finance_book)
				total_number_of_booked_depreciations = asset.opening_number_of_booked_depreciations or 0

				if depr_schedule:
					for je in depr_schedule:
						if je.journal_entry:
							total_number_of_booked_depreciations += 1
				frappe.db.set_value(
					"Asset Finance Book",
					fb_row.name,
					"total_number_of_booked_depreciations",
					total_number_of_booked_depreciations,
				)
