# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.services.goods_inward import make_receipt_from_goods_inward_note
from erpnext.tests.utils import ERPNextTestSuite


def make_inward_location(name="_Test Factory Gate"):
	if not frappe.db.exists("Inward Location", name):
		frappe.get_doc({"doctype": "Inward Location", "location_name": name}).insert(ignore_permissions=True)
	return name


def make_goods_inward_note(order, qty=None, submit=True):
	note = frappe.get_doc(
		{
			"doctype": "Goods Inward Note",
			"order_type": "Purchase Order",
			"order": order.name,
			"current_inward_location": make_inward_location(),
		}
	)
	note.get_items_from_order()
	if qty is not None:
		for row in note.items:
			row.qty = qty
	note.insert(ignore_permissions=True)
	if submit:
		note.submit()
	return note


class TestGoodsInwardNote(ERPNextTestSuite):
	def test_note_prefills_from_the_order_and_tracks_custody(self):
		item = make_item(properties={"is_stock_item": 1}).name
		order = create_purchase_order(item_code=item, qty=10)

		note = make_goods_inward_note(order)
		self.assertEqual(note.supplier, order.supplier)
		self.assertEqual(len(note.items), 1)
		self.assertEqual(note.items[0].qty, 10)
		self.assertEqual(note.status, "In Custody")

		# the consignment moves: the same note follows it
		note.db_set("current_inward_location", make_inward_location("_Test Customs Area"))

		# a second note for the same order only offers what no open note holds
		second = frappe.get_doc(
			{
				"doctype": "Goods Inward Note",
				"order_type": "Purchase Order",
				"order": order.name,
				"current_inward_location": make_inward_location(),
			}
		)
		second.get_items_from_order()
		self.assertEqual(second.items, [])

	def test_receipt_is_capped_to_custody_and_books_back(self):
		item = make_item(properties={"is_stock_item": 1}).name
		order = create_purchase_order(item_code=item, qty=10)
		note = make_goods_inward_note(order, qty=6)

		receipt = make_receipt_from_goods_inward_note(note.name)
		self.assertEqual(len(receipt.items), 1)
		self.assertEqual(receipt.items[0].qty, 6)
		self.assertEqual(receipt.items[0].goods_inward_note, note.name)

		# receiving more than custody holds is refused
		receipt.items[0].qty = 7
		receipt.items[0].received_qty = 7
		receipt.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, receipt.submit)

		receipt.reload()
		receipt.items[0].qty = 4
		receipt.items[0].received_qty = 4
		receipt.save(ignore_permissions=True)
		receipt.submit()

		note.reload()
		self.assertEqual(note.items[0].received_qty, 4)
		self.assertEqual(note.status, "Partially Received")

		# the rest follows on a second receipt; the note closes
		second = make_receipt_from_goods_inward_note(note.name)
		self.assertEqual(second.items[0].qty, 2)
		second.insert(ignore_permissions=True)
		second.submit()
		note.reload()
		self.assertEqual(note.status, "Received")

		# cancelling a receipt gives the quantity back to custody
		second.cancel()
		note.reload()
		self.assertEqual(note.items[0].received_qty, 4)
		self.assertEqual(note.status, "Partially Received")

	def test_returned_quantity_shrinks_what_is_receivable(self):
		item = make_item(properties={"is_stock_item": 1}).name
		order = create_purchase_order(item_code=item, qty=5)
		note = make_goods_inward_note(order)

		# two units go back with the truck
		note.items[0].returned_qty = 2
		note.save(ignore_permissions=True)

		receipt = make_receipt_from_goods_inward_note(note.name)
		self.assertEqual(receipt.items[0].qty, 3)

		# returned plus received may never exceed what arrived
		note.reload()
		note.items[0].returned_qty = 6
		self.assertRaises(frappe.ValidationError, note.save)

	def test_arrivals_may_not_overshoot_the_order(self):
		item = make_item(properties={"is_stock_item": 1}).name
		order = create_purchase_order(item_code=item, qty=5)
		note = make_goods_inward_note(order)

		# a duplicated note would claim the same five units twice
		duplicate = frappe.copy_doc(note)
		self.assertRaises(frappe.ValidationError, duplicate.insert)

		# two rejects go back with the truck — their replacement may arrive
		note.reload()
		note.items[0].returned_qty = 2
		note.save(ignore_permissions=True)
		replacement = make_goods_inward_note(order)
		self.assertEqual(replacement.items[0].qty, 2)

		# but a single unit on top of that overshoots the order again
		excess = frappe.get_doc(
			{
				"doctype": "Goods Inward Note",
				"order_type": "Purchase Order",
				"order": order.name,
				"current_inward_location": make_inward_location(),
				"items": [
					{
						"item_code": item,
						"qty": 1,
						"uom": frappe.db.get_value("Item", item, "stock_uom"),
					}
				],
			}
		)
		self.assertRaises(frappe.ValidationError, excess.insert)

	def test_inspection_offers_only_what_is_in_custody(self):
		from erpnext.controllers.stock_controller import check_item_quality_inspection

		item = make_item(properties={"is_stock_item": 1}).name
		order = create_purchase_order(item_code=item, qty=5)
		note = make_goods_inward_note(order)
		note.items[0].returned_qty = 2
		note.save(ignore_permissions=True)
		note.reload()

		# the dialog proposes what may still be inspected, not what arrived
		rows = check_item_quality_inspection("Goods Inward Note", note.docstatus, [note.items[0].as_dict()])
		self.assertEqual(rows[0]["qty"], 3)

		# and so does the inspection form itself
		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Goods Inward Note",
				"reference_name": note.name,
				"child_row_reference": note.items[0].name,
				"item_code": item,
			}
		)
		self.assertEqual(inspection.get_qty_under_inspection(), 3)

	def test_sample_may_not_exceed_what_is_in_custody(self):
		item = make_item(properties={"is_stock_item": 1}).name
		order = create_purchase_order(item_code=item, qty=5)
		note = make_goods_inward_note(order)
		note.items[0].returned_qty = 2
		note.save(ignore_permissions=True)

		# a sample of seven cannot describe the three units in custody
		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Goods Inward Note",
				"reference_name": note.name,
				"item_code": item,
				"manual_inspection": 1,
				"status": "Accepted",
				"sample_size": 7,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, inspection.submit)

		inspection.reload()
		inspection.sample_size = 3
		inspection.save(ignore_permissions=True)
		inspection.submit()

	def test_each_quantity_inspection_decides_in_batches(self):
		from erpnext.controllers.stock_controller import check_item_quality_inspection
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.services.test_quality_quarantine import unit_reading_rows

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Goods Inward Note",
				warehouse_role=None,
				quality_control_mode="Block",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		order = create_purchase_order(item_code=item.name, qty=4)
		note = make_goods_inward_note(order)

		def batch(unit_results):
			inspection = frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": "Goods Inward Note",
					"reference_name": note.name,
					"child_row_reference": note.items[0].name,
					"item_code": item.name,
					"inspection_basis": "Each Quantity",
					"unit_quantity": len(unit_results),
					"unit_readings": unit_reading_rows(unit_results),
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
				}
			)
			inspection.insert(ignore_permissions=True)
			return inspection

		# the first tranche decides two of the four units, rejecting one
		batch({1: ["Accepted"], 2: ["Rejected"]}).submit()

		# half decided: the receipt still waits for the rest
		self.assertRaises(frappe.ValidationError, make_receipt_from_goods_inward_note, note.name)

		# the dialog keeps offering the row, with the undecided remainder
		note.reload()
		rows = check_item_quality_inspection("Goods Inward Note", note.docstatus, [note.items[0].as_dict()])
		self.assertEqual(rows[0]["qty"], 2)
		self.assertFalse(rows[0]["quality_inspection"])

		# no batch may decide more units than remain undecided
		oversized = batch({1: ["Accepted"], 2: ["Accepted"], 3: ["Accepted"]})
		self.assertRaises(frappe.ValidationError, oversized.submit)
		oversized.reload()
		oversized.delete()

		batch({1: ["Accepted"], 2: ["Accepted"]}).submit()

		# fully decided: the verdicts pool across batches — three accepted, one rejected
		receipt = make_receipt_from_goods_inward_note(note.name)
		row = receipt.items[0]
		self.assertEqual(row.received_qty, 4)
		self.assertEqual(row.qty, 3)
		self.assertEqual(row.rejected_qty, 1)

	def test_sample_after_batches_covers_only_the_remainder(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.services.test_quality_quarantine import unit_reading_rows

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Goods Inward Note",
				warehouse_role=None,
				quality_control_mode="Block",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		order = create_purchase_order(item_code=item.name, qty=3)
		note = make_goods_inward_note(order)

		# one unit decided per-unit; it passes
		first = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Goods Inward Note",
				"reference_name": note.name,
				"child_row_reference": note.items[0].name,
				"item_code": item.name,
				"inspection_basis": "Each Quantity",
				"unit_quantity": 1,
				"unit_readings": unit_reading_rows({1: ["Accepted"]}),
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		first.insert(ignore_permissions=True)
		first.submit()

		# the inspector fails the rest on a sample — without naming the row
		sample = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Goods Inward Note",
				"reference_name": note.name,
				"item_code": item.name,
				"inspection_basis": "Sample",
				"manual_inspection": 1,
				"status": "Rejected",
				"sample_size": 3,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		sample.insert(ignore_permissions=True)
		# it binds to the same row, the earlier inspection notwithstanding
		self.assertEqual(sample.child_row_reference, note.items[0].name)
		# and three sampled units cannot describe the two undecided ones
		self.assertRaises(frappe.ValidationError, sample.submit)

		sample.reload()
		sample.sample_size = 2
		sample.save(ignore_permissions=True)
		sample.submit()

		# the rejection covers only the remainder the sample decided
		receipt = make_receipt_from_goods_inward_note(note.name)
		row = receipt.items[0]
		self.assertEqual(row.received_qty, 3)
		self.assertEqual(row.qty, 1)
		self.assertEqual(row.rejected_qty, 2)

	def test_block_trigger_gates_the_receipt_not_the_note(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Goods Inward Note",
				warehouse_role=None,
				quality_control_mode="Block",
			),
		)
		item.save()

		# arrival is a fact: the note submits with no inspection in sight
		order = create_purchase_order(item_code=item.name, qty=4)
		note = make_goods_inward_note(order)

		# but the goods may not become stock until the custody verdict is in
		self.assertRaises(frappe.ValidationError, make_receipt_from_goods_inward_note, note.name)

		# nor may a hand-built receipt slip past the gate
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

		sneak = make_purchase_receipt(order.name)
		sneak.items[0].goods_inward_note = note.name
		sneak.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, sneak.submit)
		sneak.reload()
		sneak.delete()

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Goods Inward Note",
				"reference_name": note.name,
				"item_code": item.name,
				"manual_inspection": 1,
				"status": "Accepted",
				"sample_size": 1,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()

		note.reload()
		self.assertEqual(note.items[0].quality_inspection, inspection.name)

		receipt = make_receipt_from_goods_inward_note(note.name)
		self.assertEqual(receipt.items[0].qty, 4)

	def test_custody_quarantine_is_refused(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Goods Inward Note",
				warehouse_role=None,
				quality_control_mode="Quarantine",
			),
		)
		self.assertRaises(frappe.ValidationError, item.save)

	def test_custody_rejection_rides_the_receipt_as_rejected_qty(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.services.test_quality_quarantine import unit_reading_rows
		from erpnext.stock.services.test_quality_warehouse import make_warehouse

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Goods Inward Note",
				warehouse_role=None,
				quality_control_mode="Block",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		order = create_purchase_order(item_code=item.name, qty=3)
		note = make_goods_inward_note(order)

		# inspected in custody, against the submitted note
		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Goods Inward Note",
				"reference_name": note.name,
				"item_code": item.name,
				"inspection_basis": "Each Quantity",
				"unit_quantity": 3,
				"unit_readings": unit_reading_rows({1: ["Accepted"], 2: ["Accepted"], 3: ["Rejected"]}),
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()
		note.reload()

		# the verdict prefills the split: the full delivery is received, the
		# rejected unit as rejected quantity bound for a Rejected warehouse
		receipt = make_receipt_from_goods_inward_note(note.name)
		row = receipt.items[0]
		self.assertEqual(row.received_qty, 3)
		self.assertEqual(row.qty, 2)
		self.assertEqual(row.rejected_qty, 1)

		rejects = row.rejected_warehouse or make_warehouse("_Test Custody Rejects", warehouse_type="Rejected")
		row.rejected_warehouse = rejects
		receipt.insert(ignore_permissions=True)
		receipt.submit()

		# everything left custody: accepted into stock, rejected into Rejected
		note.reload()
		self.assertEqual(note.items[0].received_qty, 3)
		self.assertEqual(note.status, "Received")
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_no": receipt.name, "warehouse": rejects, "is_cancelled": 0},
				"actual_qty",
			),
			1,
		)

		# a second receipt has nothing left to propose
		self.assertRaises(frappe.ValidationError, make_receipt_from_goods_inward_note, note.name)

	def test_custody_verdict_skips_requarantine_at_the_receipt(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.services.test_quality_quarantine import make_qc_warehouse

		qc = make_qc_warehouse("_Test QC Custody WH")
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Goods Inward Note",
				warehouse_role=None,
				quality_control_mode="Warn",
			),
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Quarantine",
				applicable_warehouse=qc,
			),
		)
		item.save()

		order = create_purchase_order(item_code=item.name, qty=2)
		note = make_goods_inward_note(order)

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Goods Inward Note",
				"reference_name": note.name,
				"item_code": item.name,
				"manual_inspection": 1,
				"status": "Accepted",
				"sample_size": 1,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()
		note.reload()

		# already decided in custody: the receipt is not routed to quarantine
		receipt = make_receipt_from_goods_inward_note(note.name)
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		self.assertNotEqual(receipt.items[0].warehouse, qc)
		self.assertEqual(
			frappe.get_all("Quality Control Lot", filters={"source_document": receipt.name}, pluck="name"),
			[],
		)

	def test_subcontracting_receipt_path(self):
		import copy

		from erpnext.controllers.tests.test_subcontracting_controller import (
			get_rm_items,
			get_subcontracting_order,
			make_bom_for_subcontracted_items,
			make_raw_materials,
			make_service_items,
			make_stock_in_entry,
			make_stock_transfer_entry,
			make_subcontracted_items,
			set_backflush_based_on,
		)

		set_backflush_based_on("BOM")
		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

		service_items = [
			{
				"warehouse": "_Test Warehouse - _TC",
				"item_code": "Subcontracted Service Item 1",
				"qty": 6,
				"rate": 100,
				"fg_item": "_Test FG Item",
				"fg_item_qty": 6,
			},
		]
		sco = get_subcontracting_order(service_items=service_items)
		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)
		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)

		# the job worker's truck arrives with the finished goods
		note = frappe.get_doc(
			{
				"doctype": "Goods Inward Note",
				"order_type": "Subcontracting Order",
				"order": sco.name,
				"current_inward_location": make_inward_location(),
			}
		)
		note.get_items_from_order()
		note.insert(ignore_permissions=True)
		note.submit()
		self.assertEqual(note.supplier, sco.supplier)
		self.assertEqual(note.items[0].item_code, "_Test FG Item")
		self.assertEqual(note.items[0].qty, 6)

		# the receipt comes through the order's own mapper: supplied items intact
		receipt = make_receipt_from_goods_inward_note(note.name)
		self.assertEqual(receipt.doctype, "Subcontracting Receipt")
		self.assertEqual(receipt.items[0].qty, 6)
		self.assertEqual(receipt.items[0].goods_inward_note, note.name)

		# partial receipt books back onto the note
		receipt.items[0].qty = 4
		receipt.items[0].received_qty = 4
		receipt.save(ignore_permissions=True)
		# raw materials backflush as usual: custody changes nothing downstream
		self.assertTrue(receipt.supplied_items)
		receipt.submit()
		note.reload()
		self.assertEqual(note.items[0].received_qty, 4)
		self.assertEqual(note.status, "Partially Received")

		# the remainder may not be exceeded
		second = make_receipt_from_goods_inward_note(note.name)
		self.assertEqual(second.items[0].qty, 2)
		second.items[0].qty = 3
		second.items[0].received_qty = 3
		second.save(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, second.submit)

		second.reload()
		second.items[0].qty = 2
		second.items[0].received_qty = 2
		second.save(ignore_permissions=True)
		second.submit()
		note.reload()
		self.assertEqual(note.status, "Received")

		# cancelling the receipt gives the quantity back to custody
		second.cancel()
		note.reload()
		self.assertEqual(note.items[0].received_qty, 4)
		self.assertEqual(note.status, "Partially Received")

	def test_goods_awaiting_receipt_report(self):
		from erpnext.stock.report.goods_awaiting_receipt.goods_awaiting_receipt import execute

		item = make_item(properties={"is_stock_item": 1}).name
		order = create_purchase_order(item_code=item, qty=7)
		note = make_goods_inward_note(order)

		_columns, rows = execute({"item_code": item})
		row = next(r for r in rows if r["goods_inward_note"] == note.name)
		self.assertEqual(row["awaiting_qty"], 7)
		self.assertEqual(row["current_inward_location"], "_Test Factory Gate")
