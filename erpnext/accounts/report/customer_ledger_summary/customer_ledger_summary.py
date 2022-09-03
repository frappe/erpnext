# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _, scrub
from frappe.utils import getdate, nowdate
from erpnext.accounts.utils import get_account_currency
from six import iteritems, itervalues

class PartyLedgerSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')

	def run(self, args):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.filters.party_type = args.get("party_type")
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])

		self.set_account_currency()

		self.get_gl_entries()
		self.get_return_invoices()
		self.get_party_adjustment_amounts()

		columns = self.get_columns()
		data = self.get_data()
		return columns, data

	def get_columns(self):
		columns = [{
			"label": _(self.filters.party_type),
			"fieldtype": "Link",
			"fieldname": "party",
			"options": self.filters.party_type,
			"width": 80 if self.party_naming_by == "Naming Series" else 200
		}]

		if self.party_naming_by == "Naming Series":
			columns.append({
				"label": _(self.filters.party_type + " Name"),
				"fieldtype": "Data",
				"fieldname": "party_name",
				"width": 200
			})

		if self.filters.party_type == "Customer":
			columns.append({
				"label": _("Sales Person"),
				"fieldtype": "Link",
				"options": "Sales Person",
				"fieldname": "sales_person",
				"width": 150
			})

		invoiced_label = "Paid Amount" if self.filters.party_type == "Employee" else "Invoiced Amount"
		paid_label = "Returned Amount" if self.filters.party_type == "Employee" else "Paid Amount"
		if self.filters.party_type in ['Customer', 'Supplier']:
			return_label = "Credit Note" if self.filters.party_type == "Customer" else "Debit Note"
		else:
			return_label = None

		columns += [
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 80
			},
			{
				"label": _("Opening Balance"),
				"fieldname": "opening_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _(invoiced_label),
				"fieldname": "invoiced_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _(paid_label),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
		]

		if return_label:
			columns.append({
				"label": _(return_label),
				"fieldname": "return_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			})

		columns += [
			{
				"label": _("Total Deductions"),
				"fieldname": "total_deductions",
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"label": _("Closing Balance"),
				"fieldname": "closing_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			}
		]

		if self.filters.show_deduction_details:
			for account in self.adjustment_details.accounts:
				columns.append({
					"label": account,
					"fieldname": "adj_" + scrub(account),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120,
					"is_adjustment": 1
				})

		return columns

	def set_account_currency(self):
		self.filters["company_currency"] = frappe.get_cached_value('Company', self.filters.company, "default_currency")
		self.filters["account_currency"] = self.filters["company_currency"]

		if self.filters.get("account") or self.filters.get('party'):
			account_currency = None

			if self.filters.get("account"):
				account_currency = get_account_currency(self.filters.account)
			elif self.filters.get("party"):
				gle_currency = frappe.db.get_value("GL Entry", {
					"party_type": self.filters.party_type, "party": self.filters.party, "company": self.filters.company
				}, "account_currency")

				if gle_currency:
					account_currency = gle_currency
				else:
					account_currency = (None if self.filters.party_type in ["Employee", "Student", "Shareholder", "Member",
						"Letter of Credit"] else frappe.db.get_value(self.filters.party_type, self.filters.party, "default_currency"))

			self.filters["account_currency"] = account_currency or self.filters.company_currency

		self.base_invoice_dr_or_cr = "debit" if self.filters.party_type in ["Customer", "Employee"] else "credit"
		self.base_reverse_dr_or_cr = "credit" if self.filters.party_type in ["Customer", "Employee"] else "debit"

		if self.filters["account_currency"] == self.filters["company_currency"]:
			self.invoice_dr_or_cr = "debit" if self.filters.party_type in ["Customer", "Employee"] else "credit"
			self.reverse_dr_or_cr = "credit" if self.filters.party_type in ["Customer", "Employee"] else "debit"
		else:
			self.invoice_dr_or_cr = "debit_in_account_currency" if self.filters.party_type in ["Customer", "Employee"] else "credit_in_account_currency"
			self.reverse_dr_or_cr = "credit_in_account_currency" if self.filters.party_type in ["Customer", "Employee"] else "debit_in_account_currency"

	def get_data(self):
		self.party_data = frappe._dict({})
		for gle in self.gl_entries:
			self.party_data.setdefault(gle.party, frappe._dict({
				"party": gle.party,
				"party_name": gle.party_name,
				"opening_balance": 0,
				"invoiced_amount": 0,
				"paid_amount": 0,
				"return_amount": 0,
				"closing_balance": 0,
				"currency": self.filters.account_currency
			}))

			amount = gle.get(self.invoice_dr_or_cr) - gle.get(self.reverse_dr_or_cr)
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

		if self.filters.party_type == "Customer":
			customers = list(self.party_data.keys())
			if customers:
				sales_person_map = dict(frappe.db.sql("""
					select steam.parent, GROUP_CONCAT(distinct steam.sales_person SEPARATOR ', ')
					from `tabSales Team` steam
					where steam.parenttype = 'Customer' and steam.parent in %s
					group by steam.parent
				""", [customers]))

				for d in self.party_data.values():
					d.sales_person = sales_person_map.get(d.party)

		out = []
		for party, row in iteritems(self.party_data):
			if row.opening_balance or row.invoiced_amount or row.paid_amount or row.return_amount or row.closing_amount:
				total_party_adjustment = sum([amount for amount in itervalues(self.adjustment_details.parties.get(party, {}))])
				row.paid_amount -= total_party_adjustment
				row.total_deductions = total_party_adjustment

				adjustments = self.adjustment_details.parties.get(party, {})
				for account in self.adjustment_details.accounts:
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
		elif self.filters.party_type == "Employee":
			join_field = ", p.employee_name as party_name"
			join = "left join `tabEmployee` p on gle.party = p.name"

		self.gl_entries = frappe.db.sql("""
			select
				gle.posting_date, gle.party, gle.voucher_type, gle.voucher_no, gle.against_voucher_type,
				gle.against_voucher, gle.debit, gle.credit, gle.debit_in_account_currency, gle.credit_in_account_currency,
				gle.is_opening {join_field}
			from `tabGL Entry` gle
			{join}
			where
				gle.docstatus < 2 and gle.party_type=%(party_type)s and ifnull(gle.party, '') != ''
				and gle.posting_date <= %(to_date)s {conditions}
			order by gle.posting_date
		""".format(join=join, join_field=join_field, conditions=conditions), self.filters, as_dict=True)

	def prepare_conditions(self):
		conditions = [""]

		if self.filters.company:
			conditions.append("gle.company=%(company)s")

		if self.filters.finance_book:
			conditions.append("ifnull(finance_book,'') in (%(finance_book)s, '')")

		if self.filters.get("party"):
			conditions.append("party=%(party)s")

		if self.filters.get("account"):
			conditions.append("account=%(account)s")
		else:
			accounts = [d.name for d in frappe.get_all("Account",
				filters={"account_type": ('in', ['Receivable', 'Payable']), "company": self.filters.company})]
			conditions.append("account in ({0})".format(", ".join([frappe.db.escape(d) for d in accounts])))

		if self.filters.get("cost_center"):
			conditions.append("cost_center=%(cost_center)s")

		if self.filters.party_type == "Customer":
			if self.filters.get("customer_group"):
				lft, rgt = frappe.db.get_value("Customer Group",
					self.filters.get("customer_group"), ["lft", "rgt"])

				conditions.append("""party in (select name from tabCustomer
					where exists(select name from `tabCustomer Group` where lft >= {0} and rgt <= {1}
						and name=tabCustomer.customer_group))""".format(lft, rgt))

			if self.filters.get("territory"):
				lft, rgt = frappe.db.get_value("Territory",
					self.filters.get("territory"), ["lft", "rgt"])

				conditions.append("""party in (select name from tabCustomer
					where exists(select name from `tabTerritory` where lft >= {0} and rgt <= {1}
						and name=tabCustomer.territory))""".format(lft, rgt))

			if self.filters.get("payment_terms_template"):
				conditions.append("party in (select name from tabCustomer where payment_terms=%(payment_terms_template)s)")

			if self.filters.get("sales_partner"):
				conditions.append("party in (select name from tabCustomer where default_sales_partner=%(sales_partner)s)")

			if self.filters.get("sales_person"):
				lft, rgt = frappe.db.get_value("Sales Person", self.filters.get("sales_person"), ["lft", "rgt"])
				conditions.append("""exists(select name from `tabSales Team` steam where
					steam.sales_person in (select name from `tabSales Person` where lft >= {0} and rgt <= {1})
					and steam.parent = party and steam.parenttype = party_type)""".format(lft, rgt))

		if self.filters.party_type == "Supplier":
			if self.filters.get("supplier_group"):
				conditions.append("""party in (select name from tabSupplier
					where supplier_group=%(supplier_group)s)""")

		if self.filters.party_type == "Employee":
			if self.filters.get("department"):
				lft, rgt = frappe.db.get_value("Department",
					self.filters.get("department"), ["lft", "rgt"])

				conditions.append("""gle.party in (select name from tabEmployee
					where exists(select name from `tabDepartment` where lft >= {0} and rgt <= {1}
						and name=tabEmployee.department))""".format(lft, rgt))

			if self.filters.get("designation"):
				conditions.append("gle.party in (select name from tabEmployee where designation=%(designation)s)")

			if self.filters.get("branch"):
				conditions.append("gle.party in (select name from tabEmployee where branch=%(brand)s)")

		hooks = frappe.get_hooks('set_gl_conditions')
		for method in hooks:
			frappe.get_attr(method)(self.filters, conditions, alias='gle')

		return " and ".join(conditions)

	def get_return_invoices(self):
		if self.filters.party_type in ['Customer', 'Supplier']:
			doctype = "Sales Invoice" if self.filters.party_type == "Customer" else "Purchase Invoice"
			self.return_invoices = [d.name for d in frappe.get_all(doctype, filters={"is_return": 1, "docstatus": 1,
				"posting_date": ["between", [self.filters.from_date, self.filters.to_date]]})]
		else:
			self.return_invoices = []

	def get_party_adjustment_amounts(self):
		if self.filters.account_currency != self.filters.company_currency:
			return

		conditions = self.prepare_conditions()

		gl_entries = frappe.db.sql("""
			select
				posting_date, account, party, voucher_type, voucher_no,
				debit, credit, debit_in_account_currency, credit_in_account_currency
			from
				`tabGL Entry`
			where
				voucher_type not in ('Sales Invoice', 'Purchase Invoice')
				and (voucher_type, voucher_no) in (
					select voucher_type, voucher_no from `tabGL Entry` gle, `tabAccount` acc
					where acc.name = gle.account and (acc.root_type in ('Income', 'Expense') or acc.account_type = 'Tax')
					and gle.posting_date between %(from_date)s and %(to_date)s
				) and (voucher_type, voucher_no) in (
					select voucher_type, voucher_no from `tabGL Entry` gle
					where gle.party_type=%(party_type)s and ifnull(party, '') != ''
					and gle.posting_date between %(from_date)s and %(to_date)s {conditions}
				)
		""".format(conditions=conditions), self.filters, as_dict=True)

		adjustment_voucher_entries = {}
		for gle in gl_entries:
			adjustment_voucher_entries.setdefault((gle.voucher_type, gle.voucher_no), [])
			adjustment_voucher_entries[(gle.voucher_type, gle.voucher_no)].append(gle)

		self.adjustment_details = get_adjustment_details(adjustment_voucher_entries,
			self.invoice_dr_or_cr, self.reverse_dr_or_cr)


def get_adjustment_details(adjustment_voucher_entries, invoice_dr_or_cr, reverse_dr_or_cr):
	adjustment_details = frappe._dict({
		'accounts': set(),
		'parties': {},
		'vouchers': {},
	})

	for voucher_gl_entries in adjustment_voucher_entries.values():
		parties = {}
		vouchers = {}
		adj_accounts = {}
		total_adj_amount = 0
		has_irrelevant_entry = False

		# build voucher's party, voucher and adjustment accounts map
		for gle in voucher_gl_entries:
			account_root_type, account_type = frappe.get_cached_value("Account", gle.account, ["root_type", "account_type"])

			if gle.party:
				parties.setdefault(gle.party, 0)
				parties[gle.party] += gle.get(reverse_dr_or_cr) - gle.get(invoice_dr_or_cr)

				if gle.against_voucher_type and gle.against_voucher:
					voucher_tuple = (gle.against_voucher_type, gle.against_voucher)
					vouchers.setdefault(voucher_tuple, 0)
					vouchers[voucher_tuple] += gle.get(reverse_dr_or_cr) - gle.get(invoice_dr_or_cr)

			elif account_root_type in ("Income", "Expense") or account_type == "Tax":
				adj_accounts.setdefault(gle.account, 0)
				adj_accounts[gle.account] += gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
				total_adj_amount += gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
			elif frappe.get_cached_value("Account", gle.account, "account_type") not in ("Bank", "Cash"):
				has_irrelevant_entry = True

		# party wise adjustments
		if parties and adj_accounts:
			if len(parties) == 1:
				party = list(parties.keys())[0]
				for adj_account, adj_amount in iteritems(adj_accounts):
					if adj_amount <= 0:
						continue

					adjustment_details.accounts.add(adj_account)
					adjustment_details.parties.setdefault(party, {})
					adjustment_details.parties[party].setdefault(adj_account, 0)
					adjustment_details.parties[party][adj_account] += adj_amount

			elif len(adj_accounts) == 1 and not has_irrelevant_entry:
				adj_account = list(adj_accounts.keys())[0]
				party_sum = sum(parties.values())

				for party, party_amount in iteritems(parties):
					if total_adj_amount <= 0:
						continue

					adjustment_details.accounts.add(adj_account)
					adjustment_details.parties.setdefault(party, {})
					adjustment_details.parties[party].setdefault(adj_account, 0)
					adjustment_details.parties[party][adj_account] += total_adj_amount * (party_amount / party_sum)

		# voucher wise adjustments
		if vouchers and adj_accounts:
			if len(vouchers) == 1:
				voucher = list(vouchers.keys())[0]
				for adj_account, adj_amount in iteritems(adj_accounts):
					if adj_amount <= 0:
						continue

					adjustment_details.accounts.add(adj_account)
					adjustment_details.vouchers.setdefault(voucher, {})
					adjustment_details.vouchers[voucher].setdefault(adj_account, 0)
					adjustment_details.vouchers[voucher][adj_account] += adj_amount

			elif len(adj_accounts) == 1 and not has_irrelevant_entry:
				adj_account = list(adj_accounts.keys())[0]
				vouchers_sum = sum(vouchers.values())

				for voucher, voucher_amount in iteritems(vouchers):
					if total_adj_amount <= 0:
						continue

					adjustment_details.accounts.add(adj_account)
					adjustment_details.vouchers.setdefault(voucher, {})
					adjustment_details.vouchers[voucher].setdefault(adj_account, 0)
					adjustment_details.vouchers[voucher][adj_account] += total_adj_amount * (voucher_amount / vouchers_sum)

			# distribute adjustment accounts using ratio of against voucher amounts
			elif len(parties) == 1:
				vouchers_sum = sum(vouchers.values())
				if vouchers_sum:
					for adj_account, adj_amount in adj_accounts.items():
						if adj_amount <= 0:
							continue

						adjustment_details.accounts.add(adj_account)
						for voucher, voucher_amount in vouchers.items():
							adjustment_details.vouchers.setdefault(voucher, {})
							adjustment_details.vouchers[voucher].setdefault(adj_account, 0)
							adjustment_details.vouchers[voucher][adj_account] += adj_amount * (voucher_amount / vouchers_sum)

	return adjustment_details


def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return PartyLedgerSummaryReport(filters).run(args)
