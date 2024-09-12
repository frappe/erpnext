"""Compatipility methods for v1 implementations of payment gateways

"""
import json

import frappe
from frappe.utils import deprecated, flt

from erpnext.utilities import payment_app_import_guard


def _get_payment_controller(*args, **kwargs):
	with payment_app_import_guard():
		try:
			from payments.utils import get_payment_controller
		except Exception:
			from payments.utils import get_payment_gateway_controller as get_payment_controller

	return get_payment_controller(*args, **kwargs)


def is_v2_gateway(payment_gateway):
	try:
		from payments.controllers import PaymentController
	except Exception:
		return False
	try:
		controller = _get_payment_controller(payment_gateway)
	except Exception:
		frappe.warnings.warn(f"{payment_gateway} is not a valid gateway; this is normal during tests.")
		return False
	return isinstance(controller, PaymentController)


def get_request_amount(self):
	data_of_completed_requests = frappe.get_all(
		"Integration Request",
		filters={
			"reference_doctype": self.doctype,
			"reference_docname": self.name,
			"status": "Completed",
		},
		pluck="data",
	)
	if not data_of_completed_requests:
		return self.grand_total
	request_amounts = sum(json.loads(d).get("request_amount") for d in data_of_completed_requests)
	return request_amounts


def request_phone_payment(self, controller):
	request_amount = get_request_amount(self)

	payment_record = dict(
		reference_doctype="Payment Request",
		reference_docname=self.name,
		payment_reference=self.reference_name,
		request_amount=request_amount,
		sender=self.email_to,
		currency=self.currency,
		payment_gateway=self.payment_gateway,
	)

	controller.validate_transaction_currency(self.currency)
	controller.request_for_payment(**payment_record)


def payment_gateway_validation(self, controller):
	try:
		if hasattr(controller, "on_payment_request_submission"):
			return controller.on_payment_request_submission(self)
		else:
			return True
	except Exception:
		return False


def get_payment_url(self, controller):
	if self.reference_doctype != "Fees":
		data = frappe.db.get_value(
			self.reference_doctype, self.reference_name, ["company", "customer_name"], as_dict=1
		)
	else:
		data = frappe.db.get_value(self.reference_doctype, self.reference_name, ["student_name"], as_dict=1)
		data.update({"company": frappe.defaults.get_defaults().company})

	controller.validate_transaction_currency(self.currency)

	if hasattr(controller, "validate_minimum_transaction_amount"):
		controller.validate_minimum_transaction_amount(self.currency, self.grand_total)

	return controller.get_payment_url(
		**{
			"amount": flt(self.grand_total, self.precision("grand_total")),
			"title": data.company.encode("utf-8"),
			"description": self.subject.encode("utf-8"),
			"reference_doctype": "Payment Request",
			"reference_docname": self.name,
			"payer_email": self.email_to or frappe.session.user,
			"payer_name": frappe.safe_encode(data.customer_name),
			"order_id": self.name,
			"currency": self.currency,
		}
	)


def set_payment_request_url(self, controller):
	if self.payment_account and self.payment_gateway and payment_gateway_validation(self, controller):
		self.payment_url = get_payment_url(self, controller)


@deprecated
def v1_gateway_before_submit(self, payment_gateway):
	try:
		controller = _get_payment_controller(payment_gateway)
	except Exception:
		frappe.warnings.warn(f"{payment_gateway} is not a valid gateway; this is normal during tests.")
		return False
	if self.payment_channel == "Phone":
		request_phone_payment(self, controller)
	else:
		set_payment_request_url(self, controller)
		if not (self.mute_email or self.flags.mute_email):
			self.send_email()
			self.make_communication_entry()
