# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import qb
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.utils import cint
from pypika import Order


class BulkTransactionLog(Document):
	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		log_detail = qb.DocType("Bulk Transaction Log Detail")
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
		log_detail = qb.DocType("Bulk Transaction Log Detail")
		limit = cint(args.get("page_length")) or 20
		dates = (
			qb.from_(log_detail)
			.select(log_detail.date)
			.distinct()
			.orderby(log_detail.date, order=Order.desc)
			.limit(limit)
			.run()
		)

		transaction_logs = (
			qb.from_(log_detail)
			.select(log_detail.date.as_("date"), Count(log_detail.date).as_("count"))
			.where(log_detail.date.isin(dates))
			.orderby(log_detail.date, order=Order.desc)
			.groupby(log_detail.date)
			.limit(limit)
			.run(as_dict=True)
		)
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
