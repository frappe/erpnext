# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
from frappe.utils import getdate, nowdate
from six import iteritems, itervalues


class PartyLedgerSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value("Global Defaults", "default_company")

	def run(self, args):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.filters.party_type = args.get("party_type")
		self.party_naming_by = frappe.db.get_value(
			args.get("naming_by")[0], None, args.get("naming_by")[1]
		)

		self.get_gl_entries()
		self.get_additional_columns()
		self.get_return_invoices()
		self.get_party_adjustment_amounts()

		columns = self.get_columns()
		data = self.get_data()
		return columns, data

	def get_additional_columns(self):
		"""
		Additional Columns for 'User Permission' based access control
		"""
		from frappe import qb

		if self.filters.party_type == "Customer":
			self.territories = frappe._dict({})
			self.customer_group = frappe._dict({})

			customer = qb.DocType("Customer")
			result = (
				frappe.qb.from_(customer)
				.select(
					customer.name, customer.territory, customer.customer_group, customer.default_sales_partner
				)
				.where((customer.disabled == 0))
				.run(as_dict=True)
			)

			for x in result:
				self.territories[x.name] = x.territory
				self.customer_group[x.name] = x.customer_group
		else:
			self.supplier_group = frappe._dict({})
			supplier = qb.DocType("Supplier")
			result = (
				frappe.qb.from_(supplier)
				.select(supplier.name, supplier.supplier_group)
				.where((supplier.disabled == 0))
				.run(as_dict=True)
			)

			for x in result:
				self.supplier_group[x.name] = x.supplier_group

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
					"label": _(self.filters.party_type + "Name"),
					"fieldtype": "Data",
					"fieldname": "party_name",
					"width": 110,
				}
			)

		credit_or_debit_note = "Credit Note" if self.filters.party_type == "Customer" else "Debit Note"

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

		# Hidden columns for handling 'User Permissions'
		if self.filters.party_type == "Customer":
			columns += [
				{
					"label": _("Territory"),
					"fieldname": "territory",
					"fieldtype": "Link",
					"options": "Territory",
					"hidden": 1,
				},
				{
					"label": _("Customer Group"),
					"fieldname": "customer_group",
					"fieldtype": "Link",
					"options": "Customer Group",
					"hidden": 1,
				},
			]
		else:
			columns += [
				{
					"label": _("Supplier Group"),
					"fieldname": "supplier_group",
					"fieldtype": "Link",
					"options": "Supplier Group",
					"hidden": 1,
				}
			]

		return columns

	def get_data(self):
		company_currency = frappe.get_cached_value(
			"Company", self.filters.get("company"), "default_currency"
		)
		invoice_dr_or_cr = "debit" if self.filters.party_type == "Customer" else "credit"
		reverse_dr_or_cr = "credit" if self.filters.party_type == "Customer" else "debit"

		self.party_data = frappe._dict({})
		for gle in self.gl_entries:
			self.party_data.setdefault(
				gle.party,
				frappe._dict(
					{
						"party": gle.party,
						"party_name": gle.party_name,
						"opening_balance": 0,
						"invoiced_amount": 0,
						"paid_amount": 0,
						"return_amount": 0,
						"closing_balance": 0,
						"currency": company_currency,
					}
				),
			)

			if self.filters.party_type == "Customer":
				self.party_data[gle.party].update({"territory": self.territories.get(gle.party)})
				self.party_data[gle.party].update({"customer_group": self.customer_group.get(gle.party)})
			else:
				self.party_data[gle.party].update({"supplier_group": self.supplier_group.get(gle.party)})

			amount = gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
			self.party_data[gle.party].closing_balance += amount

			if gle.posting_date < self.filters.from_date or gle.is_opening == "Yes":
				self.party_data[gle.party].opening_balance += amount
			else:
				if amount > 0:
					self.party_data[gle.party].invoiced_amount += amount
				elif gle.voucher_no in self.return_invoices:
					self.party_data[gle.party].return_amount -= amount
				else:
					self.party_data[gle.party].paid_amount -= amount

		out = []
		for party, row in iteritems(self.party_data):
			if (
				row.opening_balance
				or row.invoiced_amount
				or row.paid_amount
				or row.return_amount
				or row.closing_amount
			):
				total_party_adjustment = sum(
					amount for amount in itervalues(self.party_adjustment_details.get(party, {}))
				)
				row.paid_amount -= total_party_adjustment

				adjustments = self.party_adjustment_details.get(party, {})
				for account in self.party_adjustment_accounts:
					row["adj_" + scrub(account)] = adjustments.get(account, 0)

				out.append(row)

		return out

	def get_gl_entries(self):
		conditions = self.prepare_conditions()
		join = join_field = ""
		if self.filters.party_type == "Customer":
			join_field = ", p.customer_name as party_name"
			join = "left join `tabCustomer` p on gle.party = p.name"
		elif self.filters.party_type == "Supplier":
			join_field = ", p.supplier_name as party_name"
			join = "left join `tabSupplier` p on gle.party = p.name"

		self.gl_entries = frappe.db.sql(
			"""
			select
				gle.posting_date, gle.party, gle.voucher_type, gle.voucher_no, gle.against_voucher_type,
				gle.against_voucher, gle.debit, gle.credit, gle.is_opening {join_field}
			from `tabGL Entry` gle
			{join}
			where
				gle.docstatus < 2 and gle.is_cancelled = 0 and gle.party_type=%(party_type)s and ifnull(gle.party, '') != ''
				and gle.posting_date <= %(to_date)s {conditions}
			order by gle.posting_date
		""".format(
				join=join, join_field=join_field, conditions=conditions
			),
			self.filters,
			as_dict=True,
		)

	def prepare_conditions(self):
		conditions = [""]

		if self.filters.company:
			conditions.append("gle.company=%(company)s")

		if self.filters.finance_book:
			conditions.append("ifnull(finance_book,'') in (%(finance_book)s, '')")

		if self.filters.get("party"):
			conditions.append("party=%(party)s")

		if self.filters.party_type == "Customer":
			if self.filters.get("customer_group"):
				lft, rgt = frappe.db.get_value(
					"Customer Group", self.filters.get("customer_group"), ["lft", "rgt"]
				)

				conditions.append(
					"""party in (select name from tabCustomer
					where exists(select name from `tabCustomer Group` where lft >= {0} and rgt <= {1}
						and name=tabCustomer.customer_group))""".format(
						lft, rgt
					)
				)

			if self.filters.get("territory"):
				lft, rgt = frappe.db.get_value("Territory", self.filters.get("territory"), ["lft", "rgt"])

				conditions.append(
					"""party in (select name from tabCustomer
					where exists(select name from `tabTerritory` where lft >= {0} and rgt <= {1}
						and name=tabCustomer.territory))""".format(
						lft, rgt
					)
				)

			if self.filters.get("payment_terms_template"):
				conditions.append(
					"party in (select name from tabCustomer where payment_terms=%(payment_terms_template)s)"
				)

			if self.filters.get("sales_partner"):
				conditions.append(
					"party in (select name from tabCustomer where default_sales_partner=%(sales_partner)s)"
				)

			if self.filters.get("sales_person"):
				lft, rgt = frappe.db.get_value(
					"Sales Person", self.filters.get("sales_person"), ["lft", "rgt"]
				)

				conditions.append(
					"""exists(select name from `tabSales Team` steam where
					steam.sales_person in (select name from `tabSales Person` where lft >= {0} and rgt <= {1})
					and ((steam.parent = voucher_no and steam.parenttype = voucher_type)
						or (steam.parent = against_voucher and steam.parenttype = against_voucher_type)
						or (steam.parent = party and steam.parenttype = 'Customer')))""".format(
						lft, rgt
					)
				)

		if self.filters.party_type == "Supplier":
			if self.filters.get("supplier_group"):
				conditions.append(
					"""party in (select name from tabSupplier
					where supplier_group=%(supplier_group)s)"""
				)

		return " and ".join(conditions)

	def get_return_invoices(self):
		doctype = "Sales Invoice" if self.filters.party_type == "Customer" else "Purchase Invoice"
		self.return_invoices = [
			d.name
			for d in frappe.get_all(
				doctype,
				filters={
					"is_return": 1,
					"docstatus": 1,
					"posting_date": ["between", [self.filters.from_date, self.filters.to_date]],
				},
			)
		]

	def get_party_adjustment_amounts(self):
		conditions = self.prepare_conditions()
		income_or_expense = (
			"Expense Account" if self.filters.party_type == "Customer" else "Income Account"
		)
		invoice_dr_or_cr = "debit" if self.filters.party_type == "Customer" else "credit"
		reverse_dr_or_cr = "credit" if self.filters.party_type == "Customer" else "debit"
		round_off_account = frappe.get_cached_value("Company", self.filters.company, "round_off_account")

		gl_entries = frappe.db.sql(
			"""
			select
				posting_date, account, party, voucher_type, voucher_no, debit, credit
			from
				`tabGL Entry`
			where
				docstatus < 2 and is_cancelled = 0
				and (voucher_type, voucher_no) in (
					select voucher_type, voucher_no from `tabGL Entry` gle, `tabAccount` acc
					where acc.name = gle.account and acc.account_type = '{income_or_expense}'
					and gle.posting_date between %(from_date)s and %(to_date)s and gle.docstatus < 2
				) and (voucher_type, voucher_no) in (
					select voucher_type, voucher_no from `tabGL Entry` gle
					where gle.party_type=%(party_type)s and ifnull(party, '') != ''
					and gle.posting_date between %(from_date)s and %(to_date)s and gle.docstatus < 2 {conditions}
				)
		""".format(
				conditions=conditions, income_or_expense=income_or_expense
			),
			self.filters,
			as_dict=True,
		)

		self.party_adjustment_details = {}
		self.party_adjustment_accounts = set()
		adjustment_voucher_entries = {}
		for gle in gl_entries:
			adjustment_voucher_entries.setdefault((gle.voucher_type, gle.voucher_no), [])
			adjustment_voucher_entries[(gle.voucher_type, gle.voucher_no)].append(gle)

		for voucher_gl_entries in itervalues(adjustment_voucher_entries):
			parties = {}
			accounts = {}
			has_irrelevant_entry = False

			for gle in voucher_gl_entries:
				if gle.account == round_off_account:
					continue
				elif gle.party:
					parties.setdefault(gle.party, 0)
					parties[gle.party] += gle.get(reverse_dr_or_cr) - gle.get(invoice_dr_or_cr)
				elif frappe.get_cached_value("Account", gle.account, "account_type") == income_or_expense:
					accounts.setdefault(gle.account, 0)
					accounts[gle.account] += gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
				else:
					has_irrelevant_entry = True

			if parties and accounts:
				if len(parties) == 1:
					party = list(parties.keys())[0]
					for account, amount in iteritems(accounts):
						self.party_adjustment_accounts.add(account)
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount
				elif len(accounts) == 1 and not has_irrelevant_entry:
					account = list(accounts.keys())[0]
					self.party_adjustment_accounts.add(account)
					for party, amount in iteritems(parties):
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount


def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return PartyLedgerSummaryReport(filters).run(args)
