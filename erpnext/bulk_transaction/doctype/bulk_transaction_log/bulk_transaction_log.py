# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.database.operator_map import OPERATOR_MAP
from frappe.model.document import Document
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Sum
from frappe.utils import cint
from pypika import Order
from pypika.queries import QueryBuilder, Table


class BulkTransactionLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date | None
		failed: DF.Int
		log_entries: DF.Int
		succeeded: DF.Int
	# end: auto-generated types

	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		log_detail = qb.DocType("Bulk Transaction Log Detail")

		has_records = frappe.db.exists("Bulk Transaction Log Detail", {"date": self.name})
		if not has_records:
			raise frappe.DoesNotExistError

		succeeded_logs = (
			qb.from_(log_detail)
			.select(Count(log_detail.date).as_("count"))
			.where((log_detail.date == self.name) & (log_detail.transaction_status == "Success"))
			.run()
		)[0][0] or 0
		failed_logs = (
			qb.from_(log_detail)
			.select(Count(log_detail.date).as_("count"))
			.where((log_detail.date == self.name) & (log_detail.transaction_status == "Failed"))
			.run()
		)[0][0] or 0
		total_logs = succeeded_logs + failed_logs
		transaction_log = frappe._dict(
			{
				"date": self.name,
				"count": total_logs,
				"succeeded": succeeded_logs,
				"failed": failed_logs,
			}
		)
		super(Document, self).__init__(serialize_transaction_log(transaction_log))

	# nosemgrep: frappe-semgrep-rules.rules.overusing-args -- reviewed: frappe calls virtual doctype get_list with `args=`
	@staticmethod
	def get_list(args):
		frappe.has_permission("Bulk Transaction Log", "read", throw=True)
		log_detail = qb.DocType("Bulk Transaction Log Detail")
		query = (
			qb.from_(log_detail)
			.select(
				log_detail.date,
				Count(log_detail.date).as_("count"),
				count_with_status(log_detail, "Success").as_("succeeded"),
				count_with_status(log_detail, "Failed").as_("failed"),
			)
			.groupby(log_detail.date)
			.orderby(log_detail.date, order=Order.desc)
			.offset(cint(args.get("start")))
			.limit(cint(args.get("page_length")) or 20)
		)
		query = filter_by_date(query, log_detail, parse_list_filters(args.get("filters")))
		return [serialize_transaction_log(x) for x in query.run(as_dict=True)]

	# nosemgrep: frappe-semgrep-rules.rules.overusing-args -- reviewed: frappe calls virtual doctype get_count with `args=`
	@staticmethod
	def get_count(args):
		frappe.has_permission("Bulk Transaction Log", "read", throw=True)
		log_detail = qb.DocType("Bulk Transaction Log Detail")
		query = qb.from_(log_detail).select(Count(log_detail.date).distinct())
		return filter_by_date(query, log_detail, parse_list_filters(args.get("filters"))).run()[0][0]

	@staticmethod
	def get_stats(args):
		pass

	def db_update(self, *args, **kwargs):
		pass

	def delete(self):
		pass


def serialize_transaction_log(data):
	return frappe._dict(
		name=data.date,
		date=data.date,
		log_entries=data.count,
		succeeded=data.succeeded,
		failed=data.failed,
	)


def count_with_status(log_detail: Table, status: str) -> Sum:
	return Sum(Case().when(log_detail.transaction_status == status, 1).else_(0))


def filter_by_date(query: QueryBuilder, log_detail: Table, conditions: list[tuple]) -> QueryBuilder:
	for operator, value in conditions:
		if operator not in OPERATOR_MAP:
			frappe.throw(_("Unsupported filter operator {0}").format(operator))
		query = query.where(OPERATOR_MAP[operator](log_detail.date, value))
	return query


def parse_list_filters(filters: dict | list | None) -> list[tuple]:
	"""Return (operator, value) pairs for the date filters in dict or 2-, 3- and 4-item list filters."""
	filters = filters or []
	if isinstance(filters, dict):
		filters = [[field, *value] if is_list(value) else [field, value] for field, value in filters.items()]

	conditions = [with_operator(condition) for condition in filters if is_list(condition)]
	return [
		(str(condition[-2]).lower(), condition[-1])
		for condition in conditions
		if len(condition) >= 3 and condition[-3] == "date"
	]


def with_operator(condition: list | tuple) -> list:
	"""Expand the [field, value] equality shorthand to [field, "=", value]."""
	return [condition[0], "=", condition[1]] if len(condition) == 2 else list(condition)


def is_list(value) -> bool:
	return isinstance(value, list | tuple)
