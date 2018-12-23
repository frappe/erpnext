# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt
from erpnext.accounting.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

from six import iteritems
from six.moves import zip

class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		return self.get_columns(party_naming_by, args), self.get_data(party_naming_by, args)

	def get_columns(self, party_naming_by, args):
		columns = [_(args.get("party_type")) + ":Link/" + args.get("party_type") + ":200"]

		if party_naming_by == "Naming Series":
			columns += [ args.get("party_type") + " Name::140"]

		credit_debit_label = "Credit Note Amt" if args.get('party_type') == 'Customer' else "Debit Note Amt"

		columns += [{
			"label": _("Total Invoiced Amt"),
			"fieldname": "total_invoiced_amt",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100
		},
		{
			"label": _("Total Paid Amt"),
			"fieldname": "total_paid_amt",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100
		}]

		columns += [
			{
				"label": _(credit_debit_label),
				"fieldname": scrub(credit_debit_label),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140
			},
			{
				"label": _("Total Outstanding Amt"),
				"fieldname": "total_outstanding_amt",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 160
			},
			{
				"label": _("0-" + str(self.filters.range1)),
				"fieldname": scrub("0-" + str(self.filters.range1)),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 160
			},
			{
				"label": _(str(self.filters.range1) + "-" + str(self.filters.range2)),
				"fieldname": scrub(str(self.filters.range1) + "-" + str(self.filters.range2)),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 160
			},
			{
				"label": _(str(self.filters.range2) + "-" + str(self.filters.range3)),
				"fieldname": scrub(str(self.filters.range2) + "-" + str(self.filters.range3)),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 160
			},
			{
				"label": _(str(self.filters.range3) + _("-Above")),
				"fieldname": scrub(str(self.filters.range3) + _("-Above")),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 160
			}
		]

		if args.get("party_type") == "Customer":
			columns += [{
				"label": _("Territory"),
				"fieldname": "territory",
				"fieldtype": "Link",
				"options": "Territory",
				"width": 80
			},
			{
				"label": _("Customer Group"),
				"fieldname": "customer_group",
				"fieldtype": "Link",
				"options": "Customer Group",
				"width": 80
			},
			{
				"label": _("Sales Person"),
				"fieldtype": "Data",
				"fieldname": "sales_person",
				"width": 120,
			}]

		if args.get("party_type") == "Supplier":
			columns += [{
				"label": _("Supplier Group"),
				"fieldname": "supplier_group",
				"fieldtype": "Link",
				"options": "Supplier Group",
				"width": 80
			}]

		columns.append({
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80
		})

		return columns

	def get_data(self, party_naming_by, args):
		data = []

		partywise_total = self.get_partywise_total(party_naming_by, args)

		for party, party_dict in iteritems(partywise_total):
			row = [party]

			if party_naming_by == "Naming Series":
				row += [self.get_party_name(args.get("party_type"), party)]

			row += [
				party_dict.invoiced_amt, party_dict.paid_amt, party_dict.credit_amt, party_dict.outstanding_amt,
				party_dict.range1, party_dict.range2, party_dict.range3, party_dict.range4,
			]

			if args.get("party_type") == "Customer":
				row += [self.get_territory(party), self.get_customer_group(party), ", ".join(set(party_dict.sales_person))]
			if args.get("party_type") == "Supplier":
				row += [self.get_supplier_group(party)]

			row.append(party_dict.currency)
			data.append(row)

		return data

	def get_partywise_total(self, party_naming_by, args):
		party_total = frappe._dict()
		for d in self.get_voucherwise_data(party_naming_by, args):
			party_total.setdefault(d.party,
				frappe._dict({
					"invoiced_amt": 0,
					"paid_amt": 0,
					"credit_amt": 0,
					"outstanding_amt": 0,
					"range1": 0,
					"range2": 0,
					"range3": 0,
					"range4": 0,
					"sales_person": []
				})
			)
			for k in list(party_total[d.party]):
				if k not in ["currency", "sales_person"]:
					party_total[d.party][k] += flt(d.get(k, 0))

			party_total[d.party].currency = d.currency

			if d.sales_person:
				party_total[d.party].sales_person.append(d.sales_person)

		return party_total

	def get_voucherwise_data(self, party_naming_by, args):
		voucherwise_data = ReceivablePayableReport(self.filters).run(args)[1]

		cols = ["posting_date", "party"]

		if party_naming_by == "Naming Series":
			cols += ["party_name"]

		cols += ["voucher_type", "voucher_no", "due_date"]

		if args.get("party_type") == "Supplier":
			cols += ["bill_no", "bill_date"]

		cols += ["invoiced_amt", "paid_amt", "credit_amt",
		"outstanding_amt", "age", "range1", "range2", "range3", "range4", "currency", "pdc/lc_date", "pdc/lc_ref",
		"pdc/lc_amount", "remaining_balance"]

		if args.get("party_type") == "Supplier":
			cols += ["supplier_group", "remarks"]
		if args.get("party_type") == "Customer":
			cols += ["po_no", "do_no", "territory", "customer_group", "sales_person", "remarks"]

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
