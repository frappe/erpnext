# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, qb, scrub
<<<<<<< HEAD
from frappe.query_builder import Criterion, Tuple
=======
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)
from frappe.query_builder.functions import IfNull
from frappe.utils import getdate, nowdate
from frappe.utils.nestedset import get_descendants_of
from pypika.terms import LiteralValue

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)

TREE_DOCTYPES = frozenset(
	["Customer Group", "Territory", "Supplier Group", "Sales Partner", "Sales Person", "Cost Center"]
)

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children


class PartyLedgerSummaryReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

<<<<<<< HEAD
<<<<<<< HEAD
=======
		if self.filters.get("cost_center"):
			self.filters.cost_center = frappe.parse_json(self.filters.get("cost_center"))

		if self.filters.get("project"):
			self.filters.project = frappe.parse_json(self.filters.get("project"))

=======
>>>>>>> 9610a33d23 (fix: remove irrelavent conditions)
		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value("Global Defaults", "default_company")

>>>>>>> 901bcd5c43 (feat: add accounting dimensions in ledger summary reports)
	def run(self, args):
		self.filters.party_type = args.get("party_type")

		self.validate_filters()
		self.get_party_details()

		if not self.parties:
			return [], []

		self.get_gl_entries()
		self.get_return_invoices()
		self.get_party_adjustment_amounts()

		self.party_naming_by = frappe.db.get_single_value(args.get("naming_by")[0], args.get("naming_by")[1])
		columns = self.get_columns()
		data = self.get_data()

		return columns, data

	def validate_filters(self):
		if not self.filters.get("company"):
			frappe.throw(_("{0} is mandatory").format(_("Company")))

		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.update_hierarchical_filters()

	def update_hierarchical_filters(self):
		for doctype in TREE_DOCTYPES:
			key = scrub(doctype)
			if self.filters.get(key):
				self.filters[key] = get_children(doctype, self.filters[key])

	def get_party_details(self):
		"""
		Additional Columns for 'User Permission' based access control
		"""
		self.parties = []
		self.party_details = frappe._dict()
		party_type = self.filters.party_type

		doctype = qb.DocType(party_type)

		party_details_fields = [
			doctype.name.as_("party"),
			f"{scrub(party_type)}_name",
			f"{scrub(party_type)}_group",
		]

		if party_type == "Customer":
			party_details_fields.append(doctype.territory)

		conditions = self.get_party_conditions(doctype)
		query = qb.from_(doctype).select(*party_details_fields).where(Criterion.all(conditions))

		from frappe.desk.reportview import build_match_conditions

		match_conditions = build_match_conditions(party_type)

		if match_conditions:
			query = query.where(LiteralValue(match_conditions))

		party_details = query.run(as_dict=True)

		for row in party_details:
			self.parties.append(row.party)
			self.party_details[row.party] = row

	def get_party_conditions(self, doctype):
		conditions = []
		group_field = "customer_group" if self.filters.party_type == "Customer" else "supplier_group"

		if self.filters.party:
			conditions.append(doctype.name == self.filters.party)

		if self.filters.territory:
			conditions.append(doctype.territory.isin(self.filters.territory))

		if self.filters.get(group_field):
			conditions.append(doctype[group_field].isin(self.filters.get(group_field)))

		if self.filters.payment_terms_template:
			conditions.append(doctype.payment_terms == self.filters.payment_terms_template)

		if self.filters.sales_partner:
			conditions.append(doctype.default_sales_partner.isin(self.filters.sales_partner))

		if self.filters.sales_person:
			sales_team = qb.DocType("Sales Team")
			sales_invoice = qb.DocType("Sales Invoice")

			customers = (
				qb.from_(sales_team)
				.select(sales_team.parent)
				.where(sales_team.sales_person.isin(self.filters.sales_person))
				.where(sales_team.parenttype == "Customer")
			) + (
				qb.from_(sales_team)
				.join(sales_invoice)
				.on(sales_team.parent == sales_invoice.name)
				.select(sales_invoice.customer)
				.where(sales_team.sales_person.isin(self.filters.sales_person))
				.where(sales_team.parenttype == "Sales Invoice")
			)

			conditions.append(doctype.name.isin(customers))

		return conditions

	def get_columns(self):
		columns = [
			{
				"label": _(self.filters.party_type),
				"fieldtype": "Link",
				"fieldname": "party",
				"options": self.filters.party_type,
				"width": 200,
			}
		]

		if self.party_naming_by == "Naming Series":
			columns.append(
				{
					"label": _(self.filters.party_type + " Name"),
					"fieldtype": "Data",
					"fieldname": "party_name",
					"width": 150,
				}
			)

		credit_or_debit_note = "Credit Note" if self.filters.party_type == "Customer" else "Debit Note"

		if self.filters.party_type == "Customer":
			columns += [
				{
					"label": _("Customer Group"),
					"fieldname": "customer_group",
					"fieldtype": "Link",
					"options": "Customer Group",
				},
				{
					"label": _("Territory"),
					"fieldname": "territory",
					"fieldtype": "Link",
					"options": "Territory",
				},
			]
		else:
			columns += [
				{
					"label": _("Supplier Group"),
					"fieldname": "supplier_group",
					"fieldtype": "Link",
					"options": "Supplier Group",
				}
			]

		columns += [
			{
				"label": _("Opening Balance"),
				"fieldname": "opening_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Invoiced Amount"),
				"fieldname": "invoiced_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Paid Amount"),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _(credit_or_debit_note),
				"fieldname": "return_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
		]

		for account in self.party_adjustment_accounts:
			columns.append(
				{
					"label": account,
					"fieldname": "adj_" + scrub(account),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120,
					"is_adjustment": 1,
				}
			)

		columns += [
			{
				"label": _("Closing Balance"),
				"fieldname": "closing_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 50,
			},
		]

		return columns

	def get_data(self):
		company_currency = frappe.get_cached_value("Company", self.filters.get("company"), "default_currency")
		invoice_dr_or_cr = "debit" if self.filters.party_type == "Customer" else "credit"
		reverse_dr_or_cr = "credit" if self.filters.party_type == "Customer" else "debit"

		self.party_data = frappe._dict({})
		for gle in self.gl_entries:
			party_details = self.party_details.get(gle.party)
			party_name = party_details.get(f"{scrub(self.filters.party_type)}_name", "")
			self.party_data.setdefault(
				gle.party,
				frappe._dict(
					{
						**party_details,
						"party_name": party_name,
						"opening_balance": 0,
						"invoiced_amount": 0,
						"paid_amount": 0,
						"return_amount": 0,
						"closing_balance": 0,
						"currency": company_currency,
					}
				),
			)

			amount = gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
			self.party_data[gle.party].closing_balance += amount

			if gle.posting_date < self.filters.from_date or gle.is_opening == "Yes":
				self.party_data[gle.party].opening_balance += amount
			else:
				# Cache the party data reference to avoid repeated dictionary lookups
				party_data = self.party_data[gle.party]

				# Check if this is a direct return invoice (most specific condition first)
				if gle.voucher_no in self.return_invoices:
					party_data.return_amount -= amount
				# Check if this entry is against a return invoice
				elif gle.against_voucher in self.return_invoices:
					# For entries against return invoices, positive amounts are payments
					if amount > 0:
						party_data.paid_amount -= amount
					else:
						party_data.invoiced_amount += amount
				# Normal transaction logic
				else:
					if amount > 0:
						party_data.invoiced_amount += amount
					else:
						party_data.paid_amount -= amount

		out = []
		for party, row in self.party_data.items():
			if (
				row.opening_balance
				or row.invoiced_amount
				or row.paid_amount
				or row.return_amount
				or row.closing_balance  # Fixed typo from closing_amount to closing_balance
			):
				total_party_adjustment = sum(
					amount for amount in self.party_adjustment_details.get(party, {}).values()
				)
				row.paid_amount -= total_party_adjustment

				adjustments = self.party_adjustment_details.get(party, {})
				for account in self.party_adjustment_accounts:
					row["adj_" + scrub(account)] = adjustments.get(account, 0)

				out.append(row)

		return out

	def get_gl_entries(self):
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)
		gle = qb.DocType("GL Entry")
		query = (
			qb.from_(gle)
			.select(
				gle.posting_date,
				gle.party,
				gle.voucher_type,
				gle.voucher_no,
<<<<<<< HEAD
				gle.against_voucher,  # For handling returned invoices (Credit/Debit Notes)
=======
				gle.against_voucher_type,
				gle.against_voucher,
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)
				gle.debit,
				gle.credit,
				gle.is_opening,
			)
			.where(
				(gle.docstatus < 2)
				& (gle.is_cancelled == 0)
				& (gle.party_type == self.filters.party_type)
				& (IfNull(gle.party, "") != "")
				& (gle.posting_date <= self.filters.to_date)
<<<<<<< HEAD
				& (gle.party.isin(self.parties))
			)
=======
		conditions = self.prepare_conditions()
		join = join_field = ""
		if self.filters.party_type == "Customer":
			join_field = ", p.customer_name as party_name"
			join = "left join `tabCustomer` p on gle.party = p.name"
		elif self.filters.party_type == "Supplier":
			join_field = ", p.supplier_name as party_name"
			join = "left join `tabSupplier` p on gle.party = p.name"

		self.gl_entries = frappe.db.sql(
			f"""
			select
				gle.posting_date, gle.party, gle.voucher_type, gle.voucher_no, gle.against_voucher_type,
				gle.against_voucher, gle.debit, gle.credit, gle.is_opening {join_field}
			from `tabGL Entry` gle
			{join}
			where
				gle.docstatus < 2 and gle.is_cancelled = 0 and gle.party_type=%(party_type)s and ifnull(gle.party, '') != ''
				and gle.posting_date <= %(to_date)s {conditions}
			order by gle.posting_date
		""",
			self.filters,
			as_dict=True,
>>>>>>> 901bcd5c43 (feat: add accounting dimensions in ledger summary reports)
		)

		query = self.prepare_conditions(query)

=======
			)
			.orderby(gle.posting_date)
		)

		if self.filters.party_type == "Customer":
			customer = qb.DocType("Customer")
			query = (
				query.select(customer.customer_name.as_("party_name"))
				.left_join(customer)
				.on(customer.name == gle.party)
			)
		elif self.filters.party_type == "Supplier":
			supplier = qb.DocType("Supplier")
			query = (
				query.select(supplier.supplier_name.as_("party_name"))
				.left_join(supplier)
				.on(supplier.name == gle.party)
			)

		query = self.prepare_conditions(query)
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)
		self.gl_entries = query.run(as_dict=True)

	def prepare_conditions(self, query):
		gle = qb.DocType("GL Entry")
		if self.filters.company:
			query = query.where(gle.company == self.filters.company)

		if self.filters.finance_book:
			query = query.where(IfNull(gle.finance_book, "") == self.filters.finance_book)

<<<<<<< HEAD
		if self.filters.cost_center:
			query = query.where((gle.cost_center).isin(self.filters.cost_center))

		if self.filters.project:
			query = query.where((gle.project).isin(self.filters.project))

		accounting_dimensions = get_accounting_dimensions(as_list=False)

		if accounting_dimensions:
			for dimension in accounting_dimensions:
				if self.filters.get(dimension.fieldname):
					if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
						self.filters[dimension.fieldname] = get_dimension_with_children(
							dimension.document_type, self.filters.get(dimension.fieldname)
						)
						query = query.where(
							(gle[dimension.fieldname]).isin(self.filters.get(dimension.fieldname))
						)
					else:
						query = query.where(
							(gle[dimension.fieldname]).isin(self.filters.get(dimension.fieldname))
						)

<<<<<<< HEAD
		return query
=======
				conditions.append(
					f"""party in (select name from tabCustomer
					where exists(select name from `tabTerritory` where lft >= {lft} and rgt <= {rgt}
						and name=tabCustomer.territory))"""
=======
		if self.filters.party:
			query = query.where(gle.party == self.filters.party)

		if self.filters.party_type == "Customer":
			customer = qb.DocType("Customer")
			if self.filters.customer_group:
				query = query.where(
					(gle.party).isin(
						qb.from_(customer)
						.select(customer.name)
						.where(customer.customer_group == self.filters.customer_group)
					)
				)

			if self.filters.territory:
				query = query.where(
					(gle.party).isin(
						qb.from_(customer)
						.select(customer.name)
						.where(customer.territory == self.filters.territory)
					)
				)

			if self.filters.payment_terms_template:
				query = query.where(
					(gle.party).isin(
						qb.from_(customer)
						.select(customer.name)
						.where(customer.payment_terms == self.filters.payment_terms_template)
					)
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)
				)

			if self.filters.sales_partner:
				query = query.where(
					(gle.party).isin(
						qb.from_(customer)
						.select(customer.name)
						.where(customer.default_sales_partner == self.filters.sales_partner)
					)
				)

			if self.filters.sales_person:
				sales_team = qb.DocType("Sales Team")
				query = query.where(
					(gle.party).isin(
						qb.from_(sales_team)
						.select(sales_team.parent)
						.where(sales_team.sales_person == self.filters.sales_person)
					)
				)

		if self.filters.party_type == "Supplier":
			if self.filters.supplier_group:
				supplier = qb.DocType("Supplier")
				query = query.where(
					(gle.party).isin(
						qb.from_(supplier)
						.select(supplier.name)
						.where(supplier.supplier_group == self.filters.supplier_group)
					)
				)

		if self.filters.cost_center:
			self.filters.cost_center = get_cost_centers_with_children(self.filters.cost_center)
			query = query.where((gle.cost_center).isin(self.filters.cost_center))

		if self.filters.project:
			query = query.where((gle.project).isin(self.filters.project))

		accounting_dimensions = get_accounting_dimensions(as_list=False)

		if accounting_dimensions:
			for dimension in accounting_dimensions:
				if self.filters.get(dimension.fieldname):
					if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
						self.filters[dimension.fieldname] = get_dimension_with_children(
							dimension.document_type, self.filters.get(dimension.fieldname)
						)
						query = query.where(
							(gle[dimension.fieldname]).isin(self.filters.get(dimension.fieldname))
						)
					else:
						query = query.where(
							(gle[dimension.fieldname]).isin(self.filters.get(dimension.fieldname))
						)

<<<<<<< HEAD
		return " and ".join(conditions)
>>>>>>> 901bcd5c43 (feat: add accounting dimensions in ledger summary reports)
=======
		return query
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)

	def get_return_invoices(self):
		doctype = "Sales Invoice" if self.filters.party_type == "Customer" else "Purchase Invoice"
		filters = (
			{
				"is_return": 1,
				"docstatus": 1,
				"posting_date": ["between", [self.filters.from_date, self.filters.to_date]],
				f"{scrub(self.filters.party_type)}": ["in", self.parties],
			},
		)

		self.return_invoices = frappe.get_all(doctype, filters=filters, pluck="name")

	def get_party_adjustment_amounts(self):
		account_type = "Expense Account" if self.filters.party_type == "Customer" else "Income Account"
<<<<<<< HEAD

=======
		self.income_or_expense_accounts = frappe.db.get_all(
			"Account", filters={"account_type": account_type, "company": self.filters.company}, pluck="name"
		)
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)
		invoice_dr_or_cr = "debit" if self.filters.party_type == "Customer" else "credit"
		reverse_dr_or_cr = "credit" if self.filters.party_type == "Customer" else "debit"
		round_off_account = frappe.get_cached_value("Company", self.filters.company, "round_off_account")

<<<<<<< HEAD
		current_period_vouchers = set()
		adjustment_voucher_entries = {}
=======
		if not self.income_or_expense_accounts:
			# prevent empty 'in' condition
			self.income_or_expense_accounts.append("")
		else:
			# escape '%' in account name
			# ignoring frappe.db.escape as it replaces single quotes with double quotes
			self.income_or_expense_accounts = [x.replace("%", "%%") for x in self.income_or_expense_accounts]

		gl = qb.DocType("GL Entry")
		accounts_query = self.get_base_accounts_query()
		accounts_query_voucher_no = accounts_query.select(gl.voucher_no)
		accounts_query_voucher_type = accounts_query.select(gl.voucher_type)

		subquery = self.get_base_subquery()
		subquery_voucher_no = subquery.select(gl.voucher_no)
		subquery_voucher_type = subquery.select(gl.voucher_type)

		gl_entries = (
			qb.from_(gl)
			.select(
				gl.posting_date, gl.account, gl.party, gl.voucher_type, gl.voucher_no, gl.debit, gl.credit
			)
			.where(
				(gl.docstatus < 2)
				& (gl.is_cancelled == 0)
				& (gl.voucher_no.isin(accounts_query_voucher_no))
				& (gl.voucher_type.isin(accounts_query_voucher_type))
				& (gl.voucher_no.isin(subquery_voucher_no))
				& (gl.voucher_type.isin(subquery_voucher_type))
			)
		).run(as_dict=True)
>>>>>>> 7614f166d8 (refactor: convert sql queries to qb queries)

		self.party_adjustment_details = {}
		self.party_adjustment_accounts = set()

		for gle in self.gl_entries:
			if (
				gle.is_opening != "Yes"
				and gle.posting_date >= self.filters.from_date
				and gle.posting_date <= self.filters.to_date
			):
				current_period_vouchers.add((gle.voucher_type, gle.voucher_no))
				adjustment_voucher_entries.setdefault((gle.voucher_type, gle.voucher_no), []).append(gle)

		if not current_period_vouchers:
			return

		gl = qb.DocType("GL Entry")
		query = (
			qb.from_(gl)
			.select(
				gl.posting_date, gl.account, gl.party, gl.voucher_type, gl.voucher_no, gl.debit, gl.credit
			)
			.where(
				(gl.docstatus < 2)
				& (gl.is_cancelled == 0)
				& (gl.posting_date.gte(self.filters.from_date))
				& (gl.posting_date.lte(self.filters.to_date))
				& (Tuple((gl.voucher_type, gl.voucher_no)).isin(current_period_vouchers))
				& (IfNull(gl.party, "") == "")
			)
		)
		query = self.prepare_conditions(query)
		gl_entries = query.run(as_dict=True)

		for gle in gl_entries:
			adjustment_voucher_entries[(gle.voucher_type, gle.voucher_no)].append(gle)

		for voucher_gl_entries in adjustment_voucher_entries.values():
			parties = {}
			accounts = {}
			has_irrelevant_entry = False

			for gle in voucher_gl_entries:
				if gle.account == round_off_account:
					continue
				elif gle.party:
					parties.setdefault(gle.party, 0)
					parties[gle.party] += gle.get(reverse_dr_or_cr) - gle.get(invoice_dr_or_cr)
				elif frappe.get_cached_value("Account", gle.account, "account_type") == account_type:
					accounts.setdefault(gle.account, 0)
					accounts[gle.account] += gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
				else:
					has_irrelevant_entry = True

			if parties and accounts:
				if len(parties) == 1:
					party = next(iter(parties.keys()))
					for account, amount in accounts.items():
						self.party_adjustment_accounts.add(account)
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount
				elif len(accounts) == 1 and not has_irrelevant_entry:
					account = next(iter(accounts.keys()))
					self.party_adjustment_accounts.add(account)
					for party, amount in parties.items():
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount

	def get_base_accounts_query(self):
		gl = qb.DocType("GL Entry")
		query = qb.from_(gl).where(
			(gl.account.isin(self.income_or_expense_accounts))
			& (gl.posting_date.gte(self.filters.from_date))
			& (gl.posting_date.lte(self.filters.to_date))
		)
		return query

	def get_base_subquery(self):
		gl = qb.DocType("GL Entry")
		query = qb.from_(gl).where(
			(gl.docstatus < 2)
			& (gl.party_type == self.filters.party_type)
			& (IfNull(gl.party, "") != "")
			& (gl.posting_date.between(self.filters.from_date, self.filters.to_date))
		)
		query = self.prepare_conditions(query)
		return query


def get_children(doctype, value):
	if not isinstance(value, list):
		value = [d.strip() for d in value.strip().split(",") if d]

	all_children = []

	for d in value:
		all_children += get_descendants_of(doctype, value)
		all_children.append(d)

	return list(set(all_children))


def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return PartyLedgerSummaryReport(filters).run(args)
