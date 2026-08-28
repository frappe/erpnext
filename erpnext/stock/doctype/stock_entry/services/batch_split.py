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
		parent_batches = self.get_parent_batches(input_batches, pieces)
		child_batches = self.make_child_batches(fg_row, parent_batches)
		self.attach_bundle(fg_row, child_batches)

	def is_applicable(self):
		self.weight_per_piece = 0.0
		if self.doc.purpose == "Repack":
			if not self.doc.stock_entry_type or not cint(
				frappe.get_cached_value("Stock Entry Type", self.doc.stock_entry_type, "batch_split")
			):
				return False

			self.weight_per_piece = flt(self.doc.weight_per_piece)
			return True

		if self.doc.purpose != "Manufacture" or not self.doc.job_card:
			return False

		details = frappe.db.get_value(
			"Job Card", self.doc.job_card, ["batch_split", "weight_per_piece"], as_dict=1
		)

		self.weight_per_piece = flt(details.weight_per_piece)
		return cint(details.batch_split) and self.weight_per_piece > 0

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

		item_details = frappe.get_cached_value(
			"Item", row.item_code, ["has_batch_no", "create_new_batch"], as_dict=1
		)
		if not item_details.has_batch_no or not item_details.create_new_batch:
			frappe.throw(
				_(
					"Row #{0}: The item {1} must have 'Has Batch No' and 'Automatically Create New Batch' enabled for the Batch Split operation."
				).format(row.idx, row.item_code)
			)

		return row

	def get_pieces(self, fg_row):
		if self.weight_per_piece <= 0:
			frappe.throw(
				_(
					"Please set the Weight Per Piece to split the produced quantity into batches in the Stock Entry {0}."
				).format(self.doc.name)
			)

		pieces = flt(fg_row.transfer_qty) / self.weight_per_piece
		if pieces < 1 or pieces != cint(pieces):
			frappe.throw(
				_(
					"Row #{0}: The quantity {1} of the Batch Split item {2} must be a multiple of the Weight Per Piece {3}."
				).format(fg_row.idx, fg_row.transfer_qty, fg_row.item_code, self.weight_per_piece)
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
		pool = [(batch_no, flt(qty)) for batch_no, qty in input_batches if flt(qty) > 0]
		capacities = [int(flt(qty / self.weight_per_piece, 6)) for _batch_no, qty in pool]

		if sum(capacities) < pieces:
			frappe.throw(
				_(
					"The batches consumed in the Stock Entry {0} can supply only {1} whole pieces of {2} units each, but {3} pieces are required. Reduce the finished quantity or consume larger batches."
				).format(self.doc.name, sum(capacities), self.weight_per_piece, pieces)
			)

		total_qty = sum(qty for _batch_no, qty in pool)
		shares = [pieces * qty / total_qty for _batch_no, qty in pool]
		counts = [min(int(share), capacity) for share, capacity in zip(shares, capacities, strict=False)]

		while sum(counts) < pieces:
			eligible = [i for i in range(len(pool)) if counts[i] < capacities[i]]
			index = min(eligible, key=lambda i: (counts[i] - shares[i], i))
			counts[index] += 1

		parents = []
		for (batch_no, _qty), count in zip(pool, counts, strict=False):
			parents.extend([batch_no] * count)

		return parents

	def make_child_batches(self, fg_row, parent_batches):
		batches = frappe._dict()
		for parent_batch in parent_batches:
			batch_no = make_batch(
				frappe._dict(
					{
						"item": fg_row.item_code,
						"parent_batch": parent_batch,
						"reference_doctype": self.doc.doctype,
						"reference_name": self.doc.name,
					}
				)
			)

			batches[batch_no] = self.weight_per_piece

		return batches

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
