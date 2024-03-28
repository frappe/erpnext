import frappe


def execute():
	frappe.reload_doc("assets", "doctype", "Asset Depreciation Schedule")

	assets = get_details_of_draft_or_submitted_depreciable_assets()

	asset_finance_books_map = get_asset_finance_books_map()

	asset_depreciation_schedules_map = get_asset_depreciation_schedules_map()

	block_size = 100  # Size of each block

	blocks = split_list_into_blocks(assets, block_size)

	if len(blocks) > 2:
		for asset in blocks[2]:
			if not asset_depreciation_schedules_map.get(asset.name):
				continue

			depreciation_schedules = asset_depreciation_schedules_map[asset.name]

			for fb_row in asset_finance_books_map[asset.name]:
				asset_depr_schedule_doc = frappe.new_doc("Asset Depreciation Schedule")

				asset_depr_schedule_doc.set_draft_asset_depr_schedule_details(asset, fb_row)

				asset_depr_schedule_doc.insert()

				if asset.docstatus == 1:
					asset_depr_schedule_doc.submit()

				depreciation_schedules_of_fb_row = [
					ds for ds in depreciation_schedules if ds["finance_book_id"] == str(fb_row.idx)
				]

				update_depreciation_schedules(depreciation_schedules_of_fb_row, asset_depr_schedule_doc.name)


def split_list_into_blocks(lst, block_size):
    """
    Split a list into blocks of given size.

    Args:
    lst (list): The list to split.
    block_size (int): The size of each block.

    Returns:
    list of lists: List containing sublists (blocks).
    """
    return [lst[i:i+block_size] for i in range(0, len(lst), block_size)]

def get_details_of_draft_or_submitted_depreciable_assets():
	asset = frappe.qb.DocType("Asset")

	records = (
		frappe.qb.from_(asset)
		.select(
			asset.name,
			asset.opening_accumulated_depreciation,
			asset.gross_purchase_amount,
			asset.number_of_depreciations_booked,
			asset.docstatus,
		)
		.where(asset.calculate_depreciation == 1)
		.where(asset.docstatus < 2)
	).run(as_dict=True)

	return records


def group_records_by_asset_name(records):
	grouped_dict = {}

	for item in records:
		key = list(item.keys())[0]
		value = item[key]

		if value not in grouped_dict:
			grouped_dict[value] = []

		del item["asset_name"]

		grouped_dict[value].append(item)

	return grouped_dict


def get_asset_finance_books_map():
	afb = frappe.qb.DocType("Asset Finance Book")
	asset = frappe.qb.DocType("Asset")
	daily_prorata_based = frappe.db.sql(f"SHOW COLUMNS FROM `tabAsset Finance Book` LIKE 'daily_prorata_based'")
	shift_based = frappe.db.sql(f"SHOW COLUMNS FROM `tabAsset Finance Book` LIKE 'shift_based'")
	
	# Initialize the list of columns to select
	columns_to_select = [
		asset.name.as_("asset_name"),
		afb.finance_book,
		afb.idx,
		afb.depreciation_method,
		afb.total_number_of_depreciations,
		afb.frequency_of_depreciation,
		afb.rate_of_depreciation,
		afb.expected_value_after_useful_life,
	]

	# If the column exists, include it in the select statement
	if daily_prorata_based:
		columns_to_select.append(afb.daily_prorata_based)

	if shift_based:
		columns_to_select.append(afb.shift_based)

	records = (
		frappe.qb.from_(afb)
		.join(asset)
		.on(afb.parent == asset.name)
		.select(*columns_to_select)
		.where(asset.docstatus < 2)
		.orderby(afb.idx)
	).run(as_dict=True)

	asset_finance_books_map = group_records_by_asset_name(records)

	return asset_finance_books_map


def get_asset_depreciation_schedules_map():
	ds = frappe.qb.DocType("Depreciation Schedule")
	asset = frappe.qb.DocType("Asset")
	finance_book_id = frappe.db.sql(f"SHOW COLUMNS FROM `tabDepreciation Schedule` LIKE 'finance_book_id'")
	
	# Initialize the list of columns to select
	columns_to_select = [
		asset.name.as_("asset_name"),
		ds.name,
	]

	# If the column exists, include it in the select statement
	if finance_book_id:
		columns_to_select.append(ds.finance_book_id)

	records = (
		frappe.qb.from_(ds)
		.join(asset)
		.on(ds.parent == asset.name)
		.select(*columns_to_select)
		.where(asset.docstatus < 2)
		.orderby(ds.idx)
	).run(as_dict=True)

	asset_depreciation_schedules_map = group_records_by_asset_name(records)

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
