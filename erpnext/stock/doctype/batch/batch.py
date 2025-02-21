# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections import OrderedDict, defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname, revert_series_if_last
from frappe.query_builder.functions import CurDate, Sum
from frappe.utils import cint, flt, get_link_to_form
from frappe.utils.data import add_days
from frappe.utils.jinja import render_template


class UnableToSelectBatchError(frappe.ValidationError):
	pass


def get_name_from_hash():
	"""
	Get a name for a Batch by generating a unique hash.
	:return: The hash that was generated.
	"""
	temp = None
	while not temp:
		temp = frappe.generate_hash()[:7].upper()
		if frappe.db.exists("Batch", temp):
			temp = None

	return temp


def batch_uses_naming_series():
	"""
	Verify if the Batch is to be named using a naming series
	:return: bool
	"""
	use_naming_series = cint(frappe.db.get_single_value("Stock Settings", "use_naming_series"))
	return bool(use_naming_series)


def _get_batch_prefix():
	"""
	Get the naming series prefix set in Stock Settings.

	It does not do any sanity checks so make sure to use it after checking if the Batch
	is set to use naming series.
	:return: The naming series.
	"""
	naming_series_prefix = frappe.db.get_single_value("Stock Settings", "naming_series_prefix")
	if not naming_series_prefix:
		naming_series_prefix = "BATCH-"

	return naming_series_prefix


def _make_naming_series_key(prefix):
	"""
	Make naming series key for a Batch.

	Naming series key is in the format [prefix].[#####]
	:param prefix: Naming series prefix gotten from Stock Settings
	:return: The derived key. If no prefix is given, an empty string is returned
	"""
	if not str(prefix):
		return ""
	else:
		return prefix.upper() + ".#####"


def get_batch_naming_series():
	"""
	Get naming series key for a Batch.

	Naming series key is in the format [prefix].[#####]
	:return: The naming series or empty string if not available
	"""
	series = ""
	if batch_uses_naming_series():
		prefix = _get_batch_prefix()
		key = _make_naming_series_key(prefix)
		series = key

	return series


class Batch(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch_id: DF.Data
		batch_qty: DF.Float
		description: DF.SmallText | None
		disabled: DF.Check
		expiry_date: DF.Date | None
		image: DF.AttachImage | None
		item: DF.Link
		item_name: DF.Data | None
		manufacturing_date: DF.Date | None
		parent_batch: DF.Link | None
		produced_qty: DF.Float
		qty_to_produce: DF.Float
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		stock_uom: DF.Link | None
		supplier: DF.Link | None
		use_batchwise_valuation: DF.Check
	# end: auto-generated types

	def autoname(self):
		"""Generate random ID for batch if not specified"""

		if self.batch_id:
			self.name = self.batch_id
			return

		create_new_batch, batch_number_series = frappe.db.get_value(
			"Item", self.item, ["create_new_batch", "batch_number_series"]
		)

		if not create_new_batch:
			frappe.throw(_("Batch ID is mandatory"), frappe.MandatoryError)

		while not self.batch_id:
			if batch_number_series:
				self.batch_id = make_autoname(batch_number_series, doc=self)
			elif batch_uses_naming_series():
				self.batch_id = self.get_name_from_naming_series()
			else:
				self.batch_id = get_name_from_hash()

			# User might have manually created a batch with next number
			if frappe.db.exists("Batch", self.batch_id):
				self.batch_id = None

		self.name = self.batch_id

	def onload(self):
		self.image = frappe.db.get_value("Item", self.item, "image")

	def after_delete(self):
		revert_series_if_last(get_batch_naming_series(), self.name)

	def validate(self):
		self.item_has_batch_enabled()
		self.set_batchwise_valuation()

	def item_has_batch_enabled(self):
		if frappe.db.get_value("Item", self.item, "has_batch_no") == 0:
			frappe.throw(_("The selected item cannot have Batch"))

	def set_batchwise_valuation(self):
		if self.is_new():
			if frappe.db.get_single_value("Stock Settings", "do_not_use_batchwise_valuation"):
				self.use_batchwise_valuation = 0
				return

			self.use_batchwise_valuation = 1

	def before_save(self):
		self.set_expiry_date()

	def set_expiry_date(self):
		has_expiry_date, shelf_life_in_days = frappe.db.get_value(
			"Item", self.item, ["has_expiry_date", "shelf_life_in_days"]
		)

		if not self.expiry_date and has_expiry_date and shelf_life_in_days:
			if (
				not self.manufacturing_date
				and self.reference_doctype in ["Stock Entry", "Purchase Receipt", "Purchase Invoice"]
				and self.reference_name
			):
				self.manufacturing_date = frappe.db.get_value(
					self.reference_doctype, self.reference_name, "posting_date"
				)

			if self.manufacturing_date:
				self.expiry_date = add_days(self.manufacturing_date, shelf_life_in_days)

		if has_expiry_date and not self.expiry_date:
			frappe.throw(
				msg=_("Please set {0} for Batched Item {1}, which is used to set {2} on Submit.").format(
					frappe.bold(_("Shelf Life in Days")),
					get_link_to_form("Item", self.item),
					frappe.bold(_("Batch Expiry Date")),
				),
				title=_("Expiry Date Mandatory"),
			)

	def get_name_from_naming_series(self):
		"""
		Get a name generated for a Batch from the Batch's naming series.
		:return: The string that was generated.
		"""
		naming_series_prefix = _get_batch_prefix()
		# validate_template(naming_series_prefix)
		naming_series_prefix = render_template(str(naming_series_prefix), self.__dict__)
		key = _make_naming_series_key(naming_series_prefix)
		name = make_autoname(key)

		return name


@frappe.whitelist()
def get_batch_qty(
	batch_no=None,
	warehouse=None,
	item_code=None,
	posting_date=None,
	posting_time=None,
	ignore_voucher_nos=None,
	for_stock_levels=False,
	consider_negative_batches=False,
):
	"""Returns batch actual qty if warehouse is passed,
	        or returns dict of qty by warehouse if warehouse is None

	The user must pass either batch_no or batch_no + warehouse or item_code + warehouse

	:param batch_no: Optional - give qty for this batch no
	:param warehouse: Optional - give qty for this warehouse
	:param item_code: Optional - give qty for this item
	:param for_stock_levels: True consider expired batches"""

	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_auto_batch_nos,
	)

	batchwise_qty = defaultdict(float)
	kwargs = frappe._dict(
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"posting_date": posting_date,
			"posting_time": posting_time,
			"batch_no": batch_no,
			"ignore_voucher_nos": ignore_voucher_nos,
			"for_stock_levels": for_stock_levels,
			"consider_negative_batches": consider_negative_batches,
		}
	)

	batches = get_auto_batch_nos(kwargs)

	if not (batch_no and warehouse):
		return batches

	for batch in batches:
		batchwise_qty[batch.get("batch_no")] += batch.get("qty")

	return batchwise_qty[batch_no]


@frappe.whitelist()
def get_batches_by_oldest(item_code, warehouse):
	"""Returns the oldest batch and qty for the given item_code and warehouse"""
	batches = get_batch_qty(item_code=item_code, warehouse=warehouse)
	batches_dates = [[batch, frappe.get_value("Batch", batch.batch_no, "expiry_date")] for batch in batches]
	batches_dates.sort(key=lambda tup: tup[1])
	return batches_dates


@frappe.whitelist()
def split_batch(batch_no: str, item_code: str, warehouse: str, qty: float, new_batch_id: str | None = None):
	"""Split the batch into a new batch"""
	batch = frappe.get_doc(dict(doctype="Batch", item=item_code, batch_id=new_batch_id)).insert()
	qty = flt(qty)

	company = frappe.db.get_value("Warehouse", warehouse, "company")

	from_bundle_id = make_batch_bundle(
		item_code=item_code,
		warehouse=warehouse,
		batches=frappe._dict({batch_no: qty}),
		company=company,
		type_of_transaction="Outward",
		qty=qty,
	)

	to_bundle_id = make_batch_bundle(
		item_code=item_code,
		warehouse=warehouse,
		batches=frappe._dict({batch.name: qty}),
		company=company,
		type_of_transaction="Inward",
		qty=qty,
	)

	stock_entry = frappe.get_doc(
		dict(
			doctype="Stock Entry",
			purpose="Repack",
			company=company,
			items=[
				dict(
					item_code=item_code,
					qty=qty,
					s_warehouse=warehouse,
					serial_and_batch_bundle=from_bundle_id,
				),
				dict(
					item_code=item_code, qty=qty, t_warehouse=warehouse, serial_and_batch_bundle=to_bundle_id
				),
			],
		)
	)
	stock_entry.set_stock_entry_type()
	stock_entry.insert()
	stock_entry.submit()

	return batch.name


def make_batch_bundle(
	item_code: str,
	warehouse: str,
	batches: dict[str, float],
	company: str,
	type_of_transaction: str,
	qty: float,
):
	from frappe.utils import nowtime, today

	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	return (
		SerialBatchCreation(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_date": today(),
				"posting_time": nowtime(),
				"voucher_type": "Stock Entry",
				"qty": qty,
				"type_of_transaction": type_of_transaction,
				"company": company,
				"batches": batches,
				"do_not_submit": True,
			}
		)
		.make_serial_and_batch_bundle()
		.name
	)


def get_batches(item_code, warehouse, qty=1, throw=False, serial_no=None):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	batch = frappe.qb.DocType("Batch")
	sle = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(batch)
		.join(sle)
		.on(batch.batch_id == sle.batch_no)
		.select(
			batch.batch_id,
			Sum(sle.actual_qty).as_("qty"),
		)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.is_cancelled == 0)
			& ((batch.expiry_date >= CurDate()) | (batch.expiry_date.isnull()))
		)
		.groupby(batch.batch_id)
		.orderby(batch.expiry_date, batch.creation)
	)

	if serial_no and frappe.get_cached_value("Item", item_code, "has_batch_no"):
		serial_nos = get_serial_nos(serial_no)
		batches = frappe.get_all(
			"Serial No",
			fields=["distinct batch_no"],
			filters={"item_code": item_code, "warehouse": warehouse, "name": ("in", serial_nos)},
		)

		if not batches:
			validate_serial_no_with_batch(serial_nos, item_code)

		if batches and len(batches) > 1:
			return []

		query = query.where(batch.name == batches[0].batch_no)

	return query.run(as_dict=True)


def validate_serial_no_with_batch(serial_nos, item_code):
	if frappe.get_cached_value("Serial No", serial_nos[0], "item_code") != item_code:
		frappe.throw(
			_("The serial no {0} does not belong to item {1}").format(
				get_link_to_form("Serial No", serial_nos[0]), get_link_to_form("Item", item_code)
			)
		)

	serial_no_link = ",".join(get_link_to_form("Serial No", sn) for sn in serial_nos)

	message = "Serial Nos" if len(serial_nos) > 1 else "Serial No"
	frappe.throw(_("There is no batch found against the {0}: {1}").format(message, serial_no_link))


def make_batch(kwargs):
	if frappe.db.get_value("Item", kwargs.item, "has_batch_no"):
		kwargs.doctype = "Batch"
		return frappe.get_doc(kwargs).insert().name


@frappe.whitelist()
def get_pos_reserved_batch_qty(filters):
	import json

	if isinstance(filters, str):
		filters = json.loads(filters)

	p = frappe.qb.DocType("POS Invoice").as_("p")
	item = frappe.qb.DocType("POS Invoice Item").as_("item")
	sum_qty = frappe.query_builder.functions.Sum(item.stock_qty).as_("qty")

	reserved_batch_qty = (
		frappe.qb.from_(p)
		.from_(item)
		.select(sum_qty)
		.where(
			(p.name == item.parent)
			& (p.consolidated_invoice.isnull())
			& (p.status != "Consolidated")
			& (p.docstatus == 1)
			& (item.docstatus == 1)
			& (item.item_code == filters.get("item_code"))
			& (item.warehouse == filters.get("warehouse"))
			& (item.batch_no == filters.get("batch_no"))
		)
		.run()
	)

	flt_reserved_batch_qty = flt(reserved_batch_qty[0][0])
	return flt_reserved_batch_qty


def get_available_batches(kwargs):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_auto_batch_nos,
	)

	batchwise_qty = OrderedDict()

	batches = get_auto_batch_nos(kwargs)
	for batch in batches:
		key = batch.get("batch_no")
		if kwargs.get("based_on_warehouse"):
			key = (batch.get("batch_no"), batch.get("warehouse"))

		if key not in batchwise_qty:
			batchwise_qty[key] = batch.get("qty")
		else:
			batchwise_qty[key] += batch.get("qty")

	return batchwise_qty


def get_batch_no(bundle_id):
	from erpnext.stock.serial_batch_bundle import get_batch_nos

	batches = defaultdict(float)

	for batch_id, d in get_batch_nos(bundle_id).items():
		batches[batch_id] += abs(d.get("qty"))

	return batches
