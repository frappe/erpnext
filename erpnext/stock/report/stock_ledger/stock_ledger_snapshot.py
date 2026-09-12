# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import Function, IfNull, Sum

ArgMaxNull = CustomFunction("arg_max_null", ["value", "order"])


def get_opening_query(query, ledger, snapshot):
	"""Select each stock group's latest balance without sorting its entire ledger history."""
	null_order = snapshot.run(
		frappe.qb.select(Function("current_setting", "default_null_order")), pluck=True
	)[0]
	nulls_first = null_order == "NULLS_FIRST" or null_order.endswith("FIRST_ON_DESC")
	order_fields = []
	for field in (ledger.posting_datetime, ledger.creation, ledger.name):
		# Struct comparisons have their own NULL ordering. Match the previous DESC window,
		# including sites that changed DuckDB's default NULL ordering.
		order_fields.extend((field.isnull() if nulls_first else field.isnotnull(), field))
	order = Function("row", *order_fields)
	latest = (
		query.select(
			ArgMaxNull(ledger.qty_after_transaction, order).as_("qty_after_transaction"),
			ArgMaxNull(ledger.stock_value, order).as_("stock_value"),
		)
		.groupby(ledger.item_code, ledger.warehouse)
		.as_("latest_stock")
	)
	return frappe.qb.from_(latest).select(
		IfNull(Sum(latest.qty_after_transaction), 0.0).as_("total_qty"),
		IfNull(Sum(latest.stock_value), 0.0).as_("total_stock_value"),
	)
