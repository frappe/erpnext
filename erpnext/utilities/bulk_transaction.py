import json
from datetime import date, datetime

import frappe
from frappe import _


@frappe.whitelist()
def transaction_processing(data, from_doctype, to_doctype):
	if isinstance(data, str):
		deserialized_data = json.loads(data)

	else:
		deserialized_data = data

	length_of_data = len(deserialized_data)

	if length_of_data > 10:
		frappe.msgprint(
			_("Started a background job to create {1} {0}").format(to_doctype, length_of_data)
		)
		frappe.enqueue(
			job,
			deserialized_data=deserialized_data,
			from_doctype=from_doctype,
			to_doctype=to_doctype,
		)
	else:
		job(deserialized_data, from_doctype, to_doctype)


def job(deserialized_data, from_doctype, to_doctype):
	failed_history = []
	i = 0
	for d in deserialized_data:
		failed = []

		try:
			i += 1
			doc_name = d.get("name")
			frappe.db.savepoint("before_creation_state")
			task(doc_name, from_doctype, to_doctype)

		except Exception as e:
			frappe.db.rollback(save_point="before_creation_state")
			failed_history.append(e)
			failed.append(e)
			update_logger(
				doc_name, e, from_doctype, to_doctype, status="Failed", log_date=str(date.today())
			)
		if not failed:
			update_logger(
				doc_name, None, from_doctype, to_doctype, status="Success", log_date=str(date.today())
			)

	show_job_status(failed_history, deserialized_data, to_doctype)


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
			"Advance Payment": payment_entry.get_payment_entry,
		},
		"Sales Invoice": {
			"Delivery Note": sales_invoice.make_delivery_note,
			"Payment": payment_entry.get_payment_entry,
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
			"Advance Payment": payment_entry.get_payment_entry,
		},
		"Purchase Order": {
			"Purchase Invoice": purchase_order.make_purchase_invoice,
			"Purchase Receipt": purchase_order.make_purchase_receipt,
		},
		"Purhcase Invoice": {
			"Purchase Receipt": purchase_invoice.make_purchase_receipt,
			"Payment": payment_entry.get_payment_entry,
		},
		"Purchase Receipt": {"Purchase Invoice": purchase_receipt.make_purchase_invoice},
	}
	if to_doctype in ["Advance Payment", "Payment"]:
		obj = mapper[from_doctype][to_doctype](from_doctype, doc_name)
	else:
		obj = mapper[from_doctype][to_doctype](doc_name)

	obj.flags.ignore_validate = True
	obj.insert(ignore_mandatory=True)


def check_logger_doc_exists(log_date):
	return frappe.db.exists("Bulk Transaction Log", log_date)


def get_logger_doc(log_date):
	return frappe.get_doc("Bulk Transaction Log", log_date)


def create_logger_doc():
	log_doc = frappe.new_doc("Bulk Transaction Log")
	log_doc.set_new_name(set_name=str(date.today()))
	log_doc.log_date = date.today()

	return log_doc


def append_data_to_logger(log_doc, doc_name, error, from_doctype, to_doctype, status, restarted):
	row = log_doc.append("logger_data", {})
	row.transaction_name = doc_name
	row.date = date.today()
	now = datetime.now()
	row.time = now.strftime("%H:%M:%S")
	row.transaction_status = status
	row.error_description = str(error)
	row.from_doctype = from_doctype
	row.to_doctype = to_doctype
	row.retried = restarted


def update_logger(doc_name, e, from_doctype, to_doctype, status, log_date=None, restarted=0):
	if not check_logger_doc_exists(log_date):
		log_doc = create_logger_doc()
		append_data_to_logger(log_doc, doc_name, e, from_doctype, to_doctype, status, restarted)
		log_doc.insert()
	else:
		log_doc = get_logger_doc(log_date)
		if record_exists(log_doc, doc_name, status):
			append_data_to_logger(log_doc, doc_name, e, from_doctype, to_doctype, status, restarted)
			log_doc.save()


def show_job_status(failed_history, deserialized_data, to_doctype):
	if not failed_history:
		frappe.msgprint(
			_("Creation of {0} successful").format(to_doctype),
			title="Successful",
			indicator="green",
		)

	if len(failed_history) != 0 and len(failed_history) < len(deserialized_data):
		frappe.msgprint(
			_(
				"""Creation of {0} partially successful.
				Check <b><a href="/app/bulk-transaction-log">Bulk Transaction Log</a></b>"""
			).format(to_doctype),
			title="Partially successful",
			indicator="orange",
		)

	if len(failed_history) == len(deserialized_data):
		frappe.msgprint(
			_(
				"""Creation of {0} failed.
				Check <b><a href="/app/bulk-transaction-log">Bulk Transaction Log</a></b>"""
			).format(to_doctype),
			title="Failed",
			indicator="red",
		)


def record_exists(log_doc, doc_name, status):

	record = mark_retrired_transaction(log_doc, doc_name)

	if record and status == "Failed":
		return False
	elif record and status == "Success":
		return True
	else:
		return True


def mark_retrired_transaction(log_doc, doc_name):
	record = 0
	for d in log_doc.get("logger_data"):
		if d.transaction_name == doc_name and d.transaction_status == "Failed":
			d.retried = 1
			record = record + 1

	log_doc.save()

	return record
