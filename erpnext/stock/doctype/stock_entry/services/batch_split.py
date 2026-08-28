import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.doctype.batch.batch import get_available_batches, make_batch
from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from erpnext.stock.utils import get_combine_datetime


class BatchSplitFinishedGood:
	def __init__(self, doc):
		self.doc = doc

	def process(self):
		if not self.is_applicable():
			return

		fg_row = self.get_finished_good_row()
		pieces = self.get_pieces(fg_row)
		input_batches = self.get_input_batches()
		self.set_weight_per_piece(input_batches, pieces)
		parent_batches = self.get_parent_batches(input_batches, pieces)
		child_batches = self.make_child_batches(fg_row, parent_batches)
		self.attach_bundle(fg_row, child_batches)

	def is_applicable(self):
		self.weight_per_piece = 0.0
		if self.doc.purpose == "Repack":
			return self.doc.stock_entry_type and cint(
				frappe.get_cached_value("Stock Entry Type", self.doc.stock_entry_type, "batch_split")
			)

		if self.doc.purpose != "Manufacture" or not self.doc.job_card:
			return False

		details = frappe.db.get_value(
			"Job Card", self.doc.job_card, ["batch_split", "weight_per_piece"], as_dict=1
		)

		self.weight_per_piece = flt(details.weight_per_piece)
		return cint(details.batch_split) and self.weight_per_piece > 0

	def set_weight_per_piece(self, input_batches, pieces):
		if not self.weight_per_piece:
			self.weight_per_piece = sum(flt(qty) for _batch_no, qty in input_batches) / pieces

	def get_finished_good_row(self):
		fg_rows = [
			row
			for row in self.doc.items
			if row.is_finished_item and not row.secondary_item_type and not row.is_legacy_scrap_item
		]

		if len(fg_rows) != 1:
			frappe.throw(
				_("The Batch Split entry {0} must have exactly one finished good row.").format(self.doc.name)
			)

		row = fg_rows[0]
		if row.serial_and_batch_bundle:
			frappe.throw(
				_(
					"Row #{0}: Remove the Serial and Batch Bundle as the batches for the Batch Split item {1} are created automatically."
				).format(row.idx, row.item_code)
			)

		if not frappe.get_cached_value("Item", row.item_code, "has_batch_no"):
			frappe.throw(
				_(
					"Row #{0}: The item {1} must have 'Has Batch No' enabled for the Batch Split operation."
				).format(row.idx, row.item_code)
			)

		return row

	def get_pieces(self, fg_row):
		pieces = flt(fg_row.transfer_qty)
		if pieces <= 0 or pieces != cint(pieces):
			frappe.throw(
				_(
					"Row #{0}: The quantity {1} of the Batch Split item {2} must be a whole number of pieces."
				).format(fg_row.idx, pieces, fg_row.item_code)
			)

		return cint(pieces)

	def get_input_batches(self):
		input_rows = [row for row in self.doc.items if self.is_batch_input_row(row)]

		if not input_rows:
			frappe.throw(
				_(
					"The Batch Split operation requires a batch tracked raw material to be consumed in the Stock Entry {0}."
				).format(self.doc.name)
			)

		item_codes = {row.item_code for row in input_rows}
		if len(item_codes) > 1:
			frappe.throw(
				_(
					"The Batch Split entry {0} must consume exactly one batch tracked raw material, found {1} ({2})."
				).format(self.doc.name, len(item_codes), ", ".join(sorted(item_codes)))
			)

		batches = []
		for row in input_rows:
			batches.extend(self.get_row_batches(row))

		if not batches:
			frappe.throw(
				_(
					"The Batch Split operation requires a batch tracked raw material to be consumed in the Stock Entry {0}."
				).format(self.doc.name)
			)

		return batches

	def is_batch_input_row(self, row):
		if row.is_finished_item or not row.s_warehouse:
			return False

		if row.secondary_item_type or row.is_legacy_scrap_item:
			return False

		return bool(frappe.get_cached_value("Item", row.item_code, "has_batch_no"))

	def get_row_batches(self, row):
		if row.serial_and_batch_bundle:
			entries = frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": row.serial_and_batch_bundle, "batch_no": ("is", "set")},
				fields=["batch_no", "qty"],
				order_by="idx",
			)

			return [(d.batch_no, abs(flt(d.qty))) for d in entries]

		if row.batch_no:
			return [(row.batch_no, flt(row.transfer_qty))]

		return self.get_available_row_batches(row)

	def get_available_row_batches(self, row):
		available = get_available_batches(
			frappe._dict(
				{
					"item_code": row.item_code,
					"warehouse": row.s_warehouse,
					"posting_datetime": get_combine_datetime(self.doc.posting_date, self.doc.posting_time),
					"based_on": frappe.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
				}
			)
		)

		batches = []
		remaining = flt(row.transfer_qty)
		for batch_no, qty in available.items():
			if remaining <= 0:
				break

			if flt(qty) <= 0:
				continue

			taken = min(flt(qty), remaining)
			batches.append((batch_no, taken))
			remaining -= taken

		return batches

	def get_parent_batches(self, input_batches, pieces):
		pool = [[batch_no, flt(qty)] for batch_no, qty in input_batches if flt(qty) > 0]
		precision = frappe.get_precision("Serial and Batch Entry", "qty")
		parents = []
		index = 0

		for _piece in range(pieces):
			shares = {}
			remaining = self.weight_per_piece
			while remaining > 0 and index < len(pool):
				taken = min(pool[index][1], remaining)
				if taken > 0:
					shares[pool[index][0]] = flt(shares.get(pool[index][0], 0.0) + taken, precision)

				pool[index][1] = flt(pool[index][1] - taken, precision)
				remaining = flt(remaining - taken, precision)
				if pool[index][1] <= 0:
					index += 1

			parents.append(self.get_majority_batch(shares) or pool[-1][0])

		return parents

	@staticmethod
	def get_majority_batch(shares):
		majority_batch = None
		majority_share = 0.0
		for batch_no, share in shares.items():
			if share >= majority_share:
				majority_batch, majority_share = batch_no, share

		return majority_batch

	def make_child_batches(self, fg_row, parent_batches):
		batches = frappe._dict()
		next_index = {}
		for parent_batch in parent_batches:
			batch_no = self.insert_child_batch(fg_row, parent_batch, next_index)
			batches[batch_no] = 1

		return batches

	def insert_child_batch(self, fg_row, parent_batch, next_index):
		index = next_index.get(parent_batch) or cint(frappe.db.count("Batch", {"parent_batch": parent_batch}))

		while True:
			index += 1
			batch_id = f"{parent_batch}-{index}"
			if frappe.db.exists("Batch", batch_id):
				continue

			frappe.db.savepoint("insert_child_batch")
			try:
				batch_no = self.make_child_batch(fg_row, parent_batch, batch_id)
			except frappe.DuplicateEntryError:
				frappe.db.rollback(save_point="insert_child_batch")
				continue

			next_index[parent_batch] = index
			return batch_no

	def make_child_batch(self, fg_row, parent_batch, batch_id):
		return make_batch(
			frappe._dict(
				{
					"item": fg_row.item_code,
					"parent_batch": parent_batch,
					"batch_id": batch_id,
					"reference_doctype": self.doc.doctype,
					"reference_name": self.doc.name,
				}
			)
		)

	def attach_bundle(self, fg_row, batches):
		bundle = SerialBatchCreation(
			{
				"item_code": fg_row.item_code,
				"warehouse": fg_row.t_warehouse,
				"posting_datetime": get_combine_datetime(self.doc.posting_date, self.doc.posting_time),
				"voucher_type": self.doc.doctype,
				"voucher_detail_no": fg_row.name,
				"qty": sum(batches.values()),
				"batches": batches,
				"type_of_transaction": "Inward",
				"company": self.doc.company,
				"do_not_submit": True,
			}
		).make_serial_and_batch_bundle()

		fg_row.serial_and_batch_bundle = bundle.name
		fg_row.use_serial_batch_fields = 0
		fg_row.batch_no = None


def delete_unused_child_batches(doc):
	own_bundles = set(
		frappe.get_all(
			"Serial and Batch Bundle",
			filters={"voucher_type": doc.doctype, "voucher_no": doc.name},
			pluck="name",
		)
	)

	for bundle_name, batch_nos in get_bundle_wise_child_batches(doc).items():
		if any(is_batch_used_outside(batch_no, own_bundles) for batch_no in batch_nos):
			continue

		delete_child_bundle(doc, bundle_name)
		for batch_no in batch_nos:
			frappe.delete_doc("Batch", batch_no, force=True, ignore_permissions=True)


def delete_child_bundle(doc, bundle_name):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	(
		frappe.qb.update(sle)
		.set(sle.serial_and_batch_bundle, None)
		.where(
			(sle.voucher_type == doc.doctype)
			& (sle.voucher_no == doc.name)
			& (sle.serial_and_batch_bundle == bundle_name)
		)
	).run()

	frappe.delete_doc("Serial and Batch Bundle", bundle_name, force=True, ignore_permissions=True)


def is_batch_used_outside(batch_no, own_bundles):
	from frappe.model.delete_doc import get_dynamic_linked_docs, get_linked_docs

	batch_doc = frappe.get_doc("Batch", batch_no)
	for link in get_linked_docs(batch_doc) + get_dynamic_linked_docs(batch_doc):
		if (
			link["reference_doctype"] == "Serial and Batch Bundle"
			and link["reference_docname"] in own_bundles
		):
			continue

		return True

	return False


def get_bundle_wise_child_batches(doc):
	bundle = frappe.qb.DocType("Serial and Batch Bundle")
	entry = frappe.qb.DocType("Serial and Batch Entry")
	batch = frappe.qb.DocType("Batch")

	data = (
		frappe.qb.from_(bundle)
		.inner_join(entry)
		.on(entry.parent == bundle.name)
		.inner_join(batch)
		.on(batch.name == entry.batch_no)
		.select(bundle.name.as_("bundle_name"), batch.name.as_("batch_no"))
		.distinct()
		.where(
			(bundle.voucher_type == doc.doctype)
			& (bundle.voucher_no == doc.name)
			& (bundle.type_of_transaction == "Inward")
			& (batch.parent_batch.isnotnull())
		)
	).run(as_dict=True)

	bundle_wise_batches = {}
	for row in data:
		bundle_wise_batches.setdefault(row.bundle_name, []).append(row.batch_no)

	return bundle_wise_batches
