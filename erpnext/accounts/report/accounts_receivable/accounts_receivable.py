# Copyright (c) 2015, Frappe Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt


from collections import OrderedDict

import frappe
from frappe import _, qb, query_builder, scrub
from frappe.database.schema import get_definition
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Date, Substring, Sum
from frappe.utils import cint, cstr, flt, getdate, nowdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.utils import (
	build_qb_match_conditions,
	get_advance_payment_doctypes,
	get_currency_precision,
	get_party_types_from_account_type,
)

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
#  9. Report amounts are in party currency if in_party_currency is selected, otherwise company currency
# 10. This report is based on Payment Ledger Entries


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)


class ReceivablePayableReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.qb_selection_filter = []
		self.ple = qb.DocType("Payment Ledger Entry")
		self.filters.report_date = getdate(self.filters.report_date or nowdate())
		self.age_as_on = (
			getdate(nowdate())
			if "calculate_ageing_with" not in self.filters
			or self.filters.calculate_ageing_with == "Today Date"
			else self.filters.report_date
		)

		if not self.filters.range:
			self.filters.range = "30, 60, 90, 120"
		self.ranges = [num.strip() for num in self.filters.range.split(",") if num.strip().isdigit()]
		self.range_numbers = [num for num in range(1, len(self.ranges) + 2)]
		self.ple_fetch_method = (
			frappe.get_single_value("Accounts Settings", "receivable_payable_fetch_method")
			or "Buffered Cursor"
		)  # Fail Safe
		self.advance_payment_doctypes = frappe.get_hooks(
			"advance_payment_receivable_doctypes"
		) + frappe.get_hooks("advance_payment_payable_doctypes")

	def run(self, args):
		self.filters.update(args)
		self.set_defaults()
		self.party_naming_by = frappe.db.get_single_value(args.get("naming_by")[0], args.get("naming_by")[1])
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
		self.dr_or_cr = "debit" if self.filters.account_type == "Receivable" else "credit"
		self.account_type = self.filters.account_type
		self.party_type = get_party_types_from_account_type(self.account_type)
		self.party_details = {}
		self.invoices = set()
		self.skip_total_row = 0
		self.advance_payment_doctypes = get_advance_payment_doctypes()

		if self.filters.get("group_by_party"):
			self.previous_party = ""
			self.total_row_map = {}
			self.skip_total_row = 1

		if self.filters.get("in_party_currency"):
			if self.filters.get("party") and len(self.filters.get("party")) == 1:
				self.skip_total_row = 0
			else:
				self.skip_total_row = 1

	def get_data(self):
		self.get_sales_invoices_or_customers_based_on_sales_person()

		# Get invoice details like bill_no, due_date etc for all invoices
		self.get_invoice_details()

		# fetch future payments against invoices
		self.get_future_payments()

		# Get return entries
		if not self.filters.party_type or self.filters.party_type in ["Customer", "Supplier"]:
			self.get_return_entries()

		# Get Exchange Rate Revaluations
		self.get_exchange_rate_revaluations()

		self.prepare_ple_query()
		self.data = []
		self.voucher_balance = OrderedDict()

		if self.ple_fetch_method == "Buffered Cursor":
			self.fetch_ple_in_buffered_cursor()
		elif self.ple_fetch_method == "UnBuffered Cursor":
			self.fetch_ple_in_unbuffered_cursor()
		elif self.ple_fetch_method == "Raw SQL":
			self.fetch_ple_in_sql_procedures()

		# Build delivery note map against all sales invoices
		self.build_delivery_note_map()

		self.build_data()

	def fetch_ple_in_buffered_cursor(self):
		self.ple_entries = self.ple_query.run(as_dict=True)

		for ple in self.ple_entries:
			self.init_voucher_balance(ple)  # invoiced, paid, credit_note, outstanding

		# This is unavoidable. Initialization and allocation cannot happen in same loop
		for ple in self.ple_entries:
			self.update_voucher_balance(ple)

		delattr(self, "ple_entries")

	def fetch_ple_in_unbuffered_cursor(self):
		self.ple_entries = []
		with frappe.db.unbuffered_cursor():
			for ple in self.ple_query.run(as_dict=True, as_iterator=True):
				self.init_voucher_balance(ple)  # invoiced, paid, credit_note, outstanding
				self.ple_entries.append(ple)

		# This is unavoidable. Initialization and allocation cannot happen in same loop
		for ple in self.ple_entries:
			self.update_voucher_balance(ple)
		delattr(self, "ple_entries")

	def build_voucher_dict(self, ple):
		return frappe._dict(
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

	def init_voucher_balance(self, ple):
		if self.filters.get("ignore_accounts"):
			key = (ple.voucher_type, ple.voucher_no, ple.party)
		else:
			key = (ple.account, ple.voucher_type, ple.voucher_no, ple.party)

		if key not in self.voucher_balance:
			self.voucher_balance[key] = self.build_voucher_dict(ple)

		if (ple.voucher_type == ple.against_voucher_type and ple.voucher_no == ple.against_voucher_no) or (
			ple.voucher_type in ("Payment Entry", "Journal Entry")
			and ple.against_voucher_type in self.advance_payment_doctypes
		):
			self.voucher_balance[key].cost_center = ple.cost_center

		self.get_invoices(ple)

		if self.filters.get("group_by_party"):
			self.init_subtotal_row(ple.party)

		if self.filters.get("group_by_party") and not self.filters.get("in_party_currency"):
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

		if self.filters.get("ignore_accounts"):
			key = (ple.against_voucher_type, ple.against_voucher_no, ple.party)
		else:
			key = (ple.account, ple.against_voucher_type, ple.against_voucher_no, ple.party)

		# If payment is made against credit note
		# and credit note is made against a Sales Invoice
		# then consider the payment against original sales invoice.
		if ple.against_voucher_type in ("Sales Invoice", "Purchase Invoice"):
			if ple.against_voucher_no in self.return_entries:
				return_against = self.return_entries.get(ple.against_voucher_no)
				if return_against:
					if self.filters.get("ignore_accounts"):
						key = (ple.against_voucher_type, return_against, ple.party)
					else:
						key = (ple.account, ple.against_voucher_type, return_against, ple.party)

		row = self.voucher_balance.get(key)

		# Build and use a separate row for Employee Advances.
		# This allows Payments or Journals made against Emp Advance to be processed.
		if (
			not row
			and ple.against_voucher_type == "Employee Advance"
			and self.filters.handle_employee_advances
		):
			_d = self.build_voucher_dict(ple)
			_d.voucher_type = ple.against_voucher_type
			_d.voucher_no = ple.against_voucher_no
			row = self.voucher_balance[key] = _d

		if not row:
			# no invoice, this is an invoice / stand-alone payment / credit note
			if self.filters.get("ignore_accounts"):
				row = self.voucher_balance.get((ple.voucher_type, ple.voucher_no, ple.party))
			else:
				row = self.voucher_balance.get((ple.account, ple.voucher_type, ple.voucher_no, ple.party))

		row.party_type = ple.party_type
		return row

	def update_voucher_balance(self, ple):
		# get the row where this balance needs to be updated
		# if its a payment, it will return the linked invoice or will be considered as advance
		row = self.get_voucher_balance(ple)
		if not row:
			return

		if self.filters.get("in_party_currency") or self.filters.get("party_account"):
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
				if row.voucher_no == ple.voucher_no == ple.against_voucher_no:
					row.paid -= amount
					row.paid_in_account_currency -= amount_in_account_currency
				else:
					row.credit_note -= amount
					row.credit_note_in_account_currency -= amount_in_account_currency
			else:
				row.paid -= amount
				row.paid_in_account_currency -= amount_in_account_currency

	def fetch_ple_in_sql_procedures(self):
		self.proc = InitSQLProceduresForAR()

		build_balance = f"""
		begin not atomic
		declare done boolean default false;
		declare rec1 row type of `{self.proc._row_def_table_name}`;
		declare ple cursor for {self.ple_query.get_sql()};
		declare continue handler for not found set done = true;

		open ple;
		fetch ple into rec1;
		while not done do
			call {self.proc.init_procedure_name}(rec1);
			fetch ple into rec1;
		end while;
		close ple;

		set done = false;
		open ple;
		fetch ple into rec1;
		while not done do
			call {self.proc.allocate_procedure_name}(rec1);
			fetch ple into rec1;
		end while;
		close ple;
		end;
		"""
		frappe.db.sql(build_balance)

		balances = frappe.db.sql(
			f"""select
			name,
			voucher_type,
			voucher_no,
			party,
			party_account `account`,
			posting_date,
			account_currency,
			cost_center,
			sum(invoiced) `invoiced`,
			sum(paid) `paid`,
			sum(credit_note) `credit_note`,
			sum(invoiced) - sum(paid) - sum(credit_note) `outstanding`,
			sum(invoiced_in_account_currency) `invoiced_in_account_currency`,
			sum(paid_in_account_currency) `paid_in_account_currency`,
			sum(credit_note_in_account_currency) `credit_note_in_account_currency`,
			sum(invoiced_in_account_currency) - sum(paid_in_account_currency) - sum(credit_note_in_account_currency) `outstanding_in_account_currency`
			from `{self.proc._voucher_balance_name}` group by name order by posting_date;""",
			as_dict=True,
		)
		for x in balances:
			if self.filters.get("ignore_accounts"):
				key = (x.voucher_type, x.voucher_no, x.party)
			else:
				key = (x.account, x.voucher_type, x.voucher_no, x.party)

			_d = self.build_voucher_dict(x)
			for field in [
				"invoiced",
				"paid",
				"credit_note",
				"outstanding",
				"invoiced_in_account_currency",
				"paid_in_account_currency",
				"credit_note_in_account_currency",
				"outstanding_in_account_currency",
				"cost_center",
			]:
				_d[field] = x.get(field)

			self.voucher_balance[key] = _d

	def update_sub_total_row(self, row, party):
		total_row = self.total_row_map.get(party)

		if total_row:
			for field in self.get_currency_fields():
				total_row[field] += row.get(field, 0.0)
			total_row["currency"] = row.get("currency", "")

	def append_subtotal_row(self, party):
		sub_total_row = self.total_row_map.get(party)

		if sub_total_row:
			self.data.append(sub_total_row)
			self.data.append({})
			self.update_sub_total_row(sub_total_row, "Total")

	def build_data(self):
		# set outstanding for all the accumulated balances
		# as we can use this to filter out invoices without outstanding
		for _key, row in self.voucher_balance.items():
			row.outstanding = flt(row.invoiced - row.paid - row.credit_note, self.currency_precision)
			row.outstanding_in_account_currency = flt(
				row.invoiced_in_account_currency
				- row.paid_in_account_currency
				- row.credit_note_in_account_currency,
				self.currency_precision,
			)

			row.invoice_grand_total = row.invoiced

			must_consider = False
			if self.filters.get("for_revaluation_journals"):
				if (abs(row.outstanding) >= 1.0 / 10**self.currency_precision) or (
					abs(row.outstanding_in_account_currency) >= 1.0 / 10**self.currency_precision
				):
					must_consider = True
			else:
				if (abs(row.outstanding) >= 1.0 / 10**self.currency_precision) and (
					(abs(row.outstanding_in_account_currency) >= 1.0 / 10**self.currency_precision)
					or (row.voucher_no in self.err_journals)
				):
					must_consider = True

			if must_consider:
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
				self.data.append(self.total_row_map.get("Total", {}))

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
			# nosemgrep
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

			# nosemgrep
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
		if self.account_type == "Receivable":
			# nosemgrep
			si_list = frappe.get_list(
				"Sales Invoice",
				filters={
					"posting_date": ("<=", self.filters.report_date),
					"company": self.filters.company,
					"docstatus": 1,
				},
				fields=["name", "due_date", "po_no"],
			)
			for d in si_list:
				self.invoice_details.setdefault(d.name, d)

			# Get Sales Team
			if self.filters.show_sales_person:
				# nosemgrep
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

		if self.account_type == "Payable":
			# nosemgrep
			invoices = frappe.get_list(
				"Purchase Invoice",
				filters={
					"posting_date": ("<=", self.filters.report_date),
					"company": self.filters.company,
					"docstatus": 1,
				},
				fields=["name", "due_date", "bill_no", "bill_date"],
			)

			for pi in invoices:
				self.invoice_details.setdefault(pi.name, pi)

		# Invoices booked via Journal Entries
		# nosemgrep
		journal_entries = frappe.get_list(
			"Journal Entry",
			filters={
				"posting_date": ("<=", self.filters.report_date),
				"company": self.filters.company,
				"docstatus": 1,
			},
			fields=["name", "due_date", "bill_no", "bill_date"],
		)

		for je in journal_entries:
			if je.bill_no:
				self.invoice_details.setdefault(je.name, je)

	def set_party_details(self, row):
		if not row.party:
			return
		# customer / supplier name
		party_details = self.get_party_details(row.party) or {}
		row.update(party_details)

		if self.filters.get("in_party_currency") or self.filters.get("party_account"):
			row.currency = row.account_currency
		else:
			row.currency = self.company_currency

	def allocate_outstanding_based_on_payment_terms(self, row):
		self.get_payment_terms(row)
		for term in row.payment_terms:
			# update "paid" and "outstanding" for this term
			if not term.paid:
				self.allocate_closing_to_term(row, term, "paid")

			# update "credit_note" and "outstanding" for this term
			if term.outstanding:
				self.allocate_closing_to_term(row, term, "credit_note")

		row.payment_terms = sorted(row.payment_terms, key=lambda x: x["due_date"])

	def get_payment_terms(self, row):
		# build payment_terms for row
		# nosemgrep
		payment_terms_details = frappe.db.sql(
			f"""
			select
				si.name, si.party_account_currency, si.currency, si.conversion_rate,
				si.total_advance, ps.due_date, ps.payment_term, ps.payment_amount, ps.base_payment_amount,
				ps.description, ps.paid_amount, ps.base_paid_amount, ps.discounted_amount
			from `tab{row.voucher_type}` si, `tabPayment Schedule` ps
			where
				si.name = ps.parent and ps.parenttype = '{row.voucher_type}' and
				si.name = %s and
				si.is_return = 0
			order by ps.paid_amount desc, due_date
		""",
			row.voucher_no,
			as_dict=1,
		)

		original_row = frappe._dict(row)
		row.payment_terms = []

		# Cr Note's don't have Payment Terms
		if not payment_terms_details:
			return

		# Advance allocated during invoicing is not considered in payment terms
		# Deduct that from paid amount pre allocation
		row.paid -= flt(payment_terms_details[0].total_advance)

		company_currency = frappe.get_value("Company", self.filters.get("company"), "default_currency")

		# If single payment terms, no need to split the row
		if len(payment_terms_details) == 1 and payment_terms_details[0].payment_term:
			self.append_payment_term(row, payment_terms_details[0], original_row, company_currency)
			return

		for d in payment_terms_details:
			term = frappe._dict(original_row)
			self.append_payment_term(row, d, term, company_currency)

	def append_payment_term(self, row, d, term, company_currency):
		invoiced = d.base_payment_amount
		paid_amount = d.base_paid_amount

		in_party_currency = self.filters.get("in_party_currency")
		# company, billing, and party account currencies are the same
		if company_currency == d.currency and company_currency == d.party_account_currency:
			in_party_currency = False

		# When filtered by party currency and the billing currency not matches the party account currency
		if in_party_currency and d.currency != d.party_account_currency:
			in_party_currency = False

		if in_party_currency:
			invoiced = d.payment_amount
			paid_amount = d.paid_amount

		row.payment_terms.append(
			term.update(
				{
					"due_date": d.due_date,
					"invoiced": invoiced,
					"invoice_grand_total": row.invoiced,
					"payment_term": d.description or d.payment_term,
					"paid": paid_amount + d.discounted_amount,
					"credit_note": 0.0,
					"outstanding": invoiced - paid_amount - d.discounted_amount,
				}
			)
		)

		if paid_amount:
			row["paid"] -= paid_amount + d.discounted_amount

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
		pe = frappe.qb.DocType("Payment Entry")
		pe_ref = frappe.qb.DocType("Payment Entry Reference")
		ifelse = query_builder.CustomFunction("IF", ["condition", "then", "else"])

		return (
			frappe.qb.from_(pe)
			.inner_join(pe_ref)
			.on(pe_ref.parent == pe.name)
			.select(
				(pe_ref.reference_name).as_("invoice_no"),
				pe.party,
				pe.party_type,
				(pe.posting_date).as_("future_date"),
				(pe_ref.allocated_amount).as_("future_amount"),
				(pe.reference_no).as_("future_ref"),
				ifelse(
					pe.payment_type == "Receive",
					pe.source_exchange_rate * pe_ref.allocated_amount,
					pe.target_exchange_rate * pe_ref.allocated_amount,
				).as_("future_amount_in_base_currency"),
			)
			.where(
				(pe.docstatus < 2)
				& (pe.posting_date > self.filters.report_date)
				& (pe.party_type.isin(self.party_type))
			)
		).run(as_dict=True)

	def get_future_payments_from_journal_entry(self):
		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")
		query = (
			frappe.qb.from_(je)
			.inner_join(jea)
			.on(jea.parent == je.name)
			.select(
				jea.reference_name.as_("invoice_no"),
				jea.party,
				jea.party_type,
				je.posting_date.as_("future_date"),
				je.cheque_no.as_("future_ref"),
			)
			.where(
				(je.docstatus < 2)
				& (je.posting_date > self.filters.report_date)
				& (jea.party_type.isin(self.party_type))
				& (jea.reference_name.isnotnull())
				& (jea.reference_name != "")
			)
		)

		if self.filters.get("party"):
			if self.account_type == "Payable":
				query = query.select(
					Sum(jea.debit_in_account_currency - jea.credit_in_account_currency).as_("future_amount")
				)
				query = query.select(Sum(jea.debit - jea.credit).as_("future_amount_in_base_currency"))
			else:
				query = query.select(
					Sum(jea.credit_in_account_currency - jea.debit_in_account_currency).as_("future_amount")
				)
				query = query.select(Sum(jea.credit - jea.debit).as_("future_amount_in_base_currency"))
		else:
			query = query.select(
				Sum(jea.debit if self.account_type == "Payable" else jea.credit).as_(
					"future_amount_in_base_currency"
				)
			)
			query = query.select(
				Sum(
					jea.debit_in_account_currency
					if self.account_type == "Payable"
					else jea.credit_in_account_currency
				).as_("future_amount")
			)

		query = query.having(qb.Field("future_amount") > 0)
		return query.run(as_dict=True)

	def allocate_future_payments(self, row):
		# future payments are captured in additional columns
		# this method allocates pending future payments against a voucher to
		# the current row (which could be generated from payment terms)
		if not self.filters.show_future_payments:
			return

		row.remaining_balance = row.outstanding
		row.future_amount = 0.0
		for future in self.future_payments.get((row.voucher_no, row.party), []):
			if self.filters.in_party_currency:
				future_amount_field = "future_amount"
			else:
				future_amount_field = "future_amount_in_base_currency"

			if row.remaining_balance != 0 and future.get(future_amount_field):
				if future.get(future_amount_field) > row.outstanding:
					row.future_amount = row.outstanding
					future[future_amount_field] = future.get(future_amount_field) - row.outstanding
					row.remaining_balance = 0
				else:
					row.future_amount += future.get(future_amount_field)
					future[future_amount_field] = 0
					row.remaining_balance = row.outstanding - row.future_amount

				row.setdefault("future_ref", []).append(
					cstr(future.future_ref) + "/" + cstr(future.future_date)
				)

		if row.future_ref:
			row.future_ref = ", ".join(row.future_ref)

	def get_return_entries(self):
		doctype = "Sales Invoice" if self.account_type == "Receivable" else "Purchase Invoice"
		filters = {
			"posting_date": ("<=", self.filters.report_date),
			"is_return": 1,
			"docstatus": 1,
			"company": self.filters.company,
			"update_outstanding_for_self": 0,
		}

		or_filters = {}
		if party_type := self.filters.party_type:
			party_field = scrub(party_type)
			if parties := self.filters.get("party"):
				or_filters.update({party_field: ["in", parties]})

		self.return_entries = frappe._dict(
			frappe.get_all(
				doctype, filters=filters, or_filters=or_filters, fields=["name", "return_against"], as_list=1
			)
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
		if getdate(entry_date) > getdate(self.age_as_on):
			[setattr(row, f"range{i}", 0.0) for i in self.range_numbers]

		row.total_due = sum(row[f"range{i}"] for i in self.range_numbers)

	def get_ageing_data(self, entry_date, row):
		# [0-30, 30-60, 60-90, 90-120, 120-above]
		[setattr(row, f"range{i}", 0.0) for i in self.range_numbers]

		if not (self.age_as_on and entry_date):
			return

		row.age = (getdate(self.age_as_on) - getdate(entry_date)).days or 0

		index = next(
			(i for i, days in enumerate(self.ranges) if cint(row.age) <= cint(days)), len(self.ranges)
		)
		row["range" + str(index + 1)] = row.outstanding

	def prepare_ple_query(self):
		# get all the GL entries filtered by the given filters

		self.prepare_conditions()

		if self.filters.show_future_payments:
			self.qb_selection_filter.append(
				self.ple.posting_date.lte(self.filters.report_date)
				| (
					(self.ple.voucher_no == self.ple.against_voucher_no)
					& (Date(self.ple.creation).lte(self.filters.report_date))
				)
			)
		else:
			self.qb_selection_filter.append(self.ple.posting_date.lte(self.filters.report_date))

		ple = qb.DocType("Payment Ledger Entry")
		query = (
			qb.from_(ple)
			.select(
				ple.name,
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
			)
			.where(ple.delinked == 0)
			.where(Criterion.all(self.qb_selection_filter))
			.where(Criterion.any(self.or_filters))
		)

		if self.filters.get("show_remarks"):
			if remarks_length := frappe.get_single_value(
				"Accounts Settings", "receivable_payable_remarks_length"
			):
				query = query.select(Substring(ple.remarks, 1, remarks_length).as_("remarks"))
			else:
				query = query.select(ple.remarks)

		if match_conditions := build_qb_match_conditions("Payment Ledger Entry"):
			query = query.where(Criterion.all(match_conditions))

		if self.filters.get("group_by_party"):
			query = query.orderby(self.ple.party, self.ple.posting_date)
		else:
			query = query.orderby(self.ple.posting_date, self.ple.party)

		self.ple_query = query

	def get_sales_invoices_or_customers_based_on_sales_person(self):
		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.get("sales_person"), ["lft", "rgt"])

			# nosemgrep
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
		self.or_filters = []

		for _party_type in self.party_type:
			self.add_common_filters()

			if self.account_type == "Receivable":
				self.add_customer_filters()
				self.exclude_employee_transaction()

			elif self.account_type == "Payable":
				self.add_supplier_filters()

		if self.filters.cost_center:
			self.get_cost_center_conditions()

		self.add_accounting_dimensions_filters()

	def get_cost_center_conditions(self):
		cost_center_list = get_cost_centers_with_children(self.filters.cost_center)
		self.qb_selection_filter.append(self.ple.cost_center.isin(cost_center_list))

	def add_common_filters(self):
		if self.filters.company:
			self.qb_selection_filter.append(self.ple.company == self.filters.company)

		if self.filters.finance_book:
			self.qb_selection_filter.append(self.ple.finance_book == self.filters.finance_book)

		if self.filters.get("party_type"):
			self.qb_selection_filter.append(self.filters.party_type == self.ple.party_type)

		if self.filters.get("party"):
			self.qb_selection_filter.append(self.ple.party.isin(self.filters.party))

		if self.filters.party_account:
			self.qb_selection_filter.append(self.ple.account == self.filters.party_account)
		else:
			# get GL with "receivable" or "payable" account_type
			accounts = [
				d.name
				for d in frappe.get_all(
					"Account", filters={"account_type": self.account_type, "company": self.filters.company}
				)
			]

			if accounts:
				self.qb_selection_filter.append(self.ple.account.isin(accounts))

	def add_customer_filters(
		self,
	):
		self.customer = qb.DocType("Customer")

		if self.filters.get("customer_group"):
			groups = get_customer_group_with_children(self.filters.customer_group)
			customers = (
				qb.from_(self.customer)
				.select(self.customer.name)
				.where(self.customer["customer_group"].isin(groups))
			)
			self.qb_selection_filter.append(self.ple.party.isin(customers))

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

	def exclude_employee_transaction(self):
		self.qb_selection_filter.append(self.ple.party_type != "Employee")

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
		if party not in self.party_details:
			if self.account_type == "Receivable":
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
		self.add_column(_("Posting Date"), fieldname="posting_date", fieldtype="Date")
		self.add_column(
			label=_("Party Type"),
			fieldname="party_type",
			fieldtype="Data",
			width=100,
		)
		self.add_column(
			label=_("Party"),
			fieldname="party",
			fieldtype="Dynamic Link",
			options="party_type",
			width=180,
		)
		if self.account_type == "Receivable":
			label = _("Receivable Account")
		elif self.account_type == "Payable":
			label = _("Payable Account")
		else:
			label = _("Party Account")

		self.add_column(
			label=label,
			fieldname="party_account",
			fieldtype="Link",
			options="Account",
			width=180,
		)

		if self.party_naming_by == "Naming Series":
			if self.account_type == "Payable":
				label = _("Supplier Name")
				fieldname = "supplier_name"
			else:
				label = _("Customer Name")
				fieldname = "customer_name"
			self.add_column(
				label=label,
				fieldname=fieldname,
				fieldtype="Data",
			)

		if self.account_type == "Receivable":
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

		self.add_column(label=_("Due Date"), fieldname="due_date", fieldtype="Date")

		if self.account_type == "Payable":
			self.add_column(label=_("Bill No"), fieldname="bill_no", fieldtype="Data")
			self.add_column(label=_("Bill Date"), fieldname="bill_date", fieldtype="Date")

		if self.filters.based_on_payment_terms:
			self.add_column(label=_("Payment Term"), fieldname="payment_term", fieldtype="Data")
			self.add_column(label=_("Invoice Grand Total"), fieldname="invoice_grand_total")

		self.add_column(_("Invoiced Amount"), fieldname="invoiced")
		self.add_column(_("Paid Amount"), fieldname="paid")
		if self.account_type == "Receivable":
			self.add_column(_("Credit Note"), fieldname="credit_note")
		else:
			# note: fieldname is still `credit_note`
			self.add_column(_("Debit Note"), fieldname="credit_note")
		self.add_column(_("Outstanding Amount"), fieldname="outstanding")

		self.add_column(label=_("Age (Days)"), fieldname="age", fieldtype="Int", width=80)
		self.setup_ageing_columns()

		self.add_column(
			label=_("Currency"), fieldname="currency", fieldtype="Link", options="Currency", width=80
		)

		if self.filters.show_future_payments:
			self.add_column(label=_("Future Payment Ref"), fieldname="future_ref", fieldtype="Data")
			self.add_column(label=_("Future Payment Amount"), fieldname="future_amount")
			self.add_column(label=_("Remaining Balance"), fieldname="remaining_balance")

		if self.filters.account_type == "Receivable":
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

		if self.filters.account_type == "Payable":
			self.add_column(
				label=_("Supplier Group"),
				fieldname="supplier_group",
				fieldtype="Link",
				options="Supplier Group",
			)

		if self.filters.show_remarks:
			self.add_column(label=_("Remarks"), fieldname="remarks", fieldtype="Text", width=200)

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
		ranges = [*self.ranges, _("Above")]

		prev_range_value = 0
		for idx, curr_range_value in enumerate(ranges):
			label = f"{prev_range_value}-{curr_range_value}"
			self.add_column(label=label, fieldname="range" + str(idx + 1))

			self.ageing_column_labels.append(label)

			if curr_range_value.isdigit():
				prev_range_value = cint(curr_range_value) + 1

	def get_chart_data(self):
		precision = cint(frappe.db.get_default("float_precision")) or 2
		rows = []
		for row in self.data:
			row = frappe._dict(row)
			if not cint(row.bold):
				values = [flt(row.get(f"range{i}", None), precision) for i in self.range_numbers]
				rows.append({"values": values})

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
				& (
					(je.voucher_type == "Exchange Rate Revaluation")
					| (je.voucher_type == "Exchange Gain Or Loss")
				)
			)
			.run()
		)
		self.err_journals = [x[0] for x in results] if results else []


def get_customer_group_with_children(customer_groups):
	if not isinstance(customer_groups, list):
		customer_groups = [d.strip() for d in customer_groups.strip().split(",") if d]

	all_customer_groups = []
	for d in customer_groups:
		if frappe.db.exists("Customer Group", d):
			lft, rgt = frappe.db.get_value("Customer Group", d, ["lft", "rgt"])
			children = frappe.get_all("Customer Group", filters={"lft": [">=", lft], "rgt": ["<=", rgt]})
			all_customer_groups += [c.name for c in children]
		else:
			frappe.throw(_("Customer Group: {0} does not exist").format(d))

	return list(set(all_customer_groups))


class InitSQLProceduresForAR:
	"""
	Initialize SQL Procedures, Functions and Temporary tables to build Receivable / Payable report
	"""

	_varchar_type = get_definition("Data")
	_currency_type = get_definition("Currency")
	# Temporary Tables
	_voucher_balance_name = "_ar_voucher_balance"
	_voucher_balance_definition = f"""
		create temporary table `{_voucher_balance_name}`(
		name {_varchar_type},
		voucher_type {_varchar_type},
		voucher_no {_varchar_type},
		party {_varchar_type},
		party_account {_varchar_type},
		posting_date date,
		account_currency {_varchar_type},
		cost_center {_varchar_type},
		invoiced {_currency_type},
		paid {_currency_type},
		credit_note {_currency_type},
		invoiced_in_account_currency {_currency_type},
		paid_in_account_currency {_currency_type},
		credit_note_in_account_currency {_currency_type}) engine=memory;
	"""

	_row_def_table_name = "_ar_ple_row"
	_row_def_table_definition = f"""
		create temporary table `{_row_def_table_name}`(
		name {_varchar_type},
		account {_varchar_type},
		voucher_type {_varchar_type},
		voucher_no {_varchar_type},
		against_voucher_type {_varchar_type},
		against_voucher_no {_varchar_type},
		party_type {_varchar_type},
		cost_center {_varchar_type},
		party {_varchar_type},
		posting_date date,
		due_date date,
		account_currency {_varchar_type},
		amount {_currency_type},
		amount_in_account_currency {_currency_type}) engine=memory;
	"""

	# Function
	genkey_function_name = "ar_genkey"
	genkey_function_sql = f"""
	create function `{genkey_function_name}`(rec row type of `{_row_def_table_name}`, allocate bool) returns char(40)
	begin
		if allocate then
			return sha1(concat_ws(',', rec.account, rec.against_voucher_type, rec.against_voucher_no, rec.party));
		else
			return sha1(concat_ws(',', rec.account, rec.voucher_type, rec.voucher_no, rec.party));
		end if;
	end
	"""

	# Procedures
	init_procedure_name = "ar_init_tmp_table"
	init_procedure_sql = f"""
	create procedure ar_init_tmp_table(in ple row type of `{_row_def_table_name}`)
	begin
		if not exists (select name from `{_voucher_balance_name}` where name = `{genkey_function_name}`(ple, false))
		then
			insert into `{_voucher_balance_name}` values (`{genkey_function_name}`(ple, false), ple.voucher_type, ple.voucher_no, ple.party, ple.account, ple.posting_date, ple.account_currency, ple.cost_center, 0, 0, 0, 0, 0, 0);
		end if;
	end;
	"""

	allocate_procedure_name = "ar_allocate_to_tmp_table"
	allocate_procedure_sql = f"""
	create procedure ar_allocate_to_tmp_table(in ple row type of `{_row_def_table_name}`)
	begin
		declare invoiced {_currency_type} default 0;
		declare invoiced_in_account_currency {_currency_type} default 0;
		declare paid {_currency_type} default 0;
		declare paid_in_account_currency {_currency_type} default 0;
		declare credit_note {_currency_type} default 0;
		declare credit_note_in_account_currency {_currency_type} default 0;


		if ple.amount > 0 then
			if (ple.voucher_type in ("Journal Entry", "Payment Entry") and (ple.voucher_no != ple.against_voucher_no)) then
				set paid = -1 * ple.amount;
				set paid_in_account_currency = -1 * ple.amount_in_account_currency;
			else
				set invoiced = ple.amount;
				set invoiced_in_account_currency = ple.amount_in_account_currency;
			end if;
		else

		if ple.voucher_type in ("Sales Invoice", "Purchase Invoice") then
			if (ple.voucher_no = ple.against_voucher_no) then
				set paid = -1 * ple.amount;
				set paid_in_account_currency = -1 * ple.amount_in_account_currency;
			else
				set credit_note = -1 * ple.amount;
				set credit_note_in_account_currency = -1 * ple.amount_in_account_currency;
		end if;
		else
			set paid = -1 * ple.amount;
			set paid_in_account_currency = -1 * ple.amount_in_account_currency;
		end if;

		end if;

		insert into `{_voucher_balance_name}` values (`{genkey_function_name}`(ple, true), ple.against_voucher_type, ple.against_voucher_no, ple.party, ple.account, ple.posting_date, ple.account_currency,'', invoiced, paid, 0, invoiced_in_account_currency, paid_in_account_currency, 0);
	end;
	"""

	def __init__(self):
		existing_procedures = frappe.db.get_routines()

		if self.genkey_function_name not in existing_procedures:
			frappe.db.sql(self.genkey_function_sql)

		if self.init_procedure_name not in existing_procedures:
			frappe.db.sql(self.init_procedure_sql)

		if self.allocate_procedure_name not in existing_procedures:
			frappe.db.sql(self.allocate_procedure_sql)

		frappe.db.sql(f"drop table if exists `{self._voucher_balance_name}`")
		frappe.db.sql(self._voucher_balance_definition)

		frappe.db.sql(f"drop table if exists `{self._row_def_table_name}`")
		frappe.db.sql(self._row_def_table_definition)
