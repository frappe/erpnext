import frappe
from frappe.utils import flt
from erpnext.accounts.general_ledger import delete_voucher_gl_entries


def execute():
	pinvs = frappe.get_all("Purchase Invoice", filters={"docstatus": 1})
	pinvs = [d.name for d in pinvs]

	for name in pinvs:
		doc = frappe.get_doc("Purchase Invoice", name)
		party_type, party = doc.get_billing_party()

		supplier_bal = frappe.db.sql("""
			select sum(credit-debit)
			from `tabGL Entry`
			where voucher_type = 'Purchase Invoice' and voucher_no = %s and party_type = %s and party = %s
		""", (doc.name, party_type, party))

		supplier_bal = flt(supplier_bal[0][0]) if supplier_bal else 0

		grand_total = doc.base_rounded_total or doc.base_grand_total
		grand_total -= doc.base_write_off_amount
		if doc.get('is_paid'):
			grand_total -= doc.base_paid_amount

		grand_total = flt(grand_total, doc.precision('grand_total'))

		if supplier_bal != grand_total:
			print("REPOSTING {} (GLE {} / INV {})".format(doc.name, supplier_bal, grand_total))
			delete_voucher_gl_entries(doc.doctype, doc.name)
			doc.make_gl_entries(repost_future_gle=False)

		doc.clear_cache()
