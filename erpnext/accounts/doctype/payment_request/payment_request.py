import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, nowdate
from frappe.utils.background_jobs import enqueue

from erpnext import get_company_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry,
)
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.utils import get_account_currency, get_advance_payment_doctypes, get_currency_precision
from erpnext.utilities import payment_app_import_guard

ALLOWED_DOCTYPES_FOR_PAYMENT_REQUEST = [
	"Sales Order",
	"Purchase Order",
	"Sales Invoice",
	"Purchase Invoice",
	"POS Invoice",
	"Fees",
]


def _get_payment_gateway_controller(*args, **kwargs):
	with payment_app_import_guard():
		from payments.utils import get_payment_gateway_controller

	return get_payment_gateway_controller(*args, **kwargs)


class PaymentRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.subscription_plan_detail.subscription_plan_detail import (
			SubscriptionPlanDetail,
		)

		account: DF.ReadOnly | None
		amended_from: DF.Link | None
		bank: DF.Link | None
		bank_account: DF.Link | None
		bank_account_no: DF.ReadOnly | None
		branch_code: DF.ReadOnly | None
		company: DF.Link | None
		cost_center: DF.Link | None
		currency: DF.Link | None
		email_to: DF.Data | None
		failed_reason: DF.Data | None
		grand_total: DF.Currency
		iban: DF.ReadOnly | None
		is_a_subscription: DF.Check
		make_sales_invoice: DF.Check
		message: DF.Text | None
		mode_of_payment: DF.Link | None
		mute_email: DF.Check
		naming_series: DF.Literal["ACC-PRQ-.YYYY.-"]
		outstanding_amount: DF.Currency
		party: DF.DynamicLink | None
		party_account_currency: DF.Link | None
		party_name: DF.Data | None
		party_type: DF.Link | None
		payment_account: DF.ReadOnly | None
		payment_channel: DF.Literal["", "Email", "Phone", "Other"]
		payment_gateway: DF.ReadOnly | None
		payment_gateway_account: DF.Link | None
		payment_order: DF.Link | None
		payment_request_type: DF.Literal["Outward", "Inward"]
		payment_url: DF.Data | None
		phone_number: DF.Data | None
		print_format: DF.Literal[None]
		project: DF.Link | None
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		status: DF.Literal[
			"",
			"Draft",
			"Requested",
			"Initiated",
			"Partially Paid",
			"Payment Ordered",
			"Paid",
			"Failed",
			"Cancelled",
		]
		subject: DF.Data | None
		subscription_plans: DF.Table[SubscriptionPlanDetail]
		swift_number: DF.ReadOnly | None
		transaction_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		if self.get("__islocal"):
			self.status = "Draft"
		self.validate_reference_document()
		self.validate_payment_request_amount()
		# self.validate_currency()
		self.validate_subscription_details()

	def validate_reference_document(self):
		if not self.reference_doctype or not self.reference_name:
			frappe.throw(_("To create a Payment Request reference document is required"))

	def validate_payment_request_amount(self):
		if self.grand_total == 0:
			frappe.throw(
				_("{0} cannot be zero").format(self.get_label_from_fieldname("grand_total")),
				title=_("Invalid Amount"),
			)

		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if not hasattr(ref_doc, "order_type") or ref_doc.order_type != "Shopping Cart":
			ref_amount = get_amount(ref_doc, self.payment_account)
			if not ref_amount:
				frappe.throw(_("Payment Entry is already created"))

			existing_payment_request_amount = flt(get_existing_payment_request_amount(ref_doc))

			if (
				flt(
					existing_payment_request_amount + flt(self.grand_total, self.precision("grand_total")),
					get_currency_precision(),
				)
				> ref_amount
			):
				frappe.throw(
					_("Total Payment Request amount cannot be greater than {0} amount").format(
						self.reference_doctype
					)
				)

	def validate_currency(self):
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if self.payment_account and ref_doc.currency != frappe.get_cached_value(
			"Account", self.payment_account, "account_currency"
		):
			frappe.throw(_("Transaction currency must be same as Payment Gateway currency"))

	def validate_subscription_details(self):
		if self.is_a_subscription:
			amount = 0
			for subscription_plan in self.subscription_plans:
				payment_gateway = frappe.db.get_value(
					"Subscription Plan", subscription_plan.plan, "payment_gateway"
				)
				if payment_gateway != self.payment_gateway_account:
					frappe.throw(
						_(
							"The payment gateway account in plan {0} is different from the payment gateway account in this payment request"
						).format(subscription_plan.name)
					)

				rate = get_plan_rate(subscription_plan.plan, quantity=subscription_plan.qty)

				amount += rate

			if amount != self.grand_total:
				frappe.msgprint(
					_(
						"The amount of {0} set in this payment request is different from the calculated amount of all payment plans: {1}. Make sure this is correct before submitting the document."
					).format(self.grand_total, amount)
				)

	def before_submit(self):
		if (
			self.currency != self.party_account_currency
			and self.party_account_currency == get_company_currency(self.company)
		):
			# set outstanding amount in party account currency
			invoice = frappe.get_value(
				self.reference_doctype,
				self.reference_name,
				["rounded_total", "grand_total", "base_rounded_total", "base_grand_total"],
				as_dict=1,
			)
			grand_total = invoice.get("rounded_total") or invoice.get("grand_total")
			base_grand_total = invoice.get("base_rounded_total") or invoice.get("base_grand_total")
			self.outstanding_amount = flt(
				self.grand_total / grand_total * base_grand_total,
				self.precision("outstanding_amount"),
			)

		else:
			self.outstanding_amount = self.grand_total

		if self.payment_request_type == "Outward":
			self.status = "Initiated"
		elif self.payment_request_type == "Inward":
			self.status = "Requested"

		if self.payment_request_type == "Inward":
			if self.payment_channel == "Phone":
				self.request_phone_payment()
			else:
				self.set_payment_request_url()
				if not (self.mute_email or self.flags.mute_email):
					self.send_email()
					self.make_communication_entry()

	def on_submit(self):
		self.update_reference_advance_payment_status()

	def request_phone_payment(self):
		controller = _get_payment_gateway_controller(self.payment_gateway)
		request_amount = self.get_request_amount()

		payment_record = dict(
			reference_doctype="Payment Request",
			reference_docname=self.name,
			payment_reference=self.reference_name,
			request_amount=request_amount,
			sender=self.email_to,
			currency=self.currency,
			payment_gateway=self.payment_gateway,
			phone_number=self.phone_number,
		)

		controller.validate_transaction_currency(self.currency)
		controller.request_for_payment(**payment_record)

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

	def on_cancel(self):
		self.check_if_payment_entry_exists()
		self.set_as_cancelled()
		self.update_reference_advance_payment_status()

	def make_invoice(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		si = make_sales_invoice(self.reference_name, ignore_permissions=True)
		si.allocate_advances_automatically = True
		si = si.insert(ignore_permissions=True)
		si.submit()

	def payment_gateway_validation(self):
		try:
			controller = _get_payment_gateway_controller(self.payment_gateway)
			if hasattr(controller, "on_payment_request_submission"):
				return controller.on_payment_request_submission(self)
			else:
				return True
		except Exception:
			return False

	def set_payment_request_url(self):
		if self.payment_account and self.payment_gateway and self.payment_gateway_validation():
			self.payment_url = self.get_payment_url()

	def get_payment_url(self):
		if self.reference_doctype != "Fees":
			data = frappe.db.get_value(
				self.reference_doctype, self.reference_name, ["company", "customer_name"], as_dict=1
			)
		else:
			data = frappe.db.get_value(
				self.reference_doctype, self.reference_name, ["student_name"], as_dict=1
			)
			data.update({"company": frappe.defaults.get_defaults().company})

		controller = _get_payment_gateway_controller(self.payment_gateway)
		controller.validate_transaction_currency(self.currency)

		if hasattr(controller, "validate_minimum_transaction_amount"):
			controller.validate_minimum_transaction_amount(self.currency, self.grand_total)

		return controller.get_payment_url(
			**{
				"amount": flt(self.grand_total, self.precision("grand_total")),
				"title": data.company,
				"description": self.subject,
				"reference_doctype": "Payment Request",
				"reference_docname": self.name,
				"payer_email": self.email_to or frappe.session.user,
				"payer_name": data.customer_name,
				"order_id": self.name,
				"currency": self.currency,
				"payment_gateway": self.payment_gateway,
			}
		)

	def set_as_paid(self):
		if self.payment_channel == "Phone":
			self.db_set({"status": "Paid", "outstanding_amount": 0})

		else:
			payment_entry = self.create_payment_entry()
			if self.make_sales_invoice:
				self.make_invoice()

			return payment_entry

	def create_payment_entry(self, submit=True):
		"""create entry"""
		frappe.flags.ignore_account_permission = True

		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if self.reference_doctype in ["Sales Invoice", "POS Invoice"]:
			party_account = ref_doc.debit_to
		elif self.reference_doctype == "Purchase Invoice":
			party_account = ref_doc.credit_to
		else:
			party_account = get_party_account("Customer", ref_doc.get("customer"), ref_doc.company)

		party_account_currency = (
			self.get("party_account_currency")
			or ref_doc.get("party_account_currency")
			or get_account_currency(party_account)
		)

		party_amount = bank_amount = self.outstanding_amount

		if party_account_currency == ref_doc.company_currency and party_account_currency != self.currency:
			exchange_rate = ref_doc.get("conversion_rate")
			bank_amount = flt(self.outstanding_amount / exchange_rate, self.precision("grand_total"))

		# outstanding amount is already in Part's account currency
		payment_entry = get_payment_entry(
			self.reference_doctype,
			self.reference_name,
			party_amount=party_amount,
			bank_account=self.payment_account,
			bank_amount=bank_amount,
			created_from_payment_request=True,
		)

		payment_entry.update(
			{
				"mode_of_payment": self.mode_of_payment,
				"reference_no": self.name,  # to prevent validation error
				"reference_date": nowdate(),
				"remarks": "Payment Entry against {} {} via Payment Request {}".format(
					self.reference_doctype, self.reference_name, self.name
				),
			}
		)

		# Allocate payment_request for each reference in payment_entry (Payment Term can splits the row)
		self._allocate_payment_request_to_pe_references(references=payment_entry.references)

		# Update dimensions
		payment_entry.update(
			{
				"cost_center": self.get("cost_center"),
				"project": self.get("project"),
			}
		)

		# Update 'Paid Amount' on Forex transactions
		if self.currency != ref_doc.company_currency:
			if (
				self.payment_request_type == "Outward"
				and payment_entry.paid_from_account_currency == ref_doc.company_currency
				and payment_entry.paid_from_account_currency != payment_entry.paid_to_account_currency
			):
				payment_entry.paid_amount = payment_entry.base_paid_amount = (
					payment_entry.target_exchange_rate * payment_entry.received_amount
				)

		for dimension in get_accounting_dimensions():
			payment_entry.update({dimension: self.get(dimension)})

		if submit:
			payment_entry.insert(ignore_permissions=True)
			payment_entry.submit()

		return payment_entry

	def send_email(self):
		"""send email with payment link"""
		email_args = {
			"recipients": self.email_to,
			"sender": None,
			"subject": self.subject,
			"message": self.get_message(),
			"now": True,
			"attachments": [
				frappe.attach_print(
					self.reference_doctype,
					self.reference_name,
					file_name=self.reference_name,
					print_format=self.print_format,
				)
			],
		}
		enqueue(
			method=frappe.sendmail,
			queue="short",
			timeout=300,
			is_async=True,
			enqueue_after_commit=True,
			**email_args,
		)

	def get_message(self):
		"""return message with payment gateway link"""

		context = {
			"doc": frappe.get_doc(self.reference_doctype, self.reference_name),
			"payment_url": self.payment_url,
		}

		if self.message:
			return frappe.render_template(self.message, context)

	def set_failed(self):
		pass

	def set_as_cancelled(self):
		self.db_set("status", "Cancelled")

	def check_if_payment_entry_exists(self):
		if self.status == "Paid":
			if frappe.get_all(
				"Payment Entry Reference",
				filters={"reference_name": self.reference_name, "docstatus": ["<", 2]},
				fields=["parent"],
				limit=1,
			):
				frappe.throw(_("Payment Entry already exists"), title=_("Error"))

	def make_communication_entry(self):
		"""Make communication entry"""
		comm = frappe.get_doc(
			{
				"doctype": "Communication",
				"subject": self.subject,
				"content": self.get_message(),
				"sent_or_received": "Sent",
				"reference_doctype": self.reference_doctype,
				"reference_name": self.reference_name,
			}
		)
		comm.insert(ignore_permissions=True)

	def create_subscription(self, payment_provider, gateway_controller, data):
		if payment_provider == "stripe":
			with payment_app_import_guard():
				from payments.payment_gateways.stripe_integration import create_stripe_subscription

			return create_stripe_subscription(gateway_controller, data)

	def update_reference_advance_payment_status(self):
		if self.reference_doctype in get_advance_payment_doctypes():
			ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
			ref_doc.set_advance_payment_status()

	def _allocate_payment_request_to_pe_references(self, references):
		"""
		Allocate the Payment Request to the Payment Entry references based on\n
		    - Allocated Amount.
		    - Outstanding Amount of Payment Request.\n
		Payment Request is doc itself and references are the rows of Payment Entry.
		"""
		if len(references) == 1:
			references[0].payment_request = self.name
			return

		precision = references[0].precision("allocated_amount")
		outstanding_amount = self.outstanding_amount

		# to manage rows
		row_number = 1
		MOVE_TO_NEXT_ROW = 1
		TO_SKIP_NEW_ROW = 2
		NEW_ROW_ADDED = False

		while row_number <= len(references):
			row = references[row_number - 1]

			# update the idx to maintain the order
			row.idx = row_number

			if outstanding_amount == 0:
				if not NEW_ROW_ADDED:
					break

				row_number += MOVE_TO_NEXT_ROW
				continue

			# allocate the payment request to the row
			row.payment_request = self.name

			if row.allocated_amount <= outstanding_amount:
				outstanding_amount = flt(outstanding_amount - row.allocated_amount, precision)
				row_number += MOVE_TO_NEXT_ROW
			else:
				remaining_allocated_amount = flt(row.allocated_amount - outstanding_amount, precision)
				row.allocated_amount = outstanding_amount
				outstanding_amount = 0

				# create a new row without PR for remaining unallocated amount
				new_row = frappe.copy_doc(row)
				references.insert(row_number, new_row)

				# update new row
				new_row.idx = row_number + 1
				new_row.payment_request = None
				new_row.allocated_amount = remaining_allocated_amount

				NEW_ROW_ADDED = True
				row_number += TO_SKIP_NEW_ROW


@frappe.whitelist(allow_guest=True)
def make_payment_request(**args):
	"""Make payment request"""

	args = frappe._dict(args)
	if args.dt not in ALLOWED_DOCTYPES_FOR_PAYMENT_REQUEST:
		frappe.throw(_("Payment Requests cannot be created against: {0}").format(frappe.bold(args.dt)))

	ref_doc = args.ref_doc or frappe.get_doc(args.dt, args.dn)
	if not args.get("company"):
		args.company = ref_doc.company
	gateway_account = get_gateway_details(args) or frappe._dict()

	grand_total = get_amount(ref_doc, gateway_account.get("payment_account"))
	if not grand_total:
		frappe.throw(_("Payment Entry is already created"))

	if args.loyalty_points and ref_doc.doctype == "Sales Order":
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points

		loyalty_amount = validate_loyalty_points(ref_doc, int(args.loyalty_points))  # sets fields on ref_doc
		ref_doc.db_update()
		grand_total = grand_total - loyalty_amount

	# fetches existing payment request `grand_total` amount
	existing_payment_request_amount = get_existing_payment_request_amount(ref_doc)

	def validate_and_calculate_grand_total(grand_total, existing_payment_request_amount):
		grand_total -= existing_payment_request_amount
		if not grand_total:
			frappe.throw(_("Payment Request is already created"))
		return grand_total

	if existing_payment_request_amount:
		if args.order_type == "Shopping Cart":
			# If Payment Request is in an advanced stage, then create for remaining amount.
			if get_existing_payment_request_amount(
				ref_doc, ["Initiated", "Partially Paid", "Payment Ordered", "Paid"]
			):
				grand_total = validate_and_calculate_grand_total(grand_total, existing_payment_request_amount)
			else:
				# If PR's are processed, cancel all of them.
				cancel_old_payment_requests(ref_doc.doctype, ref_doc.name)
		else:
			grand_total = validate_and_calculate_grand_total(grand_total, existing_payment_request_amount)

	draft_payment_request = frappe.db.get_value(
		"Payment Request",
		{"reference_doctype": ref_doc.doctype, "reference_name": ref_doc.name, "docstatus": 0},
	)

	if draft_payment_request:
		frappe.db.set_value(
			"Payment Request", draft_payment_request, "grand_total", grand_total, update_modified=False
		)
		pr = frappe.get_doc("Payment Request", draft_payment_request)
	else:
		bank_account = (
			get_party_bank_account(args.get("party_type"), args.get("party"))
			if args.get("party_type")
			else ""
		)
		pr = frappe.new_doc("Payment Request")

		if not args.get("payment_request_type"):
			args["payment_request_type"] = (
				"Outward" if args.get("dt") in ["Purchase Order", "Purchase Invoice"] else "Inward"
			)

		party_type = args.get("party_type") or "Customer"
		party_account_currency = ref_doc.get("party_account_currency")

		if not party_account_currency:
			party_account = get_party_account(party_type, ref_doc.get(party_type.lower()), ref_doc.company)
			party_account_currency = get_account_currency(party_account)

		pr.update(
			{
				"payment_gateway_account": gateway_account.get("name"),
				"payment_gateway": gateway_account.get("payment_gateway"),
				"payment_account": gateway_account.get("payment_account"),
				"payment_channel": gateway_account.get("payment_channel"),
				"payment_request_type": args.get("payment_request_type"),
				"currency": ref_doc.currency,
				"party_account_currency": party_account_currency,
				"grand_total": grand_total,
				"mode_of_payment": args.mode_of_payment,
				"email_to": args.recipient_id or ref_doc.owner,
				"subject": _("Payment Request for {0}").format(args.dn),
				"message": gateway_account.get("message") or get_dummy_message(ref_doc),
				"reference_doctype": ref_doc.doctype,
				"reference_name": ref_doc.name,
				"company": ref_doc.get("company"),
				"party_type": party_type,
				"party": args.get("party") or ref_doc.get("customer"),
				"bank_account": bank_account,
				"party_name": args.get("party_name") or ref_doc.get("customer_name"),
				"make_sales_invoice": (
					args.make_sales_invoice  # new standard
					or args.order_type == "Shopping Cart"  # compat for webshop app
				),
				"mute_email": (
					args.mute_email  # new standard
					or args.order_type == "Shopping Cart"  # compat for webshop app
					or gateway_account.get("payment_channel", "Email") != "Email"
				),
				"phone_number": args.get("phone_number") if args.get("phone_number") else None,
			}
		)

		# Update dimensions
		pr.update(
			{
				"cost_center": ref_doc.get("cost_center"),
				"project": ref_doc.get("project"),
			}
		)

		for dimension in get_accounting_dimensions():
			pr.update({dimension: ref_doc.get(dimension)})

		if frappe.db.get_single_value("Accounts Settings", "create_pr_in_draft_status", cache=True):
			pr.insert(ignore_permissions=True)
		if args.submit_doc:
			if pr.get("__unsaved"):
				pr.insert(ignore_permissions=True)
			pr.submit()

	if args.order_type == "Shopping Cart":
		frappe.db.commit()
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = pr.get_payment_url()

	if args.return_doc:
		return pr

	return pr.as_dict()


def get_amount(ref_doc, payment_account=None):
	"""get amount based on doctype"""
	grand_total = 0

	dt = ref_doc.doctype
	if dt in ["Sales Order", "Purchase Order"]:
		advance_amount = flt(ref_doc.advance_paid)
		if ref_doc.party_account_currency != ref_doc.currency:
			advance_amount = flt(flt(ref_doc.advance_paid) / ref_doc.conversion_rate)

		grand_total = (flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)) - advance_amount

	elif dt in ["Sales Invoice", "Purchase Invoice"]:
		if (
			dt == "Sales Invoice"
			and ref_doc.is_pos
			and ref_doc.payments
			and any(
				[
					payment.type == "Phone" and payment.account == payment_account
					for payment in ref_doc.payments
				]
			)
		):
			grand_total = sum(
				[
					payment.amount
					for payment in ref_doc.payments
					if payment.type == "Phone" and payment.account == payment_account
				]
			)
		else:
			if ref_doc.party_account_currency == ref_doc.currency:
				grand_total = flt(ref_doc.outstanding_amount)
			else:
				grand_total = flt(flt(ref_doc.outstanding_amount) / ref_doc.conversion_rate)
	elif dt == "POS Invoice":
		for pay in ref_doc.payments:
			if pay.type == "Phone" and pay.account == payment_account:
				grand_total = pay.amount
				break
	elif dt == "Fees":
		grand_total = ref_doc.outstanding_amount

	return flt(grand_total, get_currency_precision()) if grand_total > 0 else 0


def get_irequest_status(payment_requests: None | list = None) -> list:
	IR = frappe.qb.DocType("Integration Request")
	res = []
	if payment_requests:
		res = (
			frappe.qb.from_(IR)
			.select(IR.name)
			.where(IR.reference_doctype.eq("Payment Request"))
			.where(IR.reference_docname.isin(payment_requests))
			.where(IR.status.isin(["Authorized", "Completed"]))
			.run(as_dict=True)
		)
	return res


def cancel_old_payment_requests(ref_dt, ref_dn):
	PR = frappe.qb.DocType("Payment Request")

	if res := (
		frappe.qb.from_(PR)
		.select(PR.name)
		.where(PR.reference_doctype == ref_dt)
		.where(PR.reference_name == ref_dn)
		.where(PR.docstatus == 1)
		.where(PR.status.isin(["Draft", "Requested"]))
		.run(as_dict=True)
	):
		if get_irequest_status([x.name for x in res]):
			frappe.throw(_("Another Payment Request is already processed"))
		else:
			for x in res:
				doc = frappe.get_doc("Payment Request", x.name)
				doc.flags.ignore_permissions = True
				doc.cancel()

				if ireqs := get_irequests_of_payment_request(doc.name):
					for ireq in ireqs:
						frappe.db.set_value("Integration Request", ireq.name, "status", "Cancelled")


def get_existing_payment_request_amount(ref_doc, statuses: list | None = None) -> list:
	"""
	Return the total amount of Payment Requests against a reference document.
	"""
	PR = frappe.qb.DocType("Payment Request")

	query = (
		frappe.qb.from_(PR)
		.select(Sum(PR.outstanding_amount))
		.where(PR.reference_doctype == ref_doc.doctype)
		.where(PR.reference_name == ref_doc.name)
		.where(PR.docstatus == 1)
	)

	if statuses:
		query = query.where(PR.status.isin(statuses))

	response = query.run()

	os_amount_in_transaction_currency = flt(response[0][0] if response[0] else 0)

	if ref_doc.currency != ref_doc.party_account_currency:
		os_amount_in_transaction_currency = flt(os_amount_in_transaction_currency / ref_doc.conversion_rate)

	return os_amount_in_transaction_currency


def get_gateway_details(args):  # nosemgrep
	"""
	Return gateway and payment account of default payment gateway
	"""
	gateway_account = args.get("payment_gateway_account", {"is_default": 1, "company": args.company})
	return get_payment_gateway_account(gateway_account)


def get_payment_gateway_account(filter):
	return frappe.db.get_value(
		"Payment Gateway Account",
		filter,
		["name", "payment_gateway", "payment_account", "payment_channel", "message"],
		as_dict=1,
	)


@frappe.whitelist()
def get_print_format_list(ref_doctype):
	print_format_list = ["Standard"]

	print_format_list.extend(
		[p.name for p in frappe.get_all("Print Format", filters={"doc_type": ref_doctype})]
	)

	return {"print_format": print_format_list}


@frappe.whitelist(allow_guest=True)
def resend_payment_email(docname):
	return frappe.get_doc("Payment Request", docname).send_email()


@frappe.whitelist()
def make_payment_entry(docname):
	doc = frappe.get_doc("Payment Request", docname)
	return doc.create_payment_entry(submit=False).as_dict()


def update_payment_requests_as_per_pe_references(references=None, cancel=False):
	"""
	Update Payment Request's `Status` and `Outstanding Amount` based on Payment Entry Reference's `Allocated Amount`.
	"""
	if not references:
		return

	precision = frappe.get_precision("Payment Entry Reference", "allocated_amount")
	referenced_payment_requests = frappe.get_all(
		"Payment Request",
		filters={"name": ["in", {row.payment_request for row in references if row.payment_request}]},
		fields=[
			"name",
			"grand_total",
			"outstanding_amount",
			"payment_request_type",
		],
	)

	referenced_payment_requests = {pr.name: pr for pr in referenced_payment_requests}
	doc_updates = {}

	for ref in references:
		if not ref.payment_request:
			continue

		payment_request = referenced_payment_requests[ref.payment_request]
		pr_outstanding = payment_request["outstanding_amount"]

		# update outstanding amount
		new_outstanding_amount = flt(
			pr_outstanding + ref.allocated_amount if cancel else pr_outstanding - ref.allocated_amount,
			precision,
		)

		# to handle same payment request for the multiple allocations
		payment_request["outstanding_amount"] = new_outstanding_amount

		if not cancel and new_outstanding_amount < 0:
			frappe.throw(
				msg=_(
					"The allocated amount is greater than the outstanding amount of Payment Request {0}"
				).format(ref.payment_request),
				title=_("Invalid Allocated Amount"),
			)

		# determine status
		if new_outstanding_amount == payment_request["grand_total"]:
			status = "Initiated" if payment_request["payment_request_type"] == "Outward" else "Requested"
		elif new_outstanding_amount == 0:
			status = "Paid"
		elif new_outstanding_amount > 0:
			status = "Partially Paid"

		# prepare bulk update data
		doc_updates[ref.payment_request] = {
			"outstanding_amount": new_outstanding_amount,
			"status": status,
		}

	# bulk update all payment requests
	if doc_updates:
		frappe.db.bulk_update("Payment Request", doc_updates)


def get_dummy_message(doc):
	return frappe.render_template(
		"""{% if doc.contact_person -%}
<p>Dear {{ doc.contact_person }},</p>
{%- else %}<p>Hello,</p>{% endif %}

<p>{{ _("Requesting payment against {0} {1} for amount {2}").format(doc.doctype,
	doc.name, doc.get_formatted("grand_total")) }}</p>

<a href="{{ payment_url }}">{{ _("Make Payment") }}</a>

<p>{{ _("If you have any questions, please get back to us.") }}</p>

<p>{{ _("Thank you for your business!") }}</p>
""",
		dict(doc=doc, payment_url="{{ payment_url }}"),
	)


@frappe.whitelist()
def get_subscription_details(reference_doctype, reference_name):
	if reference_doctype == "Sales Invoice":
		subscriptions = frappe.db.sql(
			"""SELECT parent as sub_name FROM `tabSubscription Invoice` WHERE invoice=%s""",
			reference_name,
			as_dict=1,
		)
		subscription_plans = []
		for subscription in subscriptions:
			plans = frappe.get_doc("Subscription", subscription.sub_name).plans
			for plan in plans:
				subscription_plans.append(plan)
		return subscription_plans


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Request"
		target.append(
			"references",
			{
				"reference_doctype": source.reference_doctype,
				"reference_name": source.reference_name,
				"amount": source.grand_total,
				"supplier": source.party,
				"payment_request": source_name,
				"mode_of_payment": source.mode_of_payment,
				"bank_account": source.bank_account,
				"account": source.account,
			},
		)

	doclist = get_mapped_doc(
		"Payment Request",
		source_name,
		{
			"Payment Request": {
				"doctype": "Payment Order",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist


def validate_payment(doc, method=None):
	if doc.reference_doctype != "Payment Request" or (
		frappe.db.get_value(doc.reference_doctype, doc.reference_docname, "status") != "Paid"
	):
		return

	frappe.throw(
		_("The Payment Request {0} is already paid, cannot process payment twice").format(
			doc.reference_docname
		)
	)


@frappe.whitelist()
def get_open_payment_requests_query(doctype, txt, searchfield, start, page_len, filters):
	# permission checks in `get_list()`
	filters = frappe._dict(filters)

	if not filters.reference_doctype or not filters.reference_name:
		return []

	if txt:
		filters.name = ["like", f"%{txt}%"]

	open_payment_requests = frappe.get_list(
		"Payment Request",
		filters=filters,
		fields=["name", "grand_total", "outstanding_amount"],
		order_by="transaction_date ASC,creation ASC",
	)

	return [
		(
			pr.name,
			_("<strong>Grand Total:</strong> {0}").format(pr.grand_total),
			_("<strong>Outstanding Amount:</strong> {0}").format(pr.outstanding_amount),
		)
		for pr in open_payment_requests
	]


def get_irequests_of_payment_request(doc: str | None = None) -> list:
	res = []
	if doc:
		res = frappe.db.get_all(
			"Integration Request",
			{
				"reference_doctype": "Payment Request",
				"reference_docname": doc,
				"status": "Queued",
			},
		)
	return res
