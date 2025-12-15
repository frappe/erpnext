import json
from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import get_link_to_form, today


@frappe.whitelist()
def transaction_processing(data, from_doctype, to_doctype, args=None):
	frappe.has_permission(from_doctype, "read", throw=True)
	frappe.has_permission(to_doctype, "create", throw=True)

	if isinstance(data, str):
		deserialized_data = json.loads(data)
	else:
		deserialized_data = data

	if isinstance(args, str):
		args = frappe._dict(json.loads(args))

	skipped_records = [d for d in deserialized_data if d.get("status") in ("On Hold", "Closed")]

	deserialized_data = [d for d in deserialized_data if d.get("status") not in ("On Hold", "Closed")]

	length_of_data = len(deserialized_data)

	skipped_msg = ""

	if skipped_records:
		skipped_msg = _("{0} creation for the following records will be skipped.").format(to_doctype)

		skipped_msg += (
			"<br><br><ul>"
			+ "".join(_("<li>{}</li>").format(frappe.bold(row.get("name"))) for row in skipped_records)
			+ "</ul>"
		)

	if not length_of_data:
		frappe.msgprint(skipped_msg)
		return

	frappe.msgprint(
		_("Started a background job to create {1} {0}. {2}").format(to_doctype, length_of_data, skipped_msg)
	)
	frappe.enqueue(
		job,
		deserialized_data=deserialized_data,
		from_doctype=from_doctype,
		to_doctype=to_doctype,
		args=args,
	)


@frappe.whitelist()
def retry(date: str | None = None):
	if not date:
		date = today()

	if date:
		failed_docs = frappe.db.get_all(
			"Bulk Transaction Log Detail",
			filters={"date": date, "transaction_status": "Failed", "retried": 0},
			fields=["name", "transaction_name", "from_doctype", "to_doctype"],
		)
		if not failed_docs:
			frappe.msgprint(_("There are no Failed transactions"))
		else:
			job = frappe.enqueue(
				retry_failed_transactions,
				failed_docs=failed_docs,
			)
			frappe.msgprint(
				_("Job: {0} has been triggered for processing failed transactions").format(
					get_link_to_form("RQ Job", job.id)
				)
			)


def retry_failed_transactions(failed_docs: list | None):
	if failed_docs:
		for log in failed_docs:
			try:
				frappe.db.savepoint("before_creation_state")
				task(log.transaction_name, log.from_doctype, log.to_doctype)
			except Exception:
				frappe.db.rollback(save_point="before_creation_state")
				update_log(log.name, "Failed", 1, str(frappe.get_traceback(with_context=True)))
			else:
				update_log(log.name, "Success", 1)


def update_log(log_name, status, retried, err=None):
	frappe.db.set_value("Bulk Transaction Log Detail", log_name, "transaction_status", status)
	frappe.db.set_value("Bulk Transaction Log Detail", log_name, "retried", retried)
	if err:
		frappe.db.set_value("Bulk Transaction Log Detail", log_name, "error_description", err)


def job(deserialized_data, from_doctype, to_doctype, args):
	fail_count = 0

	if args:
		# currently: flag-based transport to `task`
		frappe.flags.args = args

	for d in deserialized_data:
		try:
			doc_name = d.get("name")
			frappe.db.savepoint("before_creation_state")
			task(doc_name, from_doctype, to_doctype)
		except Exception:
			frappe.db.rollback(save_point="before_creation_state")
			fail_count += 1
			create_log(
				doc_name,
				str(frappe.get_traceback(with_context=True)),
				from_doctype,
				to_doctype,
				status="Failed",
				log_date=str(date.today()),
			)
		else:
			create_log(doc_name, None, from_doctype, to_doctype, status="Success", log_date=str(date.today()))

	show_job_status(fail_count, len(deserialized_data), to_doctype)


def task(doc_name, from_doctype, to_doctype):
	from erpnext.accounts.doctype.payment_entry import payment_entry
	from erpnext.accounts.doctype.purchase_invoice import purchase_invoice
	from erpnext.accounts.doctype.sales_invoice import sales_invoice
	from erpnext.buying.doctype.purchase_order import purchase_order
	from erpnext.buying.doctype.supplier_quotation import supplier_quotation
	from erpnext.selling.doctype.quotation import quotation
	from erpnext.selling.doctype.sales_order import sales_order
	from erpnext.stock.doctype.delivery_note import delivery_note
	from erpnext.stock.doctype.purchase_receipt import purchase_receipt

	mapper = {
		"Sales Order": {
			"Sales Invoice": sales_order.make_sales_invoice,
			"Delivery Note": sales_order.make_delivery_note,
			"Payment Entry": payment_entry.get_payment_entry,
		},
		"Sales Invoice": {
			"Delivery Note": sales_invoice.make_delivery_note,
			"Payment Entry": payment_entry.get_payment_entry,
		},
		"Delivery Note": {
			"Sales Invoice": delivery_note.make_sales_invoice,
			"Packing Slip": delivery_note.make_packing_slip,
		},
		"Quotation": {
			"Sales Order": quotation.make_sales_order,
			"Sales Invoice": quotation.make_sales_invoice,
		},
		"Supplier Quotation": {
			"Purchase Order": supplier_quotation.make_purchase_order,
			"Purchase Invoice": supplier_quotation.make_purchase_invoice,
		},
		"Purchase Order": {
			"Purchase Invoice": purchase_order.make_purchase_invoice,
			"Purchase Receipt": purchase_order.make_purchase_receipt,
			"Payment Entry": payment_entry.get_payment_entry,
		},
		"Purchase Invoice": {
			"Purchase Receipt": purchase_invoice.make_purchase_receipt,
			"Payment Entry": payment_entry.get_payment_entry,
		},
		"Purchase Receipt": {"Purchase Invoice": purchase_receipt.make_purchase_invoice},
	}

	hooks = frappe.get_hooks("bulk_transaction_task_mapper")
	for hook in hooks:
		mapper.update(frappe.get_attr(hook)())

	frappe.flags.bulk_transaction = True
	if to_doctype in ["Payment Entry"]:
		obj = mapper[from_doctype][to_doctype](from_doctype, doc_name)
	else:
		obj = mapper[from_doctype][to_doctype](doc_name)

	if obj:
		obj.flags.ignore_validate = True
		obj.set_title_field()
		obj.insert(ignore_mandatory=True)

	del obj
	del frappe.flags.bulk_transaction


def create_log(doc_name, e, from_doctype, to_doctype, status, log_date=None, restarted=0):
	transaction_log = frappe.new_doc("Bulk Transaction Log Detail")
	transaction_log.transaction_name = doc_name
	transaction_log.date = today()
	now = datetime.now()
	transaction_log.time = now.strftime("%H:%M:%S")
	transaction_log.transaction_status = status
	transaction_log.error_description = str(e)
	transaction_log.from_doctype = from_doctype
	transaction_log.to_doctype = to_doctype
	transaction_log.retried = restarted
	transaction_log.save(ignore_permissions=True)


def show_job_status(fail_count, deserialized_data_count, to_doctype):
	if not fail_count:
		frappe.msgprint(
			_("Creation of <b><a href='/app/{0}'>{1}(s)</a></b> successful").format(
				to_doctype.lower().replace(" ", "-"), to_doctype
			),
			title="Successful",
			indicator="green",
		)
	elif fail_count != 0 and fail_count < deserialized_data_count:
		frappe.msgprint(
			_(
				"""Creation of {0} partially successful.
				Check <b><a href="/app/bulk-transaction-log">Bulk Transaction Log</a></b>"""
			).format(to_doctype),
			title="Partially successful",
			indicator="orange",
		)
	else:
		frappe.msgprint(
			_(
				"""Creation of {0} failed.
				Check <b><a href="/app/bulk-transaction-log">Bulk Transaction Log</a></b>"""
			).format(to_doctype),
			title="Failed",
			indicator="red",
		)
