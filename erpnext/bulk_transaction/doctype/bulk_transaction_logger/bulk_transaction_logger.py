# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from pypika import functions as fn

from erpnext.utilities.bulk_transaction import task, update_logger


class BulkTransactionLogger(Document):
	pass

@frappe.whitelist()
def retry_failing_transaction():
	btp = frappe.qb.DocType("Bulk Transaction Logger List")
	data = (frappe.qb.from_(btp)
			.select(btp.transaction_name, btp.from_doctype, btp.to_doctype).distinct()
			.where(btp.retried != 1)
			.where(btp.transaction_status == "Failed")
			.where(btp.date == fn.CurDate())
			).run(as_dict=True)
	if len(data) > 10:
		frappe.enqueue(job,queue="long",job_name="bulk_retry",data=data)
	else:
		job(data)

def job(data):
	for d in data:
		failed = []
		try:
			task(d.transaction_name, d.from_doctype, d.to_doctype)
		except Exception as e:
			failed.append(e)
			update_logger(d.transaction_name, e , d.from_doctype, d.to_doctype, status="Failed", restarted=1)

		if not failed:
			update_logger(d.transaction_name, None , d.from_doctype, d.to_doctype, status="Success", restarted=1)