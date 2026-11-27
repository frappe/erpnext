import frappe
from frappe import _
from frappe.core.doctype.communication.email import make
from frappe.model.workflow import get_workflow_name
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt, fmt_money, get_link_to_form

import erpnext
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

PAYABLE_DOCTYPES = ("Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order")


@frappe.whitelist()
def record_payment(dt: str, names: str | list, values: str | dict, save: bool = True):
	payment = RecordPayment(dt, get_permitted_names(dt, names), frappe.parse_json(values))
	if not save:
		return payment.payment_entry
	return payment.save()


@frappe.whitelist()
def get_payment_entry_for(dt: str, names: str | list, reference_date: str | None = None):
	first, *others = sort_by_due_date(dt, get_permitted_names(dt, names))
	payment_entry = get_payment_entry(dt, first, reference_date=reference_date)
	for name in others:
		add_invoice(payment_entry, get_payment_entry(dt, name, reference_date=reference_date), name)

	for row in payment_entry.references:
		if row.payment_term and row.payment_term_outstanding:
			row.outstanding_amount = row.payment_term_outstanding

	if others:
		payment_entry.set_amounts()
	return payment_entry


@frappe.whitelist()
def get_unapplied_credit(dt: str, dn: str) -> float:
	if dt not in ("Sales Invoice", "Purchase Invoice"):
		erpnext._refuse()
	frappe.has_permission("Payment Entry", "create", throw=True)
	erpnext.require_permission(dt, dn)
	doc = frappe.get_doc(dt, cstr(dn))
	party_type, account = ("Customer", doc.debit_to) if dt == "Sales Invoice" else ("Supplier", doc.credit_to)

	ple = frappe.qb.DocType("Payment Ledger Entry")
	outstanding = Sum(ple.amount_in_account_currency)
	credits = (
		frappe.qb.from_(ple)
		.select(outstanding)
		.where(
			(ple.company == doc.company)
			& (ple.party_type == party_type)
			& (ple.party == doc.get(frappe.scrub(party_type)))
			& (ple.account == account)
			& (ple.delinked == 0)
		)
		.groupby(ple.against_voucher_type, ple.against_voucher_no)
		.having(outstanding < 0)
	).run(pluck=True)
	return abs(sum(credits))


class RecordPayment:
	def __init__(self, dt: str, names: list, values: dict):
		self.values = frappe._dict(values)
		for fieldname in ("account", "mode_of_payment", "reference_no", "tax_withheld_account"):
			self.values[fieldname] = cstr(self.values.get(fieldname)) or None
		self.payment_entry = get_payment_entry_for(dt, names, self.values.reference_date)
		self.is_receive = self.payment_entry.payment_type == "Receive"
		self.bank_field = "paid_to" if self.is_receive else "paid_from"
		self.party_currency = self.payment_entry.get(
			("paid_from" if self.is_receive else "paid_to") + "_account_currency"
		)
		self.outstanding = sum(abs(flt(row.outstanding_amount)) for row in self.payment_entry.references)
		self.is_refund = any(flt(row.outstanding_amount) < 0 for row in self.payment_entry.references)
		self.is_invoice = dt in ("Sales Invoice", "Purchase Invoice")
		self.has_discount = bool(self.payment_entry.deductions)

		self.set_details()
		self.set_bank_account()
		if self.has_discount:
			return
		self.set_amounts()
		self.set_deductions()
		self.allocate()

	def save(self):
		if self.has_discount:
			frappe.throw(
				_(
					"An early payment discount applies on this reference date. Use Edit Full Form to record it."
				),
				title=_("Early Payment Discount"),
			)

		payment_entry = self.payment_entry
		if payment_entry.has_permission("submit") and not get_workflow_name(payment_entry.doctype):
			payment_entry.submit()
		else:
			payment_entry.insert()

		if self.values.send_email and payment_entry.docstatus == 1 and payment_entry.contact_email:
			self.send_email()
		return payment_entry

	def send_email(self):
		payment_entry = self.payment_entry
		subject, message = (
			(_("Payment Receipt {0}"), _("We have received your payment of {0}. The receipt is attached."))
			if self.is_receive
			else (_("Payment Advice {0}"), _("We have paid {0} to you. The payment advice is attached."))
		)
		amount = fmt_money(payment_entry.paid_amount, currency=payment_entry.paid_from_account_currency)
		make(
			doctype=payment_entry.doctype,
			name=payment_entry.name,
			recipients=payment_entry.contact_email,
			subject=subject.format(payment_entry.name),
			content=message.format(amount),
			send_email=True,
			print_format=frappe.get_meta(payment_entry.doctype).default_print_format or "Standard",
		)

	def set_details(self):
		self.payment_entry.update(
			{
				"posting_date": self.values.posting_date,
				"mode_of_payment": self.values.mode_of_payment,
				"reference_no": self.values.reference_no,
				"reference_date": self.values.reference_date,
			}
		)

	def set_bank_account(self):
		account = self.values.account
		if not account:
			return

		payment_entry = self.payment_entry
		details = frappe.get_cached_value(
			"Account", account, ["account_type", "account_currency", "company"], as_dict=True
		)
		if (
			not details
			or details.company != payment_entry.company
			or details.account_type not in ("Bank", "Cash")
		):
			frappe.throw(
				_("Select a bank or cash account of {0}.").format(frappe.bold(payment_entry.company))
			)
		if details.account_currency != payment_entry.get(f"{self.bank_field}_account_currency"):
			frappe.throw(
				_(
					"{0} is a {1} account. Use Edit Full Form to pay through an account in another currency."
				).format(frappe.bold(account), details.account_currency)
			)

		payment_entry.set(self.bank_field, account)
		payment_entry.set(f"{self.bank_field}_account_type", details.account_type)
		payment_entry.bank_account = frappe.db.get_value(
			"Bank Account",
			{"company": payment_entry.company, "account": account, "is_company_account": 1, "disabled": 0},
			"name",
		)
		payment_entry.bank = payment_entry.bank_account_no = None
		payment_entry.set_bank_account_data()

	def set_amounts(self):
		payment_entry = self.payment_entry
		amount = flt(self.values.party_amount)
		self.validate_amount(amount)

		payment_entry.source_exchange_rate = payment_entry.target_exchange_rate = 0
		payment_entry.set_exchange_rate()

		bank_amount = amount
		if payment_entry.paid_from_account_currency != payment_entry.paid_to_account_currency:
			bank_amount = flt(self.values.bank_amount)
			self.set_rate_from_amounts(amount, bank_amount)

		if self.is_receive:
			payment_entry.paid_amount, payment_entry.received_amount = amount, bank_amount
		else:
			payment_entry.paid_amount, payment_entry.received_amount = bank_amount, amount

	def validate_amount(self, amount: float):
		if amount <= 0:
			frappe.throw(_("Enter an amount greater than zero."))
		if self.is_refund and amount > self.outstanding:
			frappe.throw(
				_("A refund cannot be more than {0}.").format(
					fmt_money(self.outstanding, currency=self.party_currency)
				)
			)

	def set_rate_from_amounts(self, amount: float, bank_amount: float):
		if not bank_amount:
			return

		payment_entry = self.payment_entry
		company_currency = frappe.get_cached_value("Company", payment_entry.company, "default_currency")
		if payment_entry.get(f"{self.bank_field}_account_currency") == company_currency:
			party_rate_field = "source_exchange_rate" if self.is_receive else "target_exchange_rate"
			payment_entry.set(party_rate_field, bank_amount / amount)
		else:
			bank_rate_field = "target_exchange_rate" if self.is_receive else "source_exchange_rate"
			payment_entry.set(bank_rate_field, amount / bank_amount)

	def set_deductions(self):
		if self.is_refund:
			return

		values = self.values
		if self.is_receive and flt(values.bank_charges):
			self.add_deduction(
				values.bank_charges, self.get_company_account("bank_charges_account"), _("Bank Charges")
			)
		if self.is_receive and flt(values.tax_withheld):
			if not values.tax_withheld_account:
				frappe.throw(_("Select the account for Tax Withheld."))
			self.add_deduction(values.tax_withheld, values.tax_withheld_account, _("Tax Withheld"))

		if values.write_off and self.is_invoice:
			self.add_write_off()

	def add_write_off(self):
		settled = (
			flt(self.values.party_amount) + flt(self.values.bank_charges) + flt(self.values.tax_withheld)
		)
		remaining = self.outstanding - settled
		if remaining > 0:
			sign = 1 if self.is_receive else -1
			self.add_deduction(
				sign * remaining, self.get_company_account("write_off_account"), _("Write Off")
			)

	def add_deduction(self, amount: float, account: str, description: str):
		payment_entry = self.payment_entry
		payment_entry.append(
			"deductions",
			{
				"account": account,
				"cost_center": payment_entry.cost_center
				or frappe.get_cached_value("Company", payment_entry.company, "cost_center"),
				"amount": flt(
					flt(amount) * payment_entry.get_exchange_rate(),
					payment_entry.precision("amount", "deductions"),
				),
				"description": description,
			},
		)

	def get_company_account(self, fieldname: str) -> str:
		company = self.payment_entry.company
		account = frappe.get_cached_value("Company", company, fieldname)
		if not account:
			frappe.throw(
				_("Set {0} in Company {1}.").format(
					_(frappe.get_meta("Company").get_label(fieldname)), get_link_to_form("Company", company)
				)
			)
		return account

	def allocate(self):
		payment_entry = self.payment_entry
		party_amount = payment_entry.paid_amount if self.is_receive else payment_entry.received_amount
		payment_entry.allocate_amount_to_references(party_amount, False, True)
		payment_entry.set_amounts()


def sort_by_due_date(dt: str, names: list) -> list:
	if len(names) < 2:
		return names
	return frappe.get_all(dt, filters={"name": ["in", names]}, order_by="due_date, name", pluck="name")


def add_invoice(payment_entry, invoice_payment, name: str):
	party_account = "paid_from" if payment_entry.payment_type == "Receive" else "paid_to"
	same_payment = all(
		payment_entry.get(field) == invoice_payment.get(field)
		for field in ("company", "payment_type", "party_type", "party", party_account)
	)
	if not (same_payment and invoice_payment.references):
		frappe.throw(
			_(
				"{0} cannot be paid together with the other invoices. Select unpaid invoices of one {1}."
			).format(frappe.bold(name), _(payment_entry.party_type))
		)

	for table in ("references", "deductions"):
		for row in invoice_payment.get(table):
			payment_entry.append(table, row.as_dict(no_default_fields=True))
	payment_entry.paid_amount += invoice_payment.paid_amount
	payment_entry.received_amount += invoice_payment.received_amount


def get_permitted_names(dt: str, names: str | list) -> list[str]:
	names = frappe.parse_json(names)
	if dt not in PAYABLE_DOCTYPES or not isinstance(names, list) or not names:
		erpnext._refuse()
	for name in names:
		erpnext.require_permission(dt, name)
	return [cstr(name) for name in names]
