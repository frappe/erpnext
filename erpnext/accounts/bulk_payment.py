import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_outstanding_reference_documents,
	get_payment_entry,
)


@frappe.whitelist(methods=["POST"])
def create_payment_entries(invoices: str | list | None = None):
	"""Create draft Payment Entries from AP report invoice selection."""
	frappe.has_permission("Payment Entry", "create", throw=True)

	names = [d["voucher_no"] for d in frappe.parse_json(invoices or "[]") if d.get("voucher_no")]
	if not names:
		frappe.throw(_("No Purchase Invoices selected"))

	payable, excluded = _partition_payable_invoices(names)
	if not payable:
		frappe.throw(_("None of the selected invoices are payable"))

	# invoices sharing a (supplier, payable account) are combined into one Payment Entry
	groups = {}
	for d in payable:
		key = (d["supplier"], d["party_account"])
		groups.setdefault(
			key, {"supplier": d["supplier"], "party_account": d["party_account"], "vouchers": []}
		)["vouchers"].append(d["voucher_no"])

	created, failed = 0, 0
	for group in groups.values():
		if _create_payment_entry(group):
			created += 1
		else:
			failed += 1

	message = _("Created {0} draft Payment Entries").format(created)
	if excluded:
		message += " — " + _("{0} excluded (not payable)").format(len(excluded))
	if failed:
		message += " — " + _("{0} failed (see Error Log)").format(failed)
	frappe.msgprint(message, title=_("Bulk Payment Entries"), indicator="green")


@frappe.whitelist()
def get_payable_invoices(invoices: str | list | None = None):
	"""Return the live payable subset of the selected invoices for the report dialog."""
	frappe.has_permission("Payment Entry", "create", throw=True)

	names = [d["voucher_no"] for d in frappe.parse_json(invoices or "[]") if d.get("voucher_no")]
	payable, excluded = _partition_payable_invoices(names)

	currency = None
	if payable:
		company = frappe.get_cached_value("Purchase Invoice", payable[0]["voucher_no"], "company")
		currency = frappe.get_cached_value("Company", company, "default_currency")

	return {"payable": payable, "excluded": excluded, "currency": currency}


def _partition_payable_invoices(names):
	"""Split submitted Purchase Invoices into payable ones and excluded ones (with reason).

	Returns are debit notes, internal transfers are inter-company, and non-positive
	outstanding means already settled — none are valid targets for a supplier payment.
	"""
	if not names:
		return [], []

	rows = frappe.get_list(
		"Purchase Invoice",
		filters={"name": ["in", names], "docstatus": 1},
		fields=[
			"name",
			"supplier",
			"credit_to",
			"outstanding_amount",
			"conversion_rate",
			"is_return",
			"is_internal_supplier",
		],
		limit_page_length=0,
	)

	payable, excluded = [], []
	for r in rows:
		if r.is_return:
			excluded.append({"voucher_no": r.name, "reason": _("Debit Note")})
		elif r.is_internal_supplier:
			excluded.append({"voucher_no": r.name, "reason": _("Internal Transfer")})
		elif flt(r.outstanding_amount) <= 0:
			excluded.append({"voucher_no": r.name, "reason": _("Already Paid")})
		else:
			payable.append(
				{
					"voucher_no": r.name,
					"supplier": r.supplier,
					"party_account": r.credit_to,
					"outstanding": flt(r.outstanding_amount) * flt(r.conversion_rate or 1),
				}
			)

	# names not returned were cancelled/deleted or no longer readable after the report loaded
	found = {r.name for r in rows}
	for name in names:
		if name not in found:
			excluded.append({"voucher_no": name, "reason": _("Not available")})

	return payable, excluded


def _create_payment_entry(group):
	supplier = group["supplier"]
	try:
		frappe.db.savepoint("bulk_pe")
		if len(group["vouchers"]) == 1:
			pe = _build_single_payment_entry(group["vouchers"][0])
		else:
			pe = _build_grouped_payment_entry(supplier, group["party_account"], group["vouchers"])

		if not pe:
			frappe.db.rollback(save_point="bulk_pe")
			frappe.log_error(
				title=_("Bulk Payment Entry skipped for {0}").format(supplier),
				message=_("No outstanding amount for the selected invoice(s)."),
			)
			return False

		pe.flags.ignore_validate = True
		pe.set_title_field()
		pe.insert(ignore_mandatory=True)
		return True
	except Exception:
		frappe.db.rollback(save_point="bulk_pe")
		frappe.log_error(title=_("Bulk Payment Entry creation failed for {0}").format(supplier))
		return False


def _build_single_payment_entry(name):
	pe = get_payment_entry("Purchase Invoice", name)
	# guard against a stale report row: nothing to allocate means the invoice is already settled
	if not pe.references or not any(flt(r.allocated_amount) for r in pe.references):
		return None
	return pe


def _build_grouped_payment_entry(supplier, party_account, names):
	name_set = set(names)
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

	# get_negative_outstanding_invoices ignores the vouchers filter, so bound refs to the selection
	for r in refs:
		if r.voucher_type != "Purchase Invoice" or r.voucher_no not in name_set:
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
