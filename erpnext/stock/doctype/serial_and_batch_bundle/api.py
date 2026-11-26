from typing import Any, Literal

import frappe
from frappe import _
from frappe.core.doctype.user_permission.user_permission import get_user_permissions
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, nowtime, parse_json, today

from erpnext import _is_within_user_permissions, _refuse, require_permission
from erpnext.stock.doctype.purchase_receipt_item.purchase_receipt_item import PurchaseReceiptItem
from erpnext.stock.serial_batch_bundle.availability.batches import (
	get_auto_batch_nos,
	get_batch_nos_from_sre,
	get_qty_based_available_batches,
)
from erpnext.stock.serial_batch_bundle.availability.reservations import get_serial_nos_from_sre
from erpnext.stock.serial_batch_bundle.availability.serial_nos import get_available_serial_nos
from erpnext.stock.serial_batch_bundle.bundle_entries import _get_serial_batch_ledgers, get_filters_for_bundle
from erpnext.stock.serial_batch_identity import SerialBatchIdentity


@frappe.whitelist()
def get_auto_data(**kwargs):
	kwargs = frappe._dict(kwargs)
	if kwargs.warehouse:
		require_permission("Warehouse", kwargs.warehouse, "select")

	warehouses = frappe.get_list("Warehouse", pluck="name", limit=0)
	if len(warehouses) == frappe.db.count("Warehouse"):
		return get_auto_data_rows(kwargs)

	return get_auto_data_rows_in_warehouses(kwargs, set(warehouses))


def get_auto_data_rows(kwargs):
	if cint(kwargs.has_serial_no):
		return get_serial_nos_from_sre(kwargs) if kwargs.scio_detail else get_available_serial_nos(kwargs)
	elif cint(kwargs.has_batch_no):
		return get_batch_nos_from_sre(kwargs) if kwargs.scio_detail else get_auto_batch_nos(kwargs)


def get_auto_data_rows_in_warehouses(kwargs, warehouses):
	if not warehouses:
		return []

	if cint(kwargs.has_serial_no) and not kwargs.scio_detail:
		kwargs.warehouse = kwargs.warehouse or list(warehouses)
		return [row for row in get_available_serial_nos(kwargs) if row.warehouse in warehouses]

	qty = flt(kwargs.qty)
	kwargs.qty = 0
	rows = [row for row in get_auto_data_rows(kwargs) or [] if row.warehouse in warehouses]
	if not qty:
		return rows

	if cint(kwargs.has_serial_no):
		return rows[: cint(qty)]

	return get_qty_based_available_batches(rows, qty)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(
	doctype: Any, txt: str, searchfield: str, start: int, page_len: int, filters: Any, as_dict: bool = False
):
	item_filters = {"disabled": 0}
	if txt:
		item_filters["name"] = ("like", f"%{txt}%")

	# get_list, not get_all, so Item permissions apply; `select` is what keeps the roles that work bundles usable
	return frappe.get_list(
		"Item",
		filters=item_filters,
		or_filters={"has_serial_no": 1, "has_batch_no": 1},
		fields=["name", "item_name"],
		as_list=1,
	)


@frappe.whitelist()
def get_serial_batch_ledgers(
	item_code: str | None = None,
	docstatus: str | list | int | None = None,
	voucher_no: str | None = None,
	name: str | list | None = None,
	child_row: dict | str | None = None,
):
	if not frappe.has_permission("Serial and Batch Bundle", "select"):
		_refuse()
	filters = get_filters_for_bundle(
		item_code=item_code, docstatus=docstatus, voucher_no=voucher_no, name=name, child_row=child_row
	)
	bundle_filters = []
	for doctype, fieldname, condition, value in filters:
		if doctype == "Serial and Batch Entry" and fieldname == "parent":
			bundle_filters.append(["Serial and Batch Bundle", "name", condition, value])
		else:
			bundle_filters.append([doctype, fieldname, condition, value])
	permitted = frappe.get_list(
		"Serial and Batch Bundle", filters=bundle_filters, pluck="name", limit_page_length=0
	)
	if not permitted:
		return []
	rows = _get_serial_batch_ledgers(item_code, docstatus, None, permitted, child_row)
	if not get_user_permissions():
		return rows
	fenced = {}
	permitted_rows = []
	for row in rows:
		within_fence = True
		for doctype, value in (("Batch", row.batch_no), ("Serial No", row.serial_no)):
			if not value:
				continue
			if (doctype, value) not in fenced:
				fenced[(doctype, value)] = _is_within_user_permissions(doctype, value)
			if not fenced[(doctype, value)]:
				within_fence = False
				break
		if within_fence:
			permitted_rows.append(row)
	return permitted_rows


@frappe.whitelist(methods=["POST"])
def add_serial_batch_ledgers(
	entries: list | str,
	child_row: PurchaseReceiptItem | dict | str,
	doc: Document | dict | str,
	warehouse: str | None = None,
	do_not_save: bool = False,
	csv_entries: list | str | None = None,
):
	child_row = parse_json(child_row)
	csv_entries = parse_json(csv_entries) or []

	if isinstance(entries, str):
		entries = parse_json(entries)

	parent_doc = doc
	if parent_doc and isinstance(parent_doc, str):
		parent_doc = parse_json(parent_doc)
	if (
		not parent_doc
		or not parent_doc.get("doctype")
		or child_row.get("parenttype") != parent_doc.get("doctype")
	):
		frappe.throw(_("The selected row does not belong to the parent document"))
	frappe.has_permission(parent_doc.get("doctype"), "write", throw=True)

	bundle_field = "serial_and_batch_bundle"
	if child_row.get("is_rejected"):
		bundle_field = "rejected_serial_and_batch_bundle"

	row = frappe._dict()
	if do_not_save:
		child_row.doctype = cstr(child_row.doctype)
		if not is_bundle_child_row(child_row.doctype):
			frappe.throw(_("{0} does not carry a serial and batch bundle").format(child_row.doctype))
		fields = ["parenttype", "parent"]
		if frappe.get_meta(child_row.doctype).has_field(bundle_field):
			fields.append(bundle_field)
		child_row.name = cstr(child_row.name)
		row = (
			child_row.name and frappe.db.get_value(child_row.doctype, child_row.name, fields, as_dict=True)
		) or frappe._dict()
		bundle = row.get(bundle_field)
	else:
		bundle = cstr(child_row.get(bundle_field))

	if bundle and frappe.db.exists("Serial and Batch Bundle", bundle):
		if do_not_save:
			require_permission("Serial and Batch Bundle", bundle, "write")
		elif not frappe.has_permission("Serial and Batch Bundle", "write", doc=bundle):
			_refuse()
		sb_doc = update_serial_batch_no_ledgers(
			bundle, entries, child_row, parent_doc, warehouse, csv_entries=csv_entries
		)
	else:
		if do_not_save:
			require_permission(row.parenttype, row.parent, "write")
		sb_doc = create_serial_batch_no_ledgers(
			entries, child_row, parent_doc, warehouse, do_not_save=do_not_save, csv_entries=csv_entries
		)

	return sb_doc


def create_serial_batch_no_ledgers(
	entries, child_row, parent_doc, warehouse=None, do_not_save=False, csv_entries=None
) -> object:
	from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import resolve_csv_entries
	from erpnext.stock.utils import get_combine_datetime

	warehouse = warehouse or (child_row.rejected_warehouse if child_row.is_rejected else child_row.warehouse)

	type_of_transaction = get_type_of_transaction(parent_doc, child_row)
	if parent_doc.get("doctype") == "Stock Entry":
		warehouse = warehouse or child_row.s_warehouse or child_row.t_warehouse

	posting_datetime = get_combine_datetime(
		parent_doc.get("posting_date") or today(), parent_doc.get("posting_time") or nowtime()
	)

	doc = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": child_row.parenttype,
			"item_code": child_row.item_code,
			"warehouse": warehouse,
			"is_rejected": child_row.is_rejected,
			"type_of_transaction": type_of_transaction,
			"posting_datetime": posting_datetime,
			"company": parent_doc.get("company"),
		}
	)

	doc.check_permission("create")
	entries = [
		*entries,
		*resolve_csv_entries(csv_entries or [], doc.item_code, doc.type_of_transaction, doc.company),
	]
	if not entries:
		frappe.throw(_("Please add at least one Serial No or Batch to save"))

	batch_no = None

	if (
		not entries[0].get("batch_no")
		and entries[0].get("serial_no")
		and frappe.get_cached_value("Item", child_row.item_code, "has_batch_no")
	):
		batch_no = get_batch(child_row.item_code)

	for row in entries:
		row = frappe._dict(row)
		doc.append(
			"entries",
			{
				"qty": (flt(row.qty) or 1.0) * (1 if type_of_transaction == "Inward" else -1),
				"warehouse": warehouse,
				"batch_no": row.batch_no or batch_no,
				"serial_no": row.serial_no,
			},
		)

	doc.save()

	if do_not_save:
		frappe.db.set_value(child_row.doctype, child_row.name, "serial_and_batch_bundle", doc.name)

	frappe.msgprint(_("Serial and Batch Bundle created"), alert=True)

	return doc


def update_serial_batch_no_ledgers(
	bundle, entries, child_row, parent_doc, warehouse=None, csv_entries=None
) -> object:
	from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import resolve_csv_entries
	from erpnext.stock.utils import get_combine_datetime

	doc = frappe.get_doc("Serial and Batch Bundle", bundle)
	doc.check_permission("write")

	if doc.docstatus != 0:
		doc.throw_error_message(
			_("Serial and Batch Bundle {0} is not a draft and its entries cannot be modified.").format(
				frappe.bold(bundle)
			)
		)

	if doc.item_code != child_row.get("item_code") or doc.company != parent_doc.get("company"):
		frappe.throw(_("The selected bundle must belong to the same Item and Company"))

	entries = [
		*entries,
		*resolve_csv_entries(csv_entries or [], doc.item_code, doc.type_of_transaction, doc.company),
	]
	doc.voucher_detail_no = child_row.name
	doc.posting_datetime = get_combine_datetime(
		parent_doc.get("posting_date") or today(), parent_doc.get("posting_time") or nowtime()
	)

	doc.warehouse = warehouse or doc.warehouse
	doc.set("entries", [])

	for d in entries:
		doc.append(
			"entries",
			{
				"qty": (flt(d.get("qty")) or 1.0) * (1 if doc.type_of_transaction == "Inward" else -1),
				"warehouse": warehouse or d.get("warehouse"),
				"batch_no": d.get("batch_no"),
				"serial_no": d.get("serial_no"),
			},
		)

	doc.save(ignore_permissions=True)

	frappe.msgprint(_("Serial and Batch Bundle updated"), alert=True)

	return doc


def is_bundle_child_row(doctype: str) -> bool:
	if not doctype or not frappe.db.exists("DocType", doctype):
		return False
	meta = frappe.get_meta(doctype)
	if not meta.istable:
		return False
	return bool(meta.has_field("serial_and_batch_bundle"))


def get_type_of_transaction(parent_doc, child_row):
	match parent_doc.get("doctype"):
		case "Stock Entry":
			return "Outward" if child_row.get("s_warehouse") else "Inward"
		case "Purchase Receipt" | "Purchase Invoice" | "Stock Reconciliation":
			inward = True
		case "Subcontracting Receipt":
			inward = child_row.get("doctype") == "Subcontracting Receipt Item"
		case _:
			inward = False

	if parent_doc.get("is_return"):
		inward = not inward

	return "Inward" if inward else "Outward"


def get_batch(item_code):
	from erpnext.stock.doctype.batch.batch import make_batch

	return make_batch(
		frappe._dict(
			{
				"item": item_code,
			}
		)
	)


@frappe.whitelist()
def get_serial_batch_scan(item_code: str, number: str, doctype: Literal["Serial No", "Batch"]):
	if not item_code:
		frappe.throw(_("Item is required"))
	frappe.has_permission("Item", "select", doc=item_code, throw=True)
	if not number.strip():
		return {}

	identity = SerialBatchIdentity(doctype)
	fields = ["name", identity.number_field]
	if doctype == "Serial No":
		fields.append("batch_no")
	records = identity.get_records(item_code, [number.strip()], fields)
	return records[0] if records else {}


@frappe.whitelist()
def get_serial_batch_numbers(
	item_code: str, doctype: Literal["Serial No", "Batch"], names: str | list[str]
) -> dict[str, str]:
	frappe.has_permission("Item", "select", doc=item_code, throw=True)
	return SerialBatchIdentity(doctype).get_number_map(frappe.parse_json(names), item_code=item_code)


@frappe.whitelist()
def is_duplicate_serial_no(bundle_id: str, serial_no: str):
	return frappe.db.exists("Serial and Batch Entry", {"parent": bundle_id, "serial_no": serial_no})
