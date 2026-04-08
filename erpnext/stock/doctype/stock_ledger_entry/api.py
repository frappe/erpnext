import frappe
from frappe import _
from frappe import utils as frappe_utils


# For Daily Number cards
@frappe.whitelist()
def get_total_no_of_slabs_daily():
	today = frappe_utils.today()
	result = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) = %s AND
		warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(today,),
	)
	return result[0][0] or 0


@frappe.whitelist()
def get_total_cost_slab_daily():
	today = frappe_utils.today()
	result = frappe.db.sql(
		"""
		SELECT SUM(valuation_rate)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) = %s AND
		warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(today,),
	)
	return result[0][0] or 0


@frappe.whitelist()
def get_daily_finished_goods_item_code_summary():
	today = frappe_utils.today()

	result = frappe.db.sql(
		"""
        SELECT item_code, COUNT(*) AS cnt
        FROM `tabStock Ledger Entry`
        WHERE DATE(creation) = %s
		AND warehouse LIKE '%%finished goods Warehouse%%'
        AND actual_qty > 0
        GROUP BY item_code
        ORDER BY cnt DESC, item_code ASC
    """,
		(today,),
		as_dict=True,
	)

	return result


# Weekly Number cards
@frappe.whitelist()
def get_total_no_of_slabs_weekly():
	start_date = frappe_utils.get_first_day_of_week(frappe_utils.today())
	end_date = frappe_utils.get_last_day_of_week(frappe_utils.today())
	result = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) BETWEEN %s AND %s AND
		warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(start_date, end_date),
	)
	return result[0][0] or 0


@frappe.whitelist()
def get_total_cost_slab_weekly():
	# Get the first and last day of the current week
	start_date = frappe_utils.get_first_day_of_week(frappe_utils.today())
	end_date = frappe_utils.get_last_day_of_week(frappe_utils.today())

	result = frappe.db.sql(
		"""
		SELECT SUM(valuation_rate)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) BETWEEN %s AND %s
		AND warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(start_date, end_date),
	)
	return result[0][0] or 0


@frappe.whitelist()
def get_weekly_finished_goods_item_code_summary():
	start_date = frappe_utils.get_first_day_of_week(frappe_utils.today())
	end_date = frappe_utils.get_last_day_of_week(frappe_utils.today())

	result = frappe.db.sql(
		"""
        SELECT item_code, COUNT(*) AS cnt
        FROM `tabStock Ledger Entry`
        WHERE DATE(creation) BETWEEN %s AND %s
		AND warehouse LIKE '%%finished goods Warehouse%%'
        AND actual_qty > 0
        GROUP BY item_code
        ORDER BY cnt DESC, item_code ASC
    """,
		(start_date, end_date),
		as_dict=True,
	)

	return result


# For Monthly Number cards
@frappe.whitelist()
def get_total_no_of_slabs_monthly():
	start_date = frappe_utils.get_first_day(frappe_utils.today())
	end_date = frappe_utils.get_last_day(frappe_utils.today())
	result = frappe.db.sql(
		"""
		SELECT COUNT(*)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) BETWEEN %s AND %s AND
		warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(start_date, end_date),
	)
	return result[0][0] or 0


@frappe.whitelist()
def get_total_cost_slab_monthly():
	# Get the first and last day of the current month
	start_date = frappe_utils.get_first_day(frappe_utils.today())
	end_date = frappe_utils.get_last_day(frappe_utils.today())

	result = frappe.db.sql(
		"""
		SELECT SUM(valuation_rate)
		FROM `tabStock Ledger Entry`
		WHERE DATE(creation) BETWEEN %s AND %s
		AND warehouse LIKE '%%finished goods Warehouse%%'
		AND actual_qty > 0
	""",
		(start_date, end_date),
	)
	return result[0][0] or 0


@frappe.whitelist()
def get_finished_goods_item_code_summary():
	start_date = frappe_utils.get_first_day(frappe_utils.today())
	end_date = frappe_utils.get_last_day(frappe_utils.today())

	result = frappe.db.sql(
		"""
        SELECT item_code, COUNT(*) AS cnt
        FROM `tabStock Ledger Entry`
        WHERE warehouse LIKE '%%finished goods Warehouse%%'
          AND actual_qty > 0
          AND DATE(creation) BETWEEN %s AND %s
        GROUP BY item_code
        ORDER BY cnt DESC, item_code ASC
    """,
		(start_date, end_date),
		as_dict=True,
	)

	return result
