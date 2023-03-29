# Copyright (c) 2015, Frappe Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt


from collections import OrderedDict

import frappe
from frappe import _, qb, scrub
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Date
from frappe.utils import cint, cstr, flt, getdate, nowdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.utils import get_currency_precision

#  This report gives a summary of all Outstanding Invoices considering the following

#  1. Invoice can be booked via Sales/Purchase Invoice or Journal Entry
#  2. Report handles both receivable and payable
#  3. Key balances for each row are "Invoiced Amount", "Paid Amount", "Credit/Debit Note Amount", "Oustanding Amount"
#  4. For explicit payment terms in invoice (example: 30% advance, 30% on delivery, 40% post delivery),
#     the invoice will be broken up into multiple rows, one for each payment term
#  5. If there are payments after the report date (post dated), these will be updated in additional columns
#     for future amount
#  6. Configurable Ageing Groups (0-30, 30-60 etc) can be set via filters
#  7. For overpayment against an invoice with payment terms, there will be an additional row
#  8. Invoice details like Sales Persons, Delivery Notes are also fetched comma separated
#  9. Report amounts are in "Party Currency" if party is selected, or company currency for multi-party
# 10. This reports is based on all GL Entries that are made against account_type "Receivable" or "Payable"


def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)


class ReceivablePayableReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.qb_selection_filter = []
		self.ple = qb.DocType("Payment Ledger Entry")
		self.filters.report_date = getdate(self.filters.report_date or nowdate())
		self.age_as_on = (
			getdate(nowdate())
			if self.filters.report_date > getdate(nowdate())
			else self.filters.report_date
		)

	def run(self, args):
		self.filters.update(args)
		self.set_defaults()
		self.party_naming_by = frappe.db.get_value(
			args.get("naming_by")[0], None, args.get("naming_by")[1]
		)
		self.get_columns()
		self.get_data()
		self.get_chart_data()
		return self.columns, self.data, None, self.chart, None, self.skip_total_row

	def set_defaults(self):
		if not self.filters.get("company"):
			self.filters.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.company_currency = frappe.get_cached_value(
			"Company", self.filters.get("company"), "default_currency"
		)
		self.currency_precision = get_currency_precision() or 2
		self.dr_or_cr = "debit" if self.filters.party_type == "Customer" else "credit"
		self.party_type = self.filters.party_type
		self.party_details = {}
		self.invoices = set()
		self.skip_total_row = 0

		if self.filters.get("group_by_party"):
			self.previous_party = ""
			self.total_row_map = {}
			self.skip_total_row = 1

	def get_data(self):
		self.get_ple_entries()
		self.get_sales_invoices_or_customers_based_on_sales_person()
		self.voucher_balance = OrderedDict()
		self.init_voucher_balance()  # invoiced, paid, credit_note, outstanding

		# Build delivery note map against all sales invoices
		self.build_delivery_note_map()

		# Get invoice details like bill_no, due_date etc for all invoices
		self.get_invoice_details()

		# fetch future payments against invoices
		self.get_future_payments()

		# Get return entries
		self.get_return_entries()

		# Get Exchange Rate Revaluations
		self.get_exchange_rate_revaluations()

		self.data = []

		for ple in self.ple_entries:
			self.update_voucher_balance(ple)

		self.build_data()

	def init_voucher_balance(self):
		# build all keys, since we want to exclude vouchers beyond the report date
		for ple in self.ple_entries:
			# get the balance object for voucher_type
			key = (ple.voucher_type, ple.voucher_no, ple.party)
			if not key in self.voucher_balance:
				self.voucher_balance[key] = frappe._dict(
					voucher_type=ple.voucher_type,
					voucher_no=ple.voucher_no,
					party=ple.party,
					party_account=ple.account,
					posting_date=ple.posting_date,
					account_currency=ple.account_currency,
					remarks=ple.remarks,
					invoiced=0.0,
					paid=0.0,
					credit_note=0.0,
					outstanding=0.0,
					invoiced_in_account_currency=0.0,
					paid_in_account_currency=0.0,
					credit_note_in_account_currency=0.0,
					outstanding_in_account_currency=0.0,
				)
			self.get_invoices(ple)

			if self.filters.get("group_by_party"):
				self.init_subtotal_row(ple.party)

		if self.filters.get("group_by_party"):
			self.init_subtotal_row("Total")

	def get_invoices(self, ple):
		if ple.voucher_type in ("Sales Invoice", "Purchase Invoice"):
			if self.filters.get("sales_person"):
				if ple.voucher_no in self.sales_person_records.get(
					"Sales Invoice", []
				) or ple.party in self.sales_person_records.get("Customer", []):
					self.invoices.add(ple.voucher_no)
			else:
				self.invoices.add(ple.voucher_no)

	def init_subtotal_row(self, party):
		if not self.total_row_map.get(party):
			self.total_row_map.setdefault(party, {"party": party, "bold": 1})

			for field in self.get_currency_fields():
				self.total_row_map[party][field] = 0.0

	def get_currency_fields(self):
		return [
			"invoiced",
			"paid",
			"credit_note",
			"outstanding",
			"range1",
			"range2",
			"range3",
			"range4",
			"range5",
			"future_amount",
			"remaining_balance",
		]

	def get_voucher_balance(self, ple):
		if self.filters.get("sales_person"):
			if not (
				ple.party in self.sales_person_records.get("Customer", [])
				or ple.against_voucher_no in self.sales_person_records.get("Sales Invoice", [])
			):
				return

		key = (ple.against_voucher_type, ple.against_voucher_no, ple.party)
		row = self.voucher_balance.get(key)

		if not row:
			# no invoice, this is an invoice / stand-alone payment / credit note
			row = self.voucher_balance.get((ple.voucher_type, ple.voucher_no, ple.party))

		return row

	def update_voucher_balance(self, ple):
		# get the row where this balance needs to be updated
		# if its a payment, it will return the linked invoice or will be considered as advance
		row = self.get_voucher_balance(ple)
		if not row:
			return

		# amount in "Party Currency", if its supplied. If not, amount in company currency
		if self.filters.get(scrub(self.party_type)):
			amount = ple.amount_in_account_currency
		else:
			amount = ple.amount
		amount_in_account_currency = ple.amount_in_account_currency

		# update voucher
		if ple.amount > 0:
			if (
				ple.voucher_type in ["Journal Entry", "Payment Entry"]
				and ple.voucher_no != ple.against_voucher_no
			):
				row.paid -= amount
				row.paid_in_account_currency -= amount_in_account_currency
			else:
				row.invoiced += amount
				row.invoiced_in_account_currency += amount_in_account_currency
		else:
			if self.is_invoice(ple):
				row.credit_note -= amount
				row.credit_note_in_account_currency -= amount_in_account_currency
			else:
				row.paid -= amount
				row.paid_in_account_currency -= amount_in_account_currency

		if ple.cost_center:
			row.cost_center = str(ple.cost_center)

	def update_sub_total_row(self, row, party):
		total_row = self.total_row_map.get(party)

		for field in self.get_currency_fields():
			total_row[field] += row.get(field, 0.0)

	def append_subtotal_row(self, party):
		sub_total_row = self.total_row_map.get(party)

		if sub_total_row:
			self.data.append(sub_total_row)
			self.data.append({})
			self.update_sub_total_row(sub_total_row, "Total")

	def build_data(self):
		# set outstanding for all the accumulated balances
		# as we can use this to filter out invoices without outstanding
		for key, row in self.voucher_balance.items():
			row.outstanding = flt(row.invoiced - row.paid - row.credit_note, self.currency_precision)
			row.outstanding_in_account_currency = flt(
				row.invoiced_in_account_currency
				- row.paid_in_account_currency
				- row.credit_note_in_account_currency,
				self.currency_precision,
			)

			row.invoice_grand_total = row.invoiced

			if (abs(row.outstanding) > 1.0 / 10**self.currency_precision) and (
				(abs(row.outstanding_in_account_currency) > 1.0 / 10**self.currency_precision)
				or (row.voucher_no in self.err_journals)
			):

				# non-zero oustanding, we must consider this row

				if self.is_invoice(row) and self.filters.based_on_payment_terms:
					# is an invoice, allocate based on fifo
					# adds a list `payment_terms` which contains new rows for each term
					self.allocate_outstanding_based_on_payment_terms(row)

					if row.payment_terms:
						# make separate rows for each payment term
						for d in row.payment_terms:
							if d.outstanding > 0:
								self.append_row(d)

						# if there is overpayment, add another row
						self.allocate_extra_payments_or_credits(row)
					else:
						self.append_row(row)
				else:
					self.append_row(row)

		if self.filters.get("group_by_party"):
			self.append_subtotal_row(self.previous_party)
			if self.data:
				self.data.append(self.total_row_map.get("Total"))

	def append_row(self, row):
		self.allocate_future_payments(row)
		self.set_invoice_details(row)
		self.set_party_details(row)
		self.set_ageing(row)

		if self.filters.get("group_by_party"):
			self.update_sub_total_row(row, row.party)
			if self.previous_party and (self.previous_party != row.party):
				self.append_subtotal_row(self.previous_party)
			self.previous_party = row.party

		self.data.append(row)

	def set_invoice_details(self, row):
		invoice_details = self.invoice_details.get(row.voucher_no, {})
		if row.due_date:
			invoice_details.pop("due_date", None)
		row.update(invoice_details)

		if row.voucher_type == "Sales Invoice":
			if self.filters.show_delivery_notes:
				self.set_delivery_notes(row)

			if self.filters.show_sales_person and row.sales_team:
				row.sales_person = ", ".join(row.sales_team)
				del row["sales_team"]

	def set_delivery_notes(self, row):
		delivery_notes = self.delivery_notes.get(row.voucher_no, [])
		if delivery_notes:
			row.delivery_notes = ", ".join(delivery_notes)

	def build_delivery_note_map(self):
		if self.invoices and self.filters.show_delivery_notes:
			self.delivery_notes = frappe._dict()

			# delivery note link inside sales invoice
			si_against_dn = frappe.db.sql(
				"""
				select parent, delivery_note
				from `tabSales Invoice Item`
				where docstatus=1 and parent in (%s)
			"""
				% (",".join(["%s"] * len(self.invoices))),
				tuple(self.invoices),
				as_dict=1,
			)

			for d in si_against_dn:
				if d.delivery_note:
					self.delivery_notes.setdefault(d.parent, set()).add(d.delivery_note)

			dn_against_si = frappe.db.sql(
				"""
				select distinct parent, against_sales_invoice
				from `tabDelivery Note Item`
				where against_sales_invoice in (%s)
			"""
				% (",".join(["%s"] * len(self.invoices))),
				tuple(self.invoices),
				as_dict=1,
			)

			for d in dn_against_si:
				self.delivery_notes.setdefault(d.against_sales_invoice, set()).add(d.parent)

	def get_invoice_details(self):
		self.invoice_details = frappe._dict()
		if self.party_type == "Customer":
			si_list = frappe.db.sql(
				"""
				select name, due_date, po_no
				from `tabSales Invoice`
				where posting_date <= %s
			""",
				self.filters.report_date,
				as_dict=1,
			)
			for d in si_list:
				self.invoice_details.setdefault(d.name, d)

			# Get Sales Team
			if self.filters.show_sales_person:
				sales_team = frappe.db.sql(
					"""
					select parent, sales_person
					from `tabSales Team`
					where parenttype = 'Sales Invoice'
				""",
					as_dict=1,
				)
				for d in sales_team:
					self.invoice_details.setdefault(d.parent, {}).setdefault("sales_team", []).append(
						d.sales_person
					)

		if self.party_type == "Supplier":
			for pi in frappe.db.sql(
				"""
				select name, due_date, bill_no, bill_date
				from `tabPurchase Invoice`
				where posting_date <= %s
			""",
				self.filters.report_date,
				as_dict=1,
			):
				self.invoice_details.setdefault(pi.name, pi)

		# Invoices booked via Journal Entries
		journal_entries = frappe.db.sql(
			"""
			select name, due_date, bill_no, bill_date
			from `tabJournal Entry`
			where posting_date <= %s
		""",
			self.filters.report_date,
			as_dict=1,
		)

		for je in journal_entries:
			if je.bill_no:
				self.invoice_details.setdefault(je.name, je)

	def set_party_details(self, row):
		# customer / supplier name
		party_details = self.get_party_details(row.party) or {}
		row.update(party_details)
		if self.filters.get(scrub(self.filters.party_type)):
			row.currency = row.account_currency
		else:
			row.currency = self.company_currency

	def allocate_outstanding_based_on_payment_terms(self, row):
		self.get_payment_terms(row)
		for term in row.payment_terms:

			# update "paid" and "oustanding" for this term
			if not term.paid:
				self.allocate_closing_to_term(row, term, "paid")

			# update "credit_note" and "oustanding" for this term
			if term.outstanding:
				self.allocate_closing_to_term(row, term, "credit_note")

		row.payment_terms = sorted(row.payment_terms, key=lambda x: x["due_date"])

	def get_payment_terms(self, row):
		# build payment_terms for row
		payment_terms_details = frappe.db.sql(
			"""
			select
				si.name, si.party_account_currency, si.currency, si.conversion_rate,
				ps.due_date, ps.payment_term, ps.payment_amount, ps.description, ps.paid_amount, ps.discounted_amount
			from `tab{0}` si, `tabPayment Schedule` ps
			where
				si.name = ps.parent and
				si.name = %s
			order by ps.paid_amount desc, due_date
		""".format(
				row.voucher_type
			),
			row.voucher_no,
			as_dict=1,
		)

		original_row = frappe._dict(row)
		row.payment_terms = []

		# If no or single payment terms, no need to split the row
		if len(payment_terms_details) <= 1:
			return

		for d in payment_terms_details:
			term = frappe._dict(original_row)
			self.append_payment_term(row, d, term)

	def append_payment_term(self, row, d, term):
		if (
			self.filters.get("customer") or self.filters.get("supplier")
		) and d.currency == d.party_account_currency:
			invoiced = d.payment_amount
		else:
			invoiced = flt(flt(d.payment_amount) * flt(d.conversion_rate), self.currency_precision)

		row.payment_terms.append(
			term.update(
				{
					"due_date": d.due_date,
					"invoiced": invoiced,
					"invoice_grand_total": row.invoiced,
					"payment_term": d.description or d.payment_term,
					"paid": d.paid_amount + d.discounted_amount,
					"credit_note": 0.0,
					"outstanding": invoiced - d.paid_amount - d.discounted_amount,
				}
			)
		)

		if d.paid_amount:
			row["paid"] -= d.paid_amount + d.discounted_amount

	def allocate_closing_to_term(self, row, term, key):
		if row[key]:
			if row[key] > term.outstanding:
				term[key] = term.outstanding
				row[key] -= term.outstanding
			else:
				term[key] = row[key]
				row[key] = 0
		term.outstanding -= term[key]

	def allocate_extra_payments_or_credits(self, row):
		# allocate extra payments / credits
		additional_row = None
		for key in ("paid", "credit_note"):
			if row[key] > 0:
				if not additional_row:
					additional_row = frappe._dict(row)
				additional_row.invoiced = 0.0
				additional_row[key] = row[key]

		if additional_row:
			additional_row.outstanding = (
				additional_row.invoiced - additional_row.paid - additional_row.credit_note
			)
			self.append_row(additional_row)

	def get_future_payments(self):
		if self.filters.show_future_payments:
			self.future_payments = frappe._dict()
			future_payments = list(self.get_future_payments_from_payment_entry())
			future_payments += list(self.get_future_payments_from_journal_entry())
			if future_payments:
				for d in future_payments:
					if d.future_amount and d.invoice_no:
						self.future_payments.setdefault((d.invoice_no, d.party), []).append(d)

	def get_future_payments_from_payment_entry(self):
		return frappe.db.sql(
			"""
			select
				ref.reference_name as invoice_no,
				payment_entry.party,
				payment_entry.party_type,
				payment_entry.posting_date as future_date,
				ref.allocated_amount as future_amount,
				payment_entry.reference_no as future_ref
			from
				`tabPayment Entry` as payment_entry inner join `tabPayment Entry Reference` as ref
			on
				(ref.parent = payment_entry.name)
			where
				payment_entry.docstatus < 2
				and payment_entry.posting_date > %s
				and payment_entry.party_type = %s
			""",
			(self.filters.report_date, self.party_type),
			as_dict=1,
		)

	def get_future_payments_from_journal_entry(self):
		if self.filters.get("party"):
			amount_field = (
				"jea.debit_in_account_currency - jea.credit_in_account_currency"
				if self.party_type == "Supplier"
				else "jea.credit_in_account_currency - jea.debit_in_account_currency"
			)
		else:
			amount_field = "jea.debit - " if self.party_type == "Supplier" else "jea.credit"

		return frappe.db.sql(
			"""
			select
				jea.reference_name as invoice_no,
				jea.party,
				jea.party_type,
				je.posting_date as future_date,
				sum('{0}') as future_amount,
				je.cheque_no as future_ref
			from
				`tabJournal Entry` as je inner join `tabJournal Entry Account` as jea
			on
				(jea.parent = je.name)
			where
				je.docstatus < 2
				and je.posting_date > %s
				and jea.party_type = %s
				and jea.reference_name is not null and jea.reference_name != ''
			group by je.name, jea.reference_name
			having future_amount > 0
			""".format(
				amount_field
			),
			(self.filters.report_date, self.party_type),
			as_dict=1,
		)

	def allocate_future_payments(self, row):
		# future payments are captured in additional columns
		# this method allocates pending future payments against a voucher to
		# the current row (which could be generated from payment terms)
		if not self.filters.show_future_payments:
			return

		row.remaining_balance = row.outstanding
		row.future_amount = 0.0
		for future in self.future_payments.get((row.voucher_no, row.party), []):
			if row.remaining_balance > 0 and future.future_amount:
				if future.future_amount > row.outstanding:
					row.future_amount = row.outstanding
					future.future_amount = future.future_amount - row.outstanding
					row.remaining_balance = 0
				else:
					row.future_amount += future.future_amount
					future.future_amount = 0
					row.remaining_balance = row.outstanding - row.future_amount

				row.setdefault("future_ref", []).append(
					cstr(future.future_ref) + "/" + cstr(future.future_date)
				)

		if row.future_ref:
			row.future_ref = ", ".join(row.future_ref)

	def get_return_entries(self):
		doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
		filters = {"is_return": 1, "docstatus": 1}
		party_field = scrub(self.filters.party_type)
		if self.filters.get(party_field):
			filters.update({party_field: self.filters.get(party_field)})
		self.return_entries = frappe._dict(
			frappe.get_all(doctype, filters, ["name", "return_against"], as_list=1)
		)

	def set_ageing(self, row):
		if self.filters.ageing_based_on == "Due Date":
			# use posting date as a fallback for advances posted via journal and payment entry
			# when ageing viewed by due date
			entry_date = row.due_date or row.posting_date
		elif self.filters.ageing_based_on == "Supplier Invoice Date":
			entry_date = row.bill_date
		else:
			entry_date = row.posting_date

		self.get_ageing_data(entry_date, row)

		# ageing buckets should not have amounts if due date is not reached
		if getdate(entry_date) > getdate(self.filters.report_date):
			row.range1 = row.range2 = row.range3 = row.range4 = row.range5 = 0.0

		row.total_due = row.range1 + row.range2 + row.range3 + row.range4 + row.range5

	def get_ageing_data(self, entry_date, row):
		# [0-30, 30-60, 60-90, 90-120, 120-above]
		row.range1 = row.range2 = row.range3 = row.range4 = row.range5 = 0.0

		if not (self.age_as_on and entry_date):
			return

		row.age = (getdate(self.age_as_on) - getdate(entry_date)).days or 0
		index = None

		if not (
			self.filters.range1 and self.filters.range2 and self.filters.range3 and self.filters.range4
		):
			self.filters.range1, self.filters.range2, self.filters.range3, self.filters.range4 = (
				30,
				60,
				90,
				120,
			)

		for i, days in enumerate(
			[self.filters.range1, self.filters.range2, self.filters.range3, self.filters.range4]
		):
			if cint(row.age) <= cint(days):
				index = i
				break

		if index is None:
			index = 4
		row["range" + str(index + 1)] = row.outstanding

	def get_ple_entries(self):
		# get all the GL entries filtered by the given filters

		self.prepare_conditions()

		if self.filters.show_future_payments:
			self.qb_selection_filter.append(
				(
					self.ple.posting_date.lte(self.filters.report_date)
					| (
						(self.ple.voucher_no == self.ple.against_voucher_no)
						& (Date(self.ple.creation).lte(self.filters.report_date))
					)
				)
			)
		else:
			self.qb_selection_filter.append(self.ple.posting_date.lte(self.filters.report_date))

		ple = qb.DocType("Payment Ledger Entry")
		query = (
			qb.from_(ple)
			.select(
				ple.account,
				ple.voucher_type,
				ple.voucher_no,
				ple.against_voucher_type,
				ple.against_voucher_no,
				ple.party_type,
				ple.cost_center,
				ple.party,
				ple.posting_date,
				ple.due_date,
				ple.account_currency,
				ple.amount,
				ple.amount_in_account_currency,
				ple.remarks,
			)
			.where(ple.delinked == 0)
			.where(Criterion.all(self.qb_selection_filter))
		)

		if self.filters.get("group_by_party"):
			query = query.orderby(self.ple.party, self.ple.posting_date)
		else:
			query = query.orderby(self.ple.posting_date, self.ple.party)

		self.ple_entries = query.run(as_dict=True)

	def get_sales_invoices_or_customers_based_on_sales_person(self):
		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.get("sales_person"), ["lft", "rgt"])

			records = frappe.db.sql(
				"""
				select distinct parent, parenttype
				from `tabSales Team` steam
				where parenttype in ('Customer', 'Sales Invoice')
					and exists(select name from `tabSales Person` where lft >= %s and rgt <= %s and name = steam.sales_person)
			""",
				(lft, rgt),
				as_dict=1,
			)

			self.sales_person_records = frappe._dict()
			for d in records:
				self.sales_person_records.setdefault(d.parenttype, set()).add(d.parent)

	def prepare_conditions(self):
		self.qb_selection_filter = []
		party_type_field = scrub(self.party_type)
		self.qb_selection_filter.append(self.ple.party_type == self.party_type)

		self.add_common_filters(party_type_field=party_type_field)

		if party_type_field == "customer":
			self.add_customer_filters()

		elif party_type_field == "supplier":
			self.add_supplier_filters()

		if self.filters.cost_center:
			self.get_cost_center_conditions()

		self.add_accounting_dimensions_filters()

	def get_cost_center_conditions(self):
		lft, rgt = frappe.db.get_value("Cost Center", self.filters.cost_center, ["lft", "rgt"])
		cost_center_list = [
			center.name
			for center in frappe.get_list("Cost Center", filters={"lft": (">=", lft), "rgt": ("<=", rgt)})
		]
		self.qb_selection_filter.append(self.ple.cost_center.isin(cost_center_list))

	def add_common_filters(self, party_type_field):
		if self.filters.company:
			self.qb_selection_filter.append(self.ple.company == self.filters.company)

		if self.filters.finance_book:
			self.qb_selection_filter.append(self.ple.finance_book == self.filters.finance_book)

		if self.filters.get(party_type_field):
			self.qb_selection_filter.append(self.ple.party == self.filters.get(party_type_field))

		if self.filters.party_account:
			self.qb_selection_filter.append(self.ple.account == self.filters.party_account)
		else:
			# get GL with "receivable" or "payable" account_type
			account_type = "Receivable" if self.party_type == "Customer" else "Payable"
			accounts = [
				d.name
				for d in frappe.get_all(
					"Account", filters={"account_type": account_type, "company": self.filters.company}
				)
			]

			if accounts:
				self.qb_selection_filter.append(self.ple.account.isin(accounts))

	def add_customer_filters(
		self,
	):
		self.customer = qb.DocType("Customer")

		if self.filters.get("customer_group"):
			self.get_hierarchical_filters("Customer Group", "customer_group")

		if self.filters.get("territory"):
			self.get_hierarchical_filters("Territory", "territory")

		if self.filters.get("payment_terms_template"):
			self.qb_selection_filter.append(
				self.ple.party.isin(
					qb.from_(self.customer)
					.select(self.customer.name)
					.where(self.customer.payment_terms == self.filters.get("payment_terms_template"))
				)
			)

		if self.filters.get("sales_partner"):
			self.qb_selection_filter.append(
				self.ple.party.isin(
					qb.from_(self.customer)
					.select(self.customer.name)
					.where(self.customer.default_sales_partner == self.filters.get("sales_partner"))
				)
			)

	def add_supplier_filters(self):
		supplier = qb.DocType("Supplier")
		if self.filters.get("supplier_group"):
			self.qb_selection_filter.append(
				self.ple.party.isin(
					qb.from_(supplier)
					.select(supplier.name)
					.where(supplier.supplier_group == self.filters.get("supplier_group"))
				)
			)

		if self.filters.get("payment_terms_template"):
			self.qb_selection_filter.append(
				self.ple.party.isin(
					qb.from_(supplier)
					.select(supplier.name)
					.where(supplier.payment_terms == self.filters.get("supplier_group"))
				)
			)

	def get_hierarchical_filters(self, doctype, key):
		lft, rgt = frappe.db.get_value(doctype, self.filters.get(key), ["lft", "rgt"])

		doc = qb.DocType(doctype)
		ple = self.ple
		customer = self.customer
		groups = qb.from_(doc).select(doc.name).where((doc.lft >= lft) & (doc.rgt <= rgt))
		customers = qb.from_(customer).select(customer.name).where(customer[key].isin(groups))
		self.qb_selection_filter.append(ple.party.isin(customers))

	def add_accounting_dimensions_filters(self):
		accounting_dimensions = get_accounting_dimensions(as_list=False)

		if accounting_dimensions:
			for dimension in accounting_dimensions:
				if self.filters.get(dimension.fieldname):
					if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
						self.filters[dimension.fieldname] = get_dimension_with_children(
							dimension.document_type, self.filters.get(dimension.fieldname)
						)
						self.qb_selection_filter.append(
							self.ple[dimension.fieldname].isin(self.filters[dimension.fieldname])
						)
					else:
						self.qb_selection_filter.append(
							self.ple[dimension.fieldname].isin(self.filters[dimension.fieldname])
						)

	def is_invoice(self, ple):
		if ple.voucher_type in ("Sales Invoice", "Purchase Invoice"):
			return True

	def get_party_details(self, party):
		if not party in self.party_details:
			if self.party_type == "Customer":
				fields = ["customer_name", "territory", "customer_group", "customer_primary_contact"]

				if self.filters.get("sales_partner"):
					fields.append("default_sales_partner")

				self.party_details[party] = frappe.db.get_value(
					"Customer",
					party,
					fields,
					as_dict=True,
				)
			else:
				self.party_details[party] = frappe.db.get_value(
					"Supplier", party, ["supplier_name", "supplier_group"], as_dict=True
				)

		return self.party_details[party]

	def get_columns(self):
		self.columns = []
		self.add_column("Posting Date", fieldtype="Date")
		self.add_column(
			label=_(self.party_type),
			fieldname="party",
			fieldtype="Link",
			options=self.party_type,
			width=180,
		)
		self.add_column(
			label="Receivable Account" if self.party_type == "Customer" else "Payable Account",
			fieldname="party_account",
			fieldtype="Link",
			options="Account",
			width=180,
		)

		if self.party_naming_by == "Naming Series":
			self.add_column(
				_("{0} Name").format(self.party_type),
				fieldname=scrub(self.party_type) + "_name",
				fieldtype="Data",
			)

		if self.party_type == "Customer":
			self.add_column(
				_("Customer Contact"),
				fieldname="customer_primary_contact",
				fieldtype="Link",
				options="Contact",
			)

		self.add_column(label=_("Cost Center"), fieldname="cost_center", fieldtype="Data")
		self.add_column(label=_("Voucher Type"), fieldname="voucher_type", fieldtype="Data")
		self.add_column(
			label=_("Voucher No"),
			fieldname="voucher_no",
			fieldtype="Dynamic Link",
			options="voucher_type",
			width=180,
		)

		self.add_column(label="Due Date", fieldtype="Date")

		if self.party_type == "Supplier":
			self.add_column(label=_("Bill No"), fieldname="bill_no", fieldtype="Data")
			self.add_column(label=_("Bill Date"), fieldname="bill_date", fieldtype="Date")

		if self.filters.based_on_payment_terms:
			self.add_column(label=_("Payment Term"), fieldname="payment_term", fieldtype="Data")
			self.add_column(label=_("Invoice Grand Total"), fieldname="invoice_grand_total")

		self.add_column(_("Invoiced Amount"), fieldname="invoiced")
		self.add_column(_("Paid Amount"), fieldname="paid")
		if self.party_type == "Customer":
			self.add_column(_("Credit Note"), fieldname="credit_note")
		else:
			# note: fieldname is still `credit_note`
			self.add_column(_("Debit Note"), fieldname="credit_note")
		self.add_column(_("Outstanding Amount"), fieldname="outstanding")

		self.setup_ageing_columns()

		self.add_column(
			label=_("Currency"), fieldname="currency", fieldtype="Link", options="Currency", width=80
		)

		if self.filters.show_future_payments:
			self.add_column(label=_("Future Payment Ref"), fieldname="future_ref", fieldtype="Data")
			self.add_column(label=_("Future Payment Amount"), fieldname="future_amount")
			self.add_column(label=_("Remaining Balance"), fieldname="remaining_balance")

		if self.filters.party_type == "Customer":
			self.add_column(label=_("Customer LPO"), fieldname="po_no", fieldtype="Data")

			# comma separated list of linked delivery notes
			if self.filters.show_delivery_notes:
				self.add_column(label=_("Delivery Notes"), fieldname="delivery_notes", fieldtype="Data")
			self.add_column(
				label=_("Territory"), fieldname="territory", fieldtype="Link", options="Territory"
			)
			self.add_column(
				label=_("Customer Group"),
				fieldname="customer_group",
				fieldtype="Link",
				options="Customer Group",
			)
			if self.filters.show_sales_person:
				self.add_column(label=_("Sales Person"), fieldname="sales_person", fieldtype="Data")

			if self.filters.sales_partner:
				self.add_column(label=_("Sales Partner"), fieldname="default_sales_partner", fieldtype="Data")

		if self.filters.party_type == "Supplier":
			self.add_column(
				label=_("Supplier Group"),
				fieldname="supplier_group",
				fieldtype="Link",
				options="Supplier Group",
			)

		if self.filters.show_remarks:
			self.add_column(label=_("Remarks"), fieldname="remarks", fieldtype="Text", width=200),

	def add_column(self, label, fieldname=None, fieldtype="Currency", options=None, width=120):
		if not fieldname:
			fieldname = scrub(label)
		if fieldtype == "Currency":
			options = "currency"
		if fieldtype == "Date":
			width = 90

		self.columns.append(
			dict(label=label, fieldname=fieldname, fieldtype=fieldtype, options=options, width=width)
		)

	def setup_ageing_columns(self):
		# for charts
		self.ageing_column_labels = []
		self.add_column(label=_("Age (Days)"), fieldname="age", fieldtype="Int", width=80)

		for i, label in enumerate(
			[
				"0-{range1}".format(range1=self.filters["range1"]),
				"{range1}-{range2}".format(
					range1=cint(self.filters["range1"]) + 1, range2=self.filters["range2"]
				),
				"{range2}-{range3}".format(
					range2=cint(self.filters["range2"]) + 1, range3=self.filters["range3"]
				),
				"{range3}-{range4}".format(
					range3=cint(self.filters["range3"]) + 1, range4=self.filters["range4"]
				),
				_("{range4}-Above").format(range4=cint(self.filters["range4"]) + 1),
			]
		):
			self.add_column(label=label, fieldname="range" + str(i + 1))
			self.ageing_column_labels.append(label)

	def get_chart_data(self):
		rows = []
		for row in self.data:
			row = frappe._dict(row)
			if not cint(row.bold):
				values = [row.range1, row.range2, row.range3, row.range4, row.range5]
				precision = cint(frappe.db.get_default("float_precision")) or 2
				rows.append({"values": [flt(val, precision) for val in values]})

		self.chart = {
			"data": {"labels": self.ageing_column_labels, "datasets": rows},
			"type": "percentage",
		}

	def get_exchange_rate_revaluations(self):
		je = qb.DocType("Journal Entry")
		results = (
			qb.from_(je)
			.select(je.name)
			.where(
				(je.company == self.filters.company)
				& (je.posting_date.lte(self.filters.report_date))
				& (je.voucher_type == "Exchange Rate Revaluation")
			)
			.run()
		)
		self.err_journals = [x[0] for x in results] if results else []
