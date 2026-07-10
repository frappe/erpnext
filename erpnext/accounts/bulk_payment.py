import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_outstanding_reference_documents,
	get_payment_entry,
)
from erpnext.utilities.bulk_transaction import transaction_processing


@frappe.whitelist(methods=["POST"])
def create_payment_entries(
	grouped_invoices: str | list | None = None,
	ungrouped_invoices: str | list | None = None,
):
	"""Create draft Payment Entries from AP report invoice selection."""
	frappe.has_permission("Payment Entry", "create", throw=True)

	grouped_invoices = [d for d in frappe.parse_json(grouped_invoices or "[]") if d.get("voucher_no")]
	ungrouped_invoices = [d for d in frappe.parse_json(ungrouped_invoices or "[]") if d.get("voucher_no")]

	if not grouped_invoices and not ungrouped_invoices:
		frappe.throw(_("No Purchase Invoices selected"))

	if ungrouped_invoices:
		data = [{"name": d["voucher_no"]} for d in ungrouped_invoices]
		transaction_processing(data, "Purchase Invoice", "Payment Entry")

	if grouped_invoices:
		groups = {}
		for d in grouped_invoices:
			key = (d["supplier"], d["party_account"])
			groups.setdefault(
				key, {"supplier": d["supplier"], "party_account": d["party_account"], "vouchers": []}
			)["vouchers"].append(d["voucher_no"])

		frappe.msgprint(
			_("Started a background job to create {0} Grouped Payment Entries").format(len(groups))
		)
		frappe.enqueue(
			make_grouped_payment_entries,
			queue="long",
			timeout=1500,
			groups=list(groups.values()),
		)


def make_grouped_payment_entries(groups):
	created, failed = 0, 0

	for group in groups:
		supplier = group["supplier"]
		try:
			frappe.db.savepoint("bulk_pe")
			pe = _build_grouped_payment_entry(supplier, group["party_account"], group["vouchers"])
			if not pe:
				frappe.db.rollback(save_point="bulk_pe")
				failed += 1
				frappe.log_error(
					title=_("Bulk Payment Entry skipped for {0}").format(supplier),
					message=_(
						"No outstanding invoices found for the selected vouchers in account {0}"
					).format(group["party_account"]),
				)
				continue

			pe.flags.ignore_validate = True
			pe.set_title_field()
			pe.insert(ignore_mandatory=True)
			created += 1
		except Exception:
			frappe.db.rollback(save_point="bulk_pe")
			failed += 1
			frappe.log_error(title=_("Bulk Payment Entry creation failed for {0}").format(supplier))

	message = _("Created {0} draft Grouped Payment Entries").format(created)

	if failed:
		message += " — " + _("{0} skipped (see Error Log)").format(failed)

	frappe.publish_realtime(
		"msgprint",
		{"message": message, "title": _("Bulk Payment Entries"), "indicator": "green"},
		user=frappe.session.user,
		after_commit=True,
	)


def _build_grouped_payment_entry(supplier, party_account, names):
	pe = get_payment_entry("Purchase Invoice", names[0])
	pe.set("references", [])

	refs = get_outstanding_reference_documents(
		{
			"party_type": "Supplier",
			"party": supplier,
			"party_account": party_account,
			"company": pe.company,
			"vouchers": [frappe._dict(voucher_type="Purchase Invoice", voucher_no=n) for n in names],
		}
	)

	for r in refs:
		if r.voucher_type != "Purchase Invoice":
			continue
		pe.append(
			"references",
			{
				"reference_doctype": r.voucher_type,
				"reference_name": r.voucher_no,
				"bill_no": r.get("bill_no"),
				"due_date": r.get("due_date"),
				"payment_term": r.get("payment_term"),
				"total_amount": r.invoice_amount,
				"outstanding_amount": r.outstanding_amount,
				"allocated_amount": r.outstanding_amount,
				"exchange_rate": r.get("exchange_rate") or 1,
			},
		)

	if not pe.references:
		return None

	# received_amount is in paid_to account currency; convert to paid_from account currency for paid_amount
	pe.received_amount = sum(r.allocated_amount for r in pe.references)
	pe.paid_amount = flt(pe.received_amount * pe.target_exchange_rate, pe.precision("paid_amount"))
	pe.set_amounts()
	return pe
