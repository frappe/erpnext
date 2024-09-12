import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, nowdate
from frappe.utils.background_jobs import enqueue

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_company_defaults,
	get_payment_entry,
)
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.utils import get_account_currency, get_currency_precision
from erpnext.utilities import payment_app_import_guard

from .payment_gateway_v1 import is_v2_gateway, v1_gateway_before_submit


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
		cost_center: DF.Link | None
		currency: DF.Link | None
		email_to: DF.Data | None
		grand_total: DF.Currency
		iban: DF.ReadOnly | None
		is_a_subscription: DF.Check
		make_sales_invoice: DF.Check
		message: DF.Text | None
		mode_of_payment: DF.Link | None
		mute_email: DF.Check
		naming_series: DF.Literal["ACC-PRQ-.YYYY.-"]
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		payment_account: DF.ReadOnly | None
		payment_channel: DF.Literal["", "Email", "Phone"]
		payment_gateway: DF.ReadOnly | None
		payment_gateway_account: DF.Link | None
		payment_order: DF.Link | None
		payment_request_type: DF.Literal["Outward", "Inward"]
		payment_url: DF.Data | None
		print_format: DF.Literal
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
		company: DF.Link | None
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
		existing_payment_request_amount = flt(
			get_existing_payment_request_amount(self.reference_doctype, self.reference_name)
		)

		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if not hasattr(ref_doc, "order_type") or ref_doc.order_type != "Shopping Cart":
			ref_amount = get_amount(ref_doc, self.payment_account)
			if not ref_amount:
				frappe.throw(_("Payment Entry is already created"))

			if existing_payment_request_amount + flt(self.grand_total) > ref_amount:
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

	def on_change(self):
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		advance_payment_doctypes = frappe.get_hooks("advance_payment_receivable_doctypes") + frappe.get_hooks(
			"advance_payment_payable_doctypes"
		)
		if self.reference_doctype in advance_payment_doctypes:
			# set advance payment status
			ref_doc.set_advance_payment_status()

	def before_submit(self):
		if self.payment_request_type == "Outward":
			self.status = "Initiated"
		elif self.payment_request_type == "Inward":
			self.status = "Requested"

		if self.payment_request_type == "Inward" and self.payment_gateway:
			if not is_v2_gateway(self.payment_gateway):
				return v1_gateway_before_submit(self, self.payment_gateway)
			tx_data = self.get_tx_data()
			with payment_app_import_guard():
				from payments.controllers import PaymentController

				controller, self.payment_session_log = PaymentController.initiate(
					tx_data, self.payment_gateway
				)
				# checkout page can also be the target of a gatway initialized flow
				# gateways also may return None if appropriate
				self.payment_url = controller.get_payment_url(self.payment_session_log)
				if not controller.is_user_flow_initiation_delegated(self.payment_session_log):
					if not (self.mute_email or self.flags.mute_email):
						self.send_email()
						self.make_communication_entry()

	def on_cancel(self):
		self.check_if_payment_entry_exists()
		self.set_as_cancelled()

	def get_tx_data(self):
		party = frappe.get_doc(self.party_type, self.party)
		if self.party_type == "Supplier" and party.supplier_primary_contact:
			contact = frappe.get_doc("Contact", party.supplier_primary_contact).as_dict()
		elif self.party_type == "Customer" and party.customer_primary_contact:
			contact = frappe.get_doc("Contact", party.customer_primary_contact).as_dict()
		else:
			contact = {}
		if self.party_type == "Supplier" and party.supplier_primary_address:
			address = frappe.get_doc("Address", party.supplier_primary_address).as_dict()
		elif self.party_type == "Customer" and party.customer_primary_address:
			address = frappe.get_doc("Address", party.customer_primary_address).as_dict()
		else:
			address = {}
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		lpm, lpp, lpa = (
			party.get("loyalty_program"),
			ref_doc.get("loyalty_points"),
			ref_doc.get("loyalty_amount"),
		)
		if lpm and lpp and lpa:
			loyalty_points = [lpm, lpp, lpa]
		else:
			loyalty_points = None
		return frappe._dict(
			{
				"amount": self.grand_total,
				"currency": self.currency,
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
				"display_reference_doctype": ref_doc.doctype,
				"display_reference_docname": ref_doc.name,
				"payer_contact": contact,
				"payer_address": address,
				"loyalty_points": loyalty_points,
				"discount_amount": ref_doc.get("discount_amount"),
			}
		)

	def make_invoice(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		si = make_sales_invoice(self.reference_name, ignore_permissions=True)
		si.allocate_advances_automatically = True
		si = si.insert(ignore_permissions=True)
		si.submit()

	def set_as_paid(self):
		if self.payment_channel == "Phone":
			self.db_set("status", "Paid")

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

		party_account_currency = ref_doc.get("party_account_currency") or get_account_currency(party_account)

		bank_amount = self.grand_total
		if party_account_currency == ref_doc.company_currency and party_account_currency != self.currency:
			party_amount = ref_doc.get("base_rounded_total") or ref_doc.get("base_grand_total")
		else:
			party_amount = self.grand_total

		payment_entry = get_payment_entry(
			self.reference_doctype,
			self.reference_name,
			party_amount=party_amount,
			bank_account=self.payment_account,
			bank_amount=bank_amount,
		)

		payment_entry.update(
			{
				"mode_of_payment": self.mode_of_payment,
				"reference_no": self.name,
				"reference_date": nowdate(),
				"remarks": "Payment Entry against {} {} via Payment Request {}".format(
					self.reference_doctype, self.reference_name, self.name
				),
			}
		)

		# Update dimensions
		payment_entry.update(
			{
				"cost_center": self.get("cost_center"),
				"project": self.get("project"),
			}
		)

		if party_account_currency == ref_doc.company_currency and party_account_currency != self.currency:
			amount = payment_entry.base_paid_amount
		else:
			amount = self.grand_total

		payment_entry.received_amount = amount
		payment_entry.get("references")[0].allocated_amount = amount

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


@frappe.whitelist(allow_guest=True)
def make_payment_request(**args):
	"""Make payment request"""

	args = frappe._dict(args)
	ref_doc = args.ref_doc or frappe.get_doc(args.dt, args.dn)

	if ref_doc.doctype not in [
		"Sales Order",
		"Purchase Order",
		"Sales Invoice",
		"Purchase Invoice",
		"POS Invoice",
		"Fees",
	]:
		frappe.throw(
			_("Payment Requests cannot be created against: {0}").format(frappe.bold(ref_doc.doctype))
		)

	gateway_account = get_gateway_details(args) or frappe._dict()

	grand_total = get_amount(ref_doc, gateway_account.get("payment_account"))
	if not grand_total:
		frappe.throw(_("Payment Entry is already created"))

	if args.loyalty_points and ref_doc.doctype == "Sales Order":
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points

		loyalty_amount = validate_loyalty_points(ref_doc, int(args.loyalty_points))  # sets fields on ref_doc
		ref_doc.db_update()
		grand_total = grand_total - loyalty_amount

	bank_account = (
		get_party_bank_account(args.get("party_type"), args.get("party")) if args.get("party_type") else ""
	)

	draft_payment_request = frappe.db.get_value(
		"Payment Request",
		{"reference_doctype": ref_doc.doctype, "reference_name": ref_doc.name, "docstatus": 0},
	)

	existing_payment_request_amount = get_existing_payment_request_amount(ref_doc.doctype, ref_doc.name)

	if existing_payment_request_amount:
		grand_total -= existing_payment_request_amount

	if draft_payment_request:
		frappe.db.set_value(
			"Payment Request", draft_payment_request, "grand_total", grand_total, update_modified=False
		)
		pr = frappe.get_doc("Payment Request", draft_payment_request)
	else:
		pr = frappe.new_doc("Payment Request")

		if not args.get("payment_request_type"):
			args["payment_request_type"] = (
				"Outward" if args.get("dt") in ["Purchase Order", "Purchase Invoice"] else "Inward"
			)

		pr.update(
			{
				"payment_gateway_account": gateway_account.get("name"),
				"payment_gateway": gateway_account.get("payment_gateway"),
				"payment_account": gateway_account.get("payment_account"),
				"payment_channel": gateway_account.get("payment_channel"),
				"payment_request_type": args.get("payment_request_type"),
				"currency": ref_doc.currency,
				"grand_total": grand_total,
				"mode_of_payment": args.mode_of_payment,
				"email_to": args.recipient_id or ref_doc.owner,
				"subject": _("Payment Request for {0}").format(args.dn),
				"message": gateway_account.get("message") or get_dummy_message(ref_doc),
				"reference_doctype": ref_doc.doctype,
				"reference_name": ref_doc.name,
				"company": ref_doc.get("company"),
				"party_type": args.get("party_type") or "Customer",
				"party": args.get("party") or ref_doc.get("customer"),
				"bank_account": bank_account,
				"make_sales_invoice": (
					args.make_sales_invoice  # new standard
					or args.order_type == "Shopping Cart"  # compat for webshop app
				),
				"mute_email": (
					args.mute_email  # new standard
					or args.order_type == "Shopping Cart"  # compat for webshop app
					or gateway_account.get("payment_channel", "Email") != "Email"
				),
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
		frappe.local.response["location"] = pr.payment_url

	if args.return_doc:
		return pr

	return pr.as_dict()


def get_amount(ref_doc, payment_account=None):
	"""get amount based on doctype"""
	dt = ref_doc.doctype
	if dt in ["Sales Order", "Purchase Order"]:
		grand_total = flt(ref_doc.rounded_total) or flt(ref_doc.grand_total)
		grand_total -= get_paid_amount_against_order(dt, ref_doc.name)
	elif dt in ["Sales Invoice", "Purchase Invoice"]:
		if not ref_doc.get("is_pos"):
			if ref_doc.party_account_currency == ref_doc.currency:
				grand_total = flt(ref_doc.grand_total)
			else:
				grand_total = flt(ref_doc.base_grand_total) / ref_doc.conversion_rate
		elif dt == "Sales Invoice":
			for pay in ref_doc.payments:
				if pay.type == "Phone" and pay.account == payment_account:
					grand_total = pay.amount
					break
	elif dt == "POS Invoice":
		for pay in ref_doc.payments:
			if pay.type == "Phone" and pay.account == payment_account:
				grand_total = pay.amount
				break
	elif dt == "Fees":
		grand_total = ref_doc.outstanding_amount

	if grand_total > 0:
		return flt(grand_total, get_currency_precision())
	else:
		frappe.throw(_("Payment Entry is already created"))


def get_existing_payment_request_amount(ref_dt, ref_dn):
	"""
	Get the existing payment request which are unpaid or partially paid for payment channel other than Phone
	and get the summation of existing paid payment request for Phone payment channel.
	"""
	existing_payment_request_amount = frappe.db.sql(
		"""
		select sum(grand_total)
		from `tabPayment Request`
		where
			reference_doctype = %s
			and reference_name = %s
			and docstatus = 1
			and (status != 'Paid'
			or (payment_channel = 'Phone'
				and status = 'Paid'))
	""",
		(ref_dt, ref_dn),
	)
	return flt(existing_payment_request_amount[0][0]) if existing_payment_request_amount else 0


def get_gateway_details(args):  # nosemgrep
	"""
	Return gateway and payment account of default payment gateway
	"""
	gateway_account = args.get("payment_gateway_account", {"is_default": 1})
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


def update_payment_req_status(doc, method):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_reference_details

	for ref in doc.references:
		payment_request_name = frappe.db.get_value(
			"Payment Request",
			{
				"reference_doctype": ref.reference_doctype,
				"reference_name": ref.reference_name,
				"docstatus": 1,
			},
		)

		if payment_request_name:
			ref_details = get_reference_details(
				ref.reference_doctype,
				ref.reference_name,
				doc.party_account_currency,
				doc.party_type,
				doc.party,
			)
			pay_req_doc = frappe.get_doc("Payment Request", payment_request_name)
			status = pay_req_doc.status

			if status != "Paid" and not ref_details.outstanding_amount:
				status = "Paid"
			elif status != "Partially Paid" and ref_details.outstanding_amount != ref_details.total_amount:
				status = "Partially Paid"
			elif ref_details.outstanding_amount == ref_details.total_amount:
				if pay_req_doc.payment_request_type == "Outward":
					status = "Initiated"
				elif pay_req_doc.payment_request_type == "Inward":
					status = "Requested"

			pay_req_doc.db_set("status", status)


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


def get_paid_amount_against_order(dt, dn):
	pe_ref = frappe.qb.DocType("Payment Entry Reference")
	if dt == "Sales Order":
		inv_dt, inv_field = "Sales Invoice Item", "sales_order"
	else:
		inv_dt, inv_field = "Purchase Invoice Item", "purchase_order"
	inv_item = frappe.qb.DocType(inv_dt)
	return (
		frappe.qb.from_(pe_ref)
		.select(
			Sum(pe_ref.allocated_amount),
		)
		.where(
			(pe_ref.docstatus == 1)
			& (
				(pe_ref.reference_name == dn)
				| pe_ref.reference_name.isin(
					frappe.qb.from_(inv_item)
					.select(inv_item.parent)
					.where(inv_item[inv_field] == dn)
					.distinct()
				)
			)
		)
	).run()[0][0] or 0
