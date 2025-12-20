import frappe
from frappe.utils import cstr


def execute():
	asset_finance_books_map = get_asset_finance_books_map()
	asset_depreciation_schedules_map = get_asset_depreciation_schedules_map()

	for key, fb_row in asset_finance_books_map.items():
		depreciation_schedules = asset_depreciation_schedules_map.get(key)
		if not depreciation_schedules:
			continue

		asset_depr_schedule_doc = frappe.new_doc("Asset Depreciation Schedule")
		asset_depr_schedule_doc.set_draft_asset_depr_schedule_details(fb_row, fb_row)
		asset_depr_schedule_doc.flags.ignore_validate = True
		asset_depr_schedule_doc.insert()

		if fb_row.docstatus == 1:
			frappe.db.set_value(
				"Asset Depreciation Schedule",
				asset_depr_schedule_doc.name,
				{"docstatus": 1, "status": "Active"},
			)

		update_depreciation_schedules(depreciation_schedules, asset_depr_schedule_doc.name)


def get_asset_finance_books_map():
	afb = frappe.qb.DocType("Asset Finance Book")
	asset = frappe.qb.DocType("Asset")

	records = (
		frappe.qb.from_(afb)
		.join(asset)
		.on(afb.parent == asset.name)
		.select(
			asset.name.as_("asset_name"),
			afb.finance_book,
			afb.idx,
			afb.depreciation_method,
			afb.total_number_of_depreciations,
			afb.frequency_of_depreciation,
			afb.rate_of_depreciation,
			afb.expected_value_after_useful_life,
			afb.daily_prorata_based,
			afb.shift_based,
			asset.docstatus,
			asset.name,
			asset.opening_accumulated_depreciation,
			asset.net_purchase_amount,
			asset.opening_number_of_booked_depreciations,
		)
		.where(asset.docstatus < 2)
		.where(asset.calculate_depreciation == 1)
		.orderby(afb.idx)
	).run(as_dict=True)

	asset_finance_books_map = frappe._dict()
	for d in records:
		asset_finance_books_map.setdefault((d.asset_name, cstr(d.finance_book)), d)

	return asset_finance_books_map


def get_asset_depreciation_schedules_map():
	ds = frappe.qb.DocType("Depreciation Schedule")
	asset = frappe.qb.DocType("Asset")

	records = (
		frappe.qb.from_(ds)
		.join(asset)
		.on(ds.parent == asset.name)
		.select(
			asset.name.as_("asset_name"),
			ds.name,
			ds.finance_book,
			ds.finance_book_id,
		)
		.where(asset.docstatus < 2)
		.where(asset.calculate_depreciation == 1)
		.orderby(ds.idx)
	).run(as_dict=True)

	if len(records) > 20000:
		frappe.db.auto_commit_on_many_writes = True

	asset_depreciation_schedules_map = frappe._dict()
	for d in records:
		asset_depreciation_schedules_map.setdefault((d.asset_name, cstr(d.finance_book)), []).append(d)

	return asset_depreciation_schedules_map


def update_depreciation_schedules(
	depreciation_schedules,
	asset_depr_schedule_name,
):
	ds = frappe.qb.DocType("Depreciation Schedule")

	for idx, depr_schedule in enumerate(depreciation_schedules, start=1):
		(
			frappe.qb.update(ds)
			.set(ds.idx, idx)
			.set(ds.parent, asset_depr_schedule_name)
			.set(ds.parentfield, "depreciation_schedule")
			.set(ds.parenttype, "Asset Depreciation Schedule")
			.where(ds.name == depr_schedule.name)
		).run()
