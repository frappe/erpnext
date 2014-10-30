# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		return self.get_columns(party_naming_by), self.get_data(party_naming_by, args)

	def get_columns(self, party_naming_by):
		columns = [_("Customer") + ":Link/Customer:200"]

		if party_naming_by == "Naming Series":
			columns += ["Customer Name::140"]

		columns += [
			_("Total Invoiced Amt") + ":Currency:140",
			_("Total Paid Amt") + ":Currency:140",
			_("Total Outstanding Amt") + ":Currency:160",
			"0-" + self.filters.range1 + ":Currency:100",
			self.filters.range1 + "-" + self.filters.range2 + ":Currency:100",
			self.filters.range2 + "-" + self.filters.range3 + ":Currency:100",
			self.filters.range3 + _("-Above") + ":Currency:100",
			_("Territory") + ":Link/Territory:80"
		]

		return columns

	def get_data(self, party_naming_by, args):
		data = []

		customerwise_total = self.get_customerwise_total(party_naming_by, args)

		for customer, customer_dict in customerwise_total.items():
			row = [customer]

			if party_naming_by == "Naming Series":
				row += [self.get_party_name("Customer", customer)]

			row += [
				customer_dict.invoiced_amt, customer_dict.paid_amt, customer_dict.outstanding_amt,
				customer_dict.range1, customer_dict.range2, customer_dict.range3, customer_dict.range4,
				self.get_territory(customer)
			]
			data.append(row)

		return data

	def get_customerwise_total(self, party_naming_by, args):
		customer_total = frappe._dict()
		for d in self.get_voucherwise_data(party_naming_by, args):
			customer_total.setdefault(d.customer,
				frappe._dict({
					"invoiced_amt": 0,
					"paid_amt": 0,
					"outstanding_amt": 0,
					"range1": 0,
					"range2": 0,
					"range3": 0,
					"range4": 0
				})
			)
			for k in customer_total[d.customer].keys():
				customer_total[d.customer][k] += d.get(k, 0)

		return customer_total

	def get_voucherwise_data(self, party_naming_by, args):
		voucherwise_data = ReceivablePayableReport(self.filters).run(args)[1]

		cols = ["posting_date", "customer"]

		if party_naming_by == "Naming Series":
			cols += ["customer_name"]

		cols += ["voucher_type", "voucher_no", "due_date", "invoiced_amt", "paid_amt",
		"outstanding_amt", "age", "range1", "range2", "range3", "range4", "territory", "remarks"]

		return self.make_data_dict(cols, voucherwise_data)

	def make_data_dict(self, cols, data):
		data_dict = []
		for d in data:
			data_dict.append(frappe._dict(zip(cols, d)))

		return data_dict

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummary(filters).run(args)
