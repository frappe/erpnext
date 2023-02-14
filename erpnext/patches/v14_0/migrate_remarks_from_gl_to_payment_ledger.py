import frappe
from frappe import qb
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import Count, IfNull
from frappe.utils import flt


def execute():
	"""
	Migrate 'remarks' field from 'tabGL Entry' to 'tabPayment Ledger Entry'
	"""

	if frappe.reload_doc("accounts", "doctype", "payment_ledger_entry"):

		gle = qb.DocType("GL Entry")
		ple = qb.DocType("Payment Ledger Entry")

		# Get empty PLE records
		un_processed = (
			qb.from_(ple).select(Count(ple.name)).where((ple.remarks.isnull()) & (ple.delinked == 0)).run()
		)[0][0]

		if un_processed:
			print(f"Remarks for {un_processed} Payment Ledger records will be updated from GL Entry")

			ifelse = CustomFunction("IF", ["condition", "then", "else"])

			processed = 0
			last_percent_update = 0
			batch_size = 1000
			last_name = None

			while True:
				if last_name:
					where_clause = (ple.name.gt(last_name)) & (ple.remarks.isnull()) & (ple.delinked == 0)
				else:
					where_clause = (ple.remarks.isnull()) & (ple.delinked == 0)

				# results are deterministic
				names = (
					qb.from_(ple).select(ple.name).where(where_clause).orderby(ple.name).limit(batch_size).run()
				)

				if names:
					last_name = names[-1][0]

					pl_entries = (
						qb.from_(ple)
						.left_join(gle)
						.on(
							(ple.account == gle.account)
							& (ple.party_type == gle.party_type)
							& (ple.party == gle.party)
							& (ple.voucher_type == gle.voucher_type)
							& (ple.voucher_no == gle.voucher_no)
							& (
								ple.against_voucher_type
								== IfNull(
									ifelse(gle.against_voucher_type == "", None, gle.against_voucher_type), gle.voucher_type
								)
							)
							& (
								ple.against_voucher_no
								== IfNull(ifelse(gle.against_voucher == "", None, gle.against_voucher), gle.voucher_no)
							)
							& (ple.company == gle.company)
							& (
								((ple.account_type == "Receivable") & (ple.amount == (gle.debit - gle.credit)))
								| (ple.account_type == "Payable") & (ple.amount == (gle.credit - gle.debit))
							)
							& (gle.remarks.notnull())
							& (gle.is_cancelled == 0)
						)
						.select(ple.name)
						.distinct()
						.select(
							gle.remarks.as_("gle_remarks"),
						)
						.where(ple.name.isin(names))
						.run(as_dict=True)
					)

					if pl_entries:
						for entry in pl_entries:
							query = qb.update(ple).set(ple.remarks, entry.gle_remarks).where((ple.name == entry.name))
							query.run()

						frappe.db.commit()

						processed += len(pl_entries)
						percentage = flt((processed / un_processed) * 100, 2)
						if percentage - last_percent_update > 1:
							print(f"{percentage}% ({processed}) PLE records updated")
							last_percent_update = percentage

				else:
					break
			print("Remarks succesfully migrated")
