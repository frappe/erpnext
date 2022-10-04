import frappe
from frappe import qb
from frappe.utils import create_batch


def execute():
	if frappe.reload_doc("accounts", "doctype", "payment_ledger_entry"):

		gle = qb.DocType("GL Entry")
		ple = qb.DocType("Payment Ledger Entry")

		# get ple and their remarks from GL Entry
		pl_entries = (
			qb.from_(ple)
			.left_join(gle)
			.on(
				(ple.account == gle.account)
				& (ple.party_type == gle.party_type)
				& (ple.party == gle.party)
				& (ple.voucher_type == gle.voucher_type)
				& (ple.voucher_no == gle.voucher_no)
				& (ple.company == gle.company)
			)
			.select(
				ple.company,
				ple.account,
				ple.party_type,
				ple.party,
				ple.voucher_type,
				ple.voucher_no,
				gle.remarks.as_("gle_remarks"),
			)
			.where((ple.delinked == 0) & (gle.is_cancelled == 0))
			.run(as_dict=True)
		)

		if pl_entries:
			# split into multiple batches, update and commit for each batch
			batch_size = 1000
			for batch in create_batch(pl_entries, batch_size):
				for entry in batch:
					query = (
						qb.update(ple)
						.set(ple.remarks, entry.gle_remarks)
						.where(
							(ple.company == entry.company)
							& (ple.account == entry.account)
							& (ple.party_type == entry.party_type)
							& (ple.party == entry.party)
							& (ple.voucher_type == entry.voucher_type)
							& (ple.voucher_no == entry.voucher_no)
						)
					)
					query.run()

				frappe.db.commit()
