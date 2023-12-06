# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import qb
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.utils import cint
from pypika import Order


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

		has_records = frappe.db.sql(
			f"select exists (select * from `tabBulk Transaction Log Detail` where date = '{self.name}');"
		)[0][0]
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

	@staticmethod
	def get_list(args):
		filter_date = parse_list_filters(args)
		limit = cint(args.get("page_length")) or 20
		log_detail = qb.DocType("Bulk Transaction Log Detail")

		dates_query = (
			qb.from_(log_detail)
			.select(log_detail.date)
			.distinct()
			.orderby(log_detail.date, order=Order.desc)
			.limit(limit)
		)
		if filter_date:
			dates_query = dates_query.where(log_detail.date == filter_date)
		dates = dates_query.run()

		transaction_logs = []
		if dates:
			transaction_logs_query = (
				qb.from_(log_detail)
				.select(log_detail.date.as_("date"), Count(log_detail.date).as_("count"))
				.where(log_detail.date.isin(dates))
				.orderby(log_detail.date, order=Order.desc)
				.groupby(log_detail.date)
				.limit(limit)
			)
			transaction_logs = transaction_logs_query.run(as_dict=True)

		return [serialize_transaction_log(x) for x in transaction_logs]

	@staticmethod
	def get_count(args):
		pass

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


def parse_list_filters(args):
	# parse date filter
	filter_date = None
	for fil in args.get("filters"):
		if isinstance(fil, list):
			for elem in fil:
				if elem == "date":
					filter_date = fil[3]
	return filter_date
