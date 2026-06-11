# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.services.test_quality_warehouse import ensure_quality_warehouse_type, make_warehouse
from erpnext.tests.utils import ERPNextTestSuite

REAL_WH = "_Test Warehouse - _TC"


def make_qc_warehouse(name="_Test QC Mint WH"):
	ensure_quality_warehouse_type()
	return make_warehouse(name, warehouse_type="Quality")


def make_quarantine_item(qc_warehouse, document_type="Stock Entry"):
	"""An item whose Quarantine trigger marks this Quality Control warehouse as
	its quarantine destination, so receiving it there is a legitimate flow."""
	from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

	item = make_item(properties={"is_stock_item": 1})
	item.append(
		"quality_triggers",
		trigger_row(
			document_type=document_type,
			warehouse_role="Inbound" if document_type == "Stock Entry" else None,
			quality_control_mode="Quarantine",
			applicable_warehouse=qc_warehouse,
		),
	)
	item.save()
	return item.name


def quality_control_lots_for(source_name, source_doctype="Stock Entry"):
	return frappe.get_all(
		"Quality Control Lot",
		filters={"source_document_type": source_doctype, "source_document": source_name},
		fields=["name", "item_code", "received_qty", "quality_warehouse", "status"],
	)


def submit_inspection_for_lot(
	lot_name, status="Accepted", reading_bundle=None, manual_inspection=0, inspection_basis=None
):
	lot = frappe.get_doc("Quality Control Lot", lot_name)
	inspection = frappe.get_doc(
		{
			"doctype": "Quality Inspection",
			"inspection_type": "Incoming",
			"reference_type": "Quality Control Lot",
			"reference_name": lot.name,
			"item_code": lot.item_code,
			"batch_no": lot.batch_no,
			"sample_size": 1,
			"report_date": nowdate(),
			"inspected_by": frappe.session.user,
			"manual_inspection": manual_inspection,
			"status": status,
			"reading_bundle": reading_bundle,
			"inspection_basis": inspection_basis,
		}
	)
	if not manual_inspection and not reading_bundle:
		# submission demands recorded readings; one verdict-carrying row
		if not frappe.db.exists("Quality Inspection Parameter", "_Test Lot Verdict"):
			frappe.get_doc(
				{"doctype": "Quality Inspection Parameter", "parameter": "_Test Lot Verdict"}
			).insert(ignore_permissions=True)
		inspection.append(
			"readings",
			{
				"specification": "_Test Lot Verdict",
				"numeric": 0,
				"value": "OK",
				"reading_value": "OK" if status == "Accepted" else "NOT OK",
			},
		)
	inspection.insert(ignore_permissions=True)
	inspection.submit()
	return inspection


def make_release(lot_name, qty, to_warehouse, batch_no=None, serial_no=None):
	lot = frappe.get_doc("Quality Control Lot", lot_name)
	release = frappe.new_doc("Stock Entry")
	release.purpose = "Quality Control Release"
	release.stock_entry_type = "Quality Control Release"
	release.company = "_Test Company"
	release.quality_control_lot = lot.name
	release.append(
		"items",
		{
			"item_code": lot.item_code,
			"qty": qty,
			"s_warehouse": lot.quality_warehouse,
			"t_warehouse": to_warehouse,
			"batch_no": batch_no,
			"serial_no": serial_no,
			"use_serial_batch_fields": 1 if (batch_no or serial_no) else 0,
		},
	)
	release.insert()
	release.submit()
	return release


def get_qty(item_code, warehouse):
	return frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0.0


class TestQualityQuarantine(ERPNextTestSuite):
	def test_quality_control_lot_minted_on_receipt_into_qc_warehouse(self):
		from erpnext.stock.doctype.quality_inspection.quality_inspection import item_query

		qc = make_qc_warehouse()
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=7, to_warehouse=qc, purpose="Material Receipt", rate=100)

		lots = quality_control_lots_for(se.name)
		self.assertEqual(len(lots), 1)
		self.assertEqual(lots[0].received_qty, 7)
		self.assertEqual(lots[0].quality_warehouse, qc)
		self.assertEqual(lots[0].status, "Under Inspection")

		# the inspection form's item link query resolves a lot to its single item
		# (a lot has no items child table like the stock vouchers do)
		result = item_query(
			"Item",
			"",
			"name",
			0,
			20,
			{"reference_doctype": "Quality Control Lot", "reference_name": lots[0].name},
		)
		self.assertEqual(result[0][0], item)

	def test_routing_carries_a_manually_built_bundle(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		qc = make_qc_warehouse("_Test QC Carry WH")
		store = make_warehouse("_Test QC Carry Store", quality_warehouse=qc)

		item = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "QCCB.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
			),
		)
		item.save()

		batch = frappe.get_doc(
			{"doctype": "Batch", "item": item.name, "batch_id": "_Test QC Carry Batch"}
		).insert(ignore_permissions=True)

		# the user builds the bundle for the store before routing redirects the row
		bundle = SerialBatchCreation(
			{
				"item_code": item.name,
				"warehouse": store,
				"voucher_type": "Stock Entry",
				"qty": 2,
				"actual_qty": 2,
				"batches": frappe._dict({batch.name: 2}),
				"type_of_transaction": "Inward",
				"company": "_Test Company",
				"do_not_submit": True,
			}
		).make_serial_and_batch_bundle()

		receipt = frappe.new_doc("Stock Entry")
		receipt.purpose = "Material Receipt"
		receipt.stock_entry_type = "Material Receipt"
		receipt.company = "_Test Company"
		receipt.append(
			"items",
			{
				"item_code": item.name,
				"qty": 2,
				"t_warehouse": store,
				"basic_rate": 100,
				"serial_and_batch_bundle": bundle.name,
			},
		)
		receipt.insert()
		receipt.submit()

		# routing redirected the row and carried the bundle with it
		self.assertEqual(receipt.items[0].t_warehouse, qc)
		self.assertEqual(frappe.db.get_value("Serial and Batch Bundle", bundle.name, "warehouse"), qc)
		lots = quality_control_lots_for(receipt.name)
		self.assertEqual(lots[0].quality_warehouse, qc)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lots[0].name, "batch_no"), batch.name)

	def test_multi_batch_row_mints_one_lot_per_batch(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		qc = make_qc_warehouse("_Test QC Multi Batch WH")
		item = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "QCMB2.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				applicable_warehouse=qc,
			),
		)
		item.save()

		batches = {}
		for batch_id, qty in (("_Test QC Multi One", 2), ("_Test QC Multi Two", 3)):
			batch = frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": batch_id}).insert(
				ignore_permissions=True
			)
			batches[batch.name] = qty

		bundle = SerialBatchCreation(
			{
				"item_code": item.name,
				"warehouse": qc,
				"voucher_type": "Stock Entry",
				"qty": 5,
				"actual_qty": 5,
				"batches": frappe._dict(batches),
				"type_of_transaction": "Inward",
				"company": "_Test Company",
				"do_not_submit": True,
			}
		).make_serial_and_batch_bundle()

		receipt = frappe.new_doc("Stock Entry")
		receipt.purpose = "Material Receipt"
		receipt.stock_entry_type = "Material Receipt"
		receipt.company = "_Test Company"
		receipt.append(
			"items",
			{
				"item_code": item.name,
				"qty": 5,
				"t_warehouse": qc,
				"basic_rate": 100,
				"serial_and_batch_bundle": bundle.name,
			},
		)
		receipt.insert()
		receipt.submit()

		# one row, two batches: one lot per batch, each carrying its own quantity
		lots = frappe.get_all(
			"Quality Control Lot",
			filters={"source_document": receipt.name},
			fields=["batch_no", "received_qty"],
		)
		self.assertEqual(
			{lot.batch_no: lot.received_qty for lot in lots},
			{name: float(qty) for name, qty in batches.items()},
		)

	def test_quality_warehouse_refuses_unrelated_stock(self):
		qc = make_qc_warehouse("_Test QC Strict WH")
		plain_item = make_item(properties={"is_stock_item": 1}).name

		# an item with no quarantine requirement cannot be parked in quarantine —
		# it would sit locked with no inspection path to release it
		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=plain_item,
			qty=1,
			to_warehouse=qc,
			purpose="Material Receipt",
			rate=100,
		)

	def test_no_quality_control_lot_for_normal_warehouse(self):
		item = make_item(properties={"is_stock_item": 1}).name
		se = make_stock_entry(
			item_code=item, qty=5, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		self.assertEqual(quality_control_lots_for(se.name), [])

	def _quarantine_item(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
			),
		)
		item.save()
		return item.name

	def test_quarantine_routes_to_quality_warehouse_and_mints_lot(self):
		qc = make_qc_warehouse()
		store = make_warehouse("_Test QC Routed Store", quality_warehouse=qc)
		item = self._quarantine_item()

		se = make_stock_entry(item_code=item, qty=4, to_warehouse=store, purpose="Material Receipt", rate=100)

		# the receipt was redirected into the Quality Control warehouse on validate…
		self.assertEqual(se.items[0].t_warehouse, qc)
		# …the document still submitted freely, and the lot was minted there
		lots = quality_control_lots_for(se.name)
		self.assertEqual(len(lots), 1)
		self.assertEqual(lots[0].quality_warehouse, qc)
		self.assertEqual(lots[0].received_qty, 4)

	def test_quality_warehouse_exit_is_locked(self):
		# dedicated Quality Control warehouse no store points at, so nothing auto-releases
		qc = make_qc_warehouse("_Test QC Lock WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# an ordinary transfer out of the Quality Control warehouse is blocked…
		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=item,
			qty=2,
			from_warehouse=qc,
			to_warehouse=REAL_WH,
			purpose="Material Transfer",
		)

		# …a release without a lot reference is blocked too…
		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=item,
			qty=2,
			from_warehouse=qc,
			to_warehouse=REAL_WH,
			purpose="Quality Control Release",
		)

		# …and a release backed by the lot only works once its inspection is submitted
		self.assertRaises(frappe.ValidationError, make_release, lot, 2, REAL_WH)
		submit_inspection_for_lot(lot)
		make_release(lot, 2, REAL_WH)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Partially Released")

	def test_release_moves_only_the_lots_batch(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		# dedicated Quality Control warehouse with no store, so nothing auto-releases
		qc = make_qc_warehouse("_Test QC Batch WH")
		item = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "QCBT.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				applicable_warehouse=qc,
			),
		)
		item.save()

		def receive_batch(batch_id):
			batch = frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": batch_id}).insert(
				ignore_permissions=True
			)
			se = make_stock_entry(
				item_code=item.name,
				qty=2,
				to_warehouse=qc,
				purpose="Material Receipt",
				rate=100,
				batch_no=batch.name,
				use_serial_batch_fields=1,
			)
			return batch.name, quality_control_lots_for(se.name)[0].name

		batch_one, lot_one = receive_batch("_Test QC Batch One")
		batch_two, lot_two = receive_batch("_Test QC Batch Two")

		# a verdict claiming the wrong batch is refused
		mismatched = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot_one,
				"item_code": item.name,
				"sample_size": 1,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"manual_inspection": 1,
				"status": "Accepted",
				"batch_no": batch_two,
			}
		)
		mismatched.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, mismatched.submit)
		mismatched.delete()

		# a batched verdict must say which batch it covers
		anonymous = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot_one,
				"item_code": item.name,
				"sample_size": 1,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"manual_inspection": 1,
				"status": "Accepted",
			}
		)
		anonymous.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, anonymous.submit)
		anonymous.delete()

		submit_inspection_for_lot(lot_one)

		# the release must carry the lot's own batch — another batch of the same
		# item in the same warehouse is refused, as is a batchless release
		self.assertRaises(frappe.ValidationError, make_release, lot_one, 2, REAL_WH, batch_no=batch_two)
		self.assertRaises(frappe.ValidationError, make_release, lot_one, 2, REAL_WH)
		make_release(lot_one, 2, REAL_WH, batch_no=batch_one)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot_one, "status"), "Released")

	def test_release_moves_exactly_the_accepted_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		qc = make_qc_warehouse("_Test QC Serial WH")
		store = make_warehouse("_Test QC Serial Store", quality_warehouse=qc)

		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCSN.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
				applicable_warehouse=qc,
			),
		)
		item.save()

		se = make_stock_entry(
			item_code=item.name, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(se.name)[0].name
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": qc}, pluck="name", order_by="name"
		)
		self.assertEqual(len(serials), 3)

		# units 1 and 3 pass, unit 2 fails — each unit identified by its serial
		bundle = make_bundle(
			3,
			{1: ["Accepted"], 2: ["Rejected"], 3: ["Accepted"]},
			item_code=item.name,
			unit_serials={1: serials[0], 2: serials[1], 3: serials[2]},
		)
		submit_inspection_for_lot(lot, reading_bundle=bundle.name)

		# exactly the accepted serials were released; the rejected one stays held
		self.assertEqual(frappe.db.get_value("Serial No", serials[0], "warehouse"), store)
		self.assertEqual(frappe.db.get_value("Serial No", serials[2], "warehouse"), store)
		self.assertEqual(frappe.db.get_value("Serial No", serials[1], "warehouse"), qc)

	def test_recorded_serials_set_the_sample_size(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Sample Serials WH")
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCSS.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				applicable_warehouse=qc,
			),
		)
		item.save()
		se = make_stock_entry(
			item_code=item.name, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(se.name)[0].name
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": qc}, pluck="name", order_by="name"
		)

		def build_inspection(serial_no=None):
			return frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": "Quality Control Lot",
					"reference_name": lot,
					"item_code": item.name,
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
					"manual_inspection": 1,
					"status": "Accepted",
					"sample_size": 2,
					"serial_no": serial_no,
				}
			)

		# a serialized verdict must say which units it covers
		anonymous = build_inspection()
		anonymous.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, anonymous.submit)
		anonymous.delete()

		inspection = build_inspection("\n".join(serials[:2]))
		inspection.insert(ignore_permissions=True)
		# the recorded serials are the sample
		self.assertEqual(inspection.sample_size, 2)

		# a serial of the same item that never came through the lot's source is refused
		make_stock_entry(
			item_code=item.name, qty=1, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		stray = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": REAL_WH}, pluck="name"
		)[0]
		stray_inspection = build_inspection(stray)
		stray_inspection.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, stray_inspection.submit)
		stray_inspection.delete()

		# a serial belonging to another item is refused
		other = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCSO.#####"}
		)
		make_stock_entry(
			item_code=other.name, qty=1, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		foreign_serial = frappe.get_all("Serial No", filters={"item_code": other.name}, pluck="name")[0]
		inspection.serial_no = foreign_serial
		self.assertRaises(frappe.ValidationError, inspection.save)

	def test_manual_release_refuses_rejected_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		# no store points at this Quality Control warehouse, so nothing auto-releases
		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		qc = make_qc_warehouse("_Test QC Manual Serial WH")

		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCMS.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
				applicable_warehouse=qc,
			),
		)
		item.save()

		se = make_stock_entry(
			item_code=item.name, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(se.name)[0].name
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": qc}, pluck="name", order_by="name"
		)

		bundle = make_bundle(
			3,
			{1: ["Accepted"], 2: ["Rejected"], 3: ["Accepted"]},
			item_code=item.name,
			unit_serials={1: serials[0], 2: serials[1], 3: serials[2]},
		)
		submit_inspection_for_lot(lot, reading_bundle=bundle.name)

		# the rejected serial cannot be released, and serials must be named
		self.assertRaises(frappe.ValidationError, make_release, lot, 1, REAL_WH, serial_no=serials[1])
		self.assertRaises(frappe.ValidationError, make_release, lot, 2, REAL_WH)

		make_release(lot, 2, REAL_WH, serial_no=f"{serials[0]}\n{serials[2]}")
		self.assertEqual(frappe.db.get_value("Serial No", serials[1], "warehouse"), qc)

	def test_generated_release_honors_bundle_mode(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		# legacy serial/batch fields disabled: generated entries must carry a
		# Serial and Batch Bundle instead
		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 0)
		try:
			qc = make_qc_warehouse("_Test QC Bundle Mode WH")
			store = make_warehouse("_Test QC Bundle Mode Store", quality_warehouse=qc)

			item = make_item(
				properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "QCBM.#####"}
			)
			item.append(
				"quality_triggers",
				trigger_row(
					document_type="Stock Entry",
					warehouse_role="Inbound",
					quality_control_mode="Quarantine",
					applicable_warehouse=qc,
				),
			)
			item.save()

			batch = frappe.get_doc(
				{"doctype": "Batch", "item": item.name, "batch_id": "_Test QC Bundle Mode Batch"}
			).insert(ignore_permissions=True)
			se = make_stock_entry(
				item_code=item.name,
				qty=2,
				to_warehouse=qc,
				purpose="Material Receipt",
				rate=100,
				batch_no=batch.name,
				use_serial_batch_fields=1,
			)
			lot = quality_control_lots_for(se.name)[0].name
			self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "batch_no"), batch.name)

			submit_inspection_for_lot(lot)

			release = frappe.get_doc(
				"Stock Entry", {"quality_control_lot": lot, "purpose": "Quality Control Release"}
			)
			row = release.items[0]
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertFalse(row.batch_no)
			bundle_batches = frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": row.serial_and_batch_bundle},
				pluck="batch_no",
			)
			self.assertEqual(set(bundle_batches), {batch.name})
			self.assertEqual(get_qty(item.name, store), 2)
		finally:
			frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)

	def test_return_allocation_respects_batches(self):
		from erpnext.stock.services.quality_quarantine import _rejected_outstanding_lots

		qc = make_qc_warehouse("_Test QC Alloc WH")
		item = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "QCAL.#####"}
		).name

		def make_lot(batch_no, rejected):
			return (
				frappe.get_doc(
					{
						"doctype": "Quality Control Lot",
						"item_code": item,
						"company": "_Test Company",
						"quality_warehouse": qc,
						"batch_no": batch_no,
						"received_qty": rejected,
						"rejected_qty": rejected,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)

		frappe.get_doc({"doctype": "Batch", "item": item, "batch_id": "_Test QC Alloc A"}).insert(
			ignore_permissions=True
		)
		frappe.get_doc({"doctype": "Batch", "item": item, "batch_id": "_Test QC Alloc B"}).insert(
			ignore_permissions=True
		)
		lot_a = make_lot("_Test QC Alloc A", 4)
		make_lot("_Test QC Alloc B", 2)

		# a return carrying batch A books only against batch A's lots
		offered = _rejected_outstanding_lots(item, qc, batch_no="_Test QC Alloc A")
		self.assertEqual([lot.name for lot in offered], [lot_a])

	def test_cancellation_reversal_is_exempt_from_the_lock(self):
		qc = make_qc_warehouse()
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		se.cancel()  # reversal takes stock back out of the Quality Control warehouse — allowed
		# the untouched lot is removed along with the reversed stock, and the
		# document sheds its quality status with it
		self.assertFalse(frappe.db.exists("Quality Control Lot", lot))
		self.assertFalse(frappe.db.get_value("Stock Entry", se.name, "quality_status"))

	def test_inspection_acceptance_releases_quarantined_stock(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Auto WH")
		store = make_warehouse("_Test QC Auto Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry", warehouse_role="Inbound", quality_control_mode="Quarantine"
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=6, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name
		self.assertEqual(get_qty(item.name, store), 0)  # quarantined, not in the store

		# acceptance auto-creates the release: stock lands in the store, lot closes
		submit_inspection_for_lot(lot, status="Accepted")
		self.assertEqual(get_qty(item.name, store), 6)
		self.assertEqual(get_qty(item.name, qc), 0)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

		# the source receipt can no longer be cancelled while the release stands
		self.assertRaises(frappe.ValidationError, receipt.cancel)

	def test_per_unit_inspection_splits_the_lot(self):
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		qc = make_qc_warehouse("_Test QC Split WH")
		store = make_warehouse("_Test QC Split Store", quality_warehouse=qc)
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# 5 units inspected individually: 3 pass, 2 fail
		bundle = make_bundle(
			5,
			{
				1: ["Accepted"],
				2: ["Accepted"],
				3: ["Rejected"],
				4: ["Accepted"],
				5: ["Rejected"],
			},
			item_code=item,
		)
		inspection = submit_inspection_for_lot(lot, status="Accepted", reading_bundle=bundle.name)
		# a mixed outcome is named, not collapsed into Accepted
		self.assertEqual(inspection.status, "Partially Accepted")

		# accepted units released to the store, rejected units stay quarantined
		self.assertEqual(get_qty(item, store), 3)
		self.assertEqual(get_qty(item, qc), 2)
		lot_doc = frappe.get_doc("Quality Control Lot", lot)
		self.assertEqual(lot_doc.accepted_qty, 3)
		self.assertEqual(lot_doc.rejected_qty, 2)
		self.assertEqual(lot_doc.pending_qty, 0)

	def test_each_quantity_basis_is_stamped_and_requires_a_bundle(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		qc = make_qc_warehouse("_Test QC Basis WH")
		store = make_warehouse("_Test QC Basis Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=2, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name

		# the trigger's basis landed on the lot...
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "inspection_basis"), "Each Quantity")

		# ...so an inspection without per-unit readings is refused
		self.assertRaises(frappe.ValidationError, submit_inspection_for_lot, lot)

		# a bundle covering fewer units than are under inspection is refused too
		short_bundle = make_bundle(1, {1: ["Accepted"]}, item_code=item.name)
		self.assertRaises(
			frappe.ValidationError, submit_inspection_for_lot, lot, reading_bundle=short_bundle.name
		)

		# and accepted with a bundle covering every unit
		bundle = make_bundle(2, {1: ["Accepted"], 2: ["Accepted"]}, item_code=item.name)
		inspection = submit_inspection_for_lot(lot, reading_bundle=bundle.name)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

		# the bundle is claimed by that inspection and cannot decide another one
		self.assertEqual(
			frappe.db.get_value("Quality Inspection Reading Bundle", bundle.name, "quality_inspection"),
			inspection.name,
		)
		second_receipt = make_stock_entry(
			item_code=item.name, qty=2, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		second_lot = quality_control_lots_for(second_receipt.name)[0].name
		self.assertRaises(
			frappe.ValidationError, submit_inspection_for_lot, second_lot, reading_bundle=bundle.name
		)

	def test_cancelling_inspection_unwinds_the_decision(self):
		qc = make_qc_warehouse("_Test QC Unwind WH")
		store = make_warehouse("_Test QC Unwind Store", quality_warehouse=qc)
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# the receipt wears the quarantine state
		self.assertEqual(frappe.db.get_value("Stock Entry", se.name, "quality_status"), "Under Inspection")

		# accept: the auto-release moves the stock to the store
		inspection = submit_inspection_for_lot(lot)
		self.assertEqual(frappe.db.get_value("Stock Entry", se.name, "quality_status"), "Released")
		release = frappe.get_doc(
			"Stock Entry", {"quality_control_lot": lot, "purpose": "Quality Control Release"}
		)
		self.assertEqual(get_qty(item, store), 5)

		# cancelling the inspection cancels the release and restores the lot
		inspection.cancel()
		release.reload()
		self.assertEqual(release.docstatus, 2)
		self.assertEqual(get_qty(item, qc), 5)
		self.assertEqual(get_qty(item, store), 0)
		lot_state = frappe.db.get_value(
			"Quality Control Lot", lot, ["accepted_qty", "pending_qty", "status"], as_dict=True
		)
		self.assertEqual(lot_state.accepted_qty, 0)
		self.assertEqual(lot_state.pending_qty, 5)
		self.assertEqual(lot_state.status, "Under Inspection")

		self.assertEqual(frappe.db.get_value("Stock Entry", se.name, "quality_status"), "Under Inspection")

		# reject: cancelling clears the booked rejection too
		rejecting = submit_inspection_for_lot(lot, status="Rejected")
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "rejected_qty"), 5)
		self.assertEqual(frappe.db.get_value("Stock Entry", se.name, "quality_status"), "Rejected")
		rejecting.cancel()
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "rejected_qty"), 0)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Under Inspection")

	def test_cancelling_an_inspection_cancels_its_bundle(self):
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		qc = make_qc_warehouse("_Test QC Cancel Bundle WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=2, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		bundle = make_bundle(2, {1: ["Accepted"], 2: ["Accepted"]}, item_code=item)
		inspection = submit_inspection_for_lot(lot, reading_bundle=bundle.name)

		# a voided inspection voids its per-unit readings with it (no deadlock on
		# the bundle guard), and the claim stays on the cancelled pair so the
		# readings can never decide other stock
		inspection.cancel()
		bundle.reload()
		self.assertEqual(bundle.docstatus, 2)
		self.assertEqual(bundle.quality_inspection, inspection.name)

	def test_sample_inspection_demands_recorded_readings(self):
		qc = make_qc_warehouse("_Test QC Rubber Stamp WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=1, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		def build_inspection():
			return frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": "Quality Control Lot",
					"reference_name": lot,
					"item_code": item,
					"sample_size": 1,
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
				}
			)

		# no readings, not manual: a rubber stamp — refused
		empty = build_inspection()
		empty.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, empty.submit)
		empty.delete()

		# a sample of zero units is a verdict about nothing — refused even manual
		zero = build_inspection()
		zero.manual_inspection = 1
		zero.sample_size = 0
		zero.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, zero.submit)
		zero.delete()

		# a formula row without a recorded reading is no better
		if not frappe.db.exists("Quality Inspection Parameter", "_Test Lot Verdict"):
			frappe.get_doc(
				{"doctype": "Quality Inspection Parameter", "parameter": "_Test Lot Verdict"}
			).insert(ignore_permissions=True)
		formula = build_inspection()
		formula.append(
			"readings",
			{
				"specification": "_Test Lot Verdict",
				"numeric": 0,
				"formula_based_criteria": 1,
				"acceptance_formula": "reading_value == 'OK'",
			},
		)
		formula.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, formula.submit)

	def test_inspector_can_override_the_basis(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Override Basis WH")
		store = make_warehouse("_Test QC Override Basis Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
				applicable_warehouse=qc,
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=2, to_warehouse=qc, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name

		# the lot proposes Each Quantity, but the inspector overrides to Sample —
		# no bundle demanded, the recorded reading decides the whole quantity
		submit_inspection_for_lot(lot, inspection_basis="Sample")
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")
		self.assertEqual(get_qty(item.name, store), 2)

	def test_manual_inspection_overrides_each_quantity(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Manual WH")
		store = make_warehouse("_Test QC Manual Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=3, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name

		# the inspector's manual verdict needs no reading bundle, even on Each Quantity
		submit_inspection_for_lot(lot, status="Accepted", manual_inspection=1)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")
		self.assertEqual(get_qty(item.name, store), 3)

	def test_purchase_receipt_stamps_basis_on_the_lot(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		qc = make_qc_warehouse("_Test QC PR Basis WH")
		store = make_warehouse("_Test QC PR Basis Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,  # auto-set Inbound
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		receipt = make_purchase_receipt(item_code=item.name, qty=3, warehouse=store, rate=100)
		lot = quality_control_lots_for(receipt.name, "Purchase Receipt")[0]
		self.assertEqual(lot.quality_warehouse, qc)  # routed
		self.assertEqual(
			frappe.db.get_value("Quality Control Lot", lot.name, "inspection_basis"), "Each Quantity"
		)

	def test_inspection_rejection_keeps_stock_quarantined(self):
		qc = make_qc_warehouse("_Test QC Reject WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=4, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		submit_inspection_for_lot(lot, status="Rejected")

		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Rejected")
		self.assertEqual(get_qty(item, qc), 4)  # stays under quality hold for the purchase return

	def test_return_inspection_serials_must_match_the_return(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCRS.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Delivery Note", warehouse_role="Inbound", quality_control_mode="Block"
			),
		)
		item.save()

		make_stock_entry(
			item_code=item.name, qty=3, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": REAL_WH}, pluck="name", order_by="name"
		)
		delivery = create_delivery_note(
			item_code=item.name,
			warehouse=REAL_WH,
			qty=3,
			serial_no="\n".join(serials),
			use_serial_batch_fields=1,
		)

		# the customer returns two specific units
		sales_return = make_return_doc("Delivery Note", delivery.name)
		sales_return.items[0].qty = -2
		sales_return.items[0].serial_no = "\n".join(serials[:2])
		sales_return.items[0].use_serial_batch_fields = 1
		sales_return.items[0].serial_and_batch_bundle = None
		sales_return.save()

		def build_inspection(serial_no):
			return frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": "Delivery Note",
					"reference_name": sales_return.name,
					"item_code": item.name,
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
					"manual_inspection": 1,
					"status": "Accepted",
					"serial_no": serial_no,
				}
			)

		# sampling a delivered serial that is NOT on this return is refused
		wrong = build_inspection(serials[2])
		wrong.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, wrong.submit)
		wrong.delete()

		# sampling a returned serial passes
		inspection = build_inspection(serials[0])
		inspection.insert(ignore_permissions=True)
		inspection.submit()

		# tampering with the return's serials after the inspection is caught at
		# the return's own submission
		sales_return.reload()
		sales_return.items[0].qty = -1
		sales_return.items[0].serial_no = serials[2]
		sales_return.save()
		self.assertRaises(frappe.ValidationError, sales_return.submit)

		# with the inspected serials restored, the return submits
		sales_return.reload()
		sales_return.items[0].qty = -2
		sales_return.items[0].serial_no = "\n".join(serials[:2])
		sales_return.save()
		sales_return.submit()

	def test_bundle_serials_guard_the_document_after_inspection(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCTB.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				stock_entry_type="Material Issue",
				warehouse_role="Outbound",
				quality_control_mode="Block",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		make_stock_entry(
			item_code=item.name, qty=3, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": REAL_WH}, pluck="name", order_by="name"
		)

		issue = make_stock_entry(
			item_code=item.name,
			qty=2,
			from_warehouse=REAL_WH,
			purpose="Material Issue",
			serial_no="\n".join(serials[:2]),
			use_serial_batch_fields=1,
			do_not_submit=True,
		)

		bundle = make_bundle(
			2,
			{1: ["Accepted"], 2: ["Accepted"]},
			item_code=item.name,
			unit_serials={1: serials[0], 2: serials[1]},
		)
		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Outgoing",
				"reference_type": "Stock Entry",
				"reference_name": issue.name,
				"item_code": item.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"inspection_basis": "Each Quantity",
				"reading_bundle": bundle.name,
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()

		# swapping the issued serials after the inspection is caught at submission
		issue.reload()
		issue.items[0].serial_no = "\n".join([serials[0], serials[2]])
		issue.save()
		self.assertRaises(frappe.ValidationError, issue.submit)

		# with the inspected serials restored, the issue submits
		issue.reload()
		issue.items[0].serial_no = "\n".join(serials[:2])
		issue.save()
		issue.submit()

	def test_inspected_batch_guards_the_document(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(
			properties={"is_stock_item": 1, "has_batch_no": 1, "batch_number_series": "QCBG.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				stock_entry_type="Material Issue",
				warehouse_role="Outbound",
				quality_control_mode="Block",
			),
		)
		item.save()

		def receive_batch(batch_id):
			batch = frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": batch_id}).insert(
				ignore_permissions=True
			)
			make_stock_entry(
				item_code=item.name,
				qty=2,
				to_warehouse=REAL_WH,
				purpose="Material Receipt",
				rate=100,
				batch_no=batch.name,
				use_serial_batch_fields=1,
			)
			return batch.name

		batch_one = receive_batch("_Test QC Guard Batch One")
		batch_two = receive_batch("_Test QC Guard Batch Two")

		issue = make_stock_entry(
			item_code=item.name,
			qty=1,
			from_warehouse=REAL_WH,
			purpose="Material Issue",
			batch_no=batch_one,
			use_serial_batch_fields=1,
			do_not_submit=True,
		)

		# inspecting a batch the row does not carry is refused outright
		wrong = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Outgoing",
				"reference_type": "Stock Entry",
				"reference_name": issue.name,
				"item_code": item.name,
				"sample_size": 1,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"manual_inspection": 1,
				"status": "Accepted",
				"batch_no": batch_two,
			}
		)
		wrong.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, wrong.submit)
		wrong.delete()

		inspection = frappe.copy_doc(wrong)
		inspection.batch_no = batch_one
		inspection.insert(ignore_permissions=True)
		inspection.submit()

		# swapping the issued batch after the inspection is caught at submission
		issue.reload()
		issue.items[0].batch_no = batch_two
		issue.save()
		self.assertRaises(frappe.ValidationError, issue.submit)

		issue.reload()
		issue.items[0].batch_no = batch_one
		issue.save()
		issue.submit()

	def test_serial_and_batch_must_agree(self):
		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "QCSB.#####",
				"has_batch_no": 1,
				"batch_number_series": "QCSBB.#####",
			}
		)

		def receive_batch(batch_id):
			batch = frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": batch_id}).insert(
				ignore_permissions=True
			)
			receipt = make_stock_entry(
				item_code=item.name,
				qty=1,
				to_warehouse=REAL_WH,
				purpose="Material Receipt",
				rate=100,
				batch_no=batch.name,
				use_serial_batch_fields=1,
			)
			serial = frappe.get_all(
				"Serial No",
				filters={"item_code": item.name, "batch_no": batch.name},
				pluck="name",
			)[0]
			return batch.name, serial, receipt

		batch_one, serial_one, receipt_one = receive_batch("_Test QC Agree One")
		batch_two, serial_two, _ = receive_batch("_Test QC Agree Two")

		# naming batch one while sampling a serial of batch two is incoherent
		disagreeing = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Stock Entry",
				"reference_name": receipt_one.name,
				"item_code": item.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"manual_inspection": 1,
				"status": "Accepted",
				"batch_no": batch_one,
				"serial_no": serial_two,
			}
		)
		self.assertRaises(frappe.ValidationError, disagreeing.insert)

	def test_inward_block_inspection_waives_unborn_batch(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "QCAB.#####",
			}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Block",
			),
		)
		item.save()

		# the batch is auto-created at submission, which Block holds until the
		# inspection exists — the inspection cannot name an unborn batch
		receipt = make_purchase_receipt(
			item_code=item.name, qty=2, warehouse=REAL_WH, rate=100, do_not_submit=True
		)
		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"item_code": item.name,
				"sample_size": 1,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"manual_inspection": 1,
				"status": "Accepted",
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()

		receipt.reload()
		receipt.submit()
		self.assertTrue(frappe.db.exists("Batch", {"item": item.name, "batch_id": ("like", "QCAB%")}))

	def test_inward_block_inspection_accepts_typed_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Block",
			),
		)
		item.save()

		# serials typed on the draft row do not exist yet — they are created at
		# the receipt's submission, which Block holds until the inspection exists
		receipt = make_purchase_receipt(
			item_code=item.name, qty=2, warehouse=REAL_WH, rate=100, do_not_submit=True
		)
		receipt.items[0].serial_no = "QC-TYPED-001\nQC-TYPED-002"
		receipt.items[0].use_serial_batch_fields = 1
		receipt.save()

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"item_code": item.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"manual_inspection": 1,
				"status": "Accepted",
				"serial_no": "QC-TYPED-001\nQC-TYPED-002",
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()

		receipt.reload()
		receipt.submit()
		self.assertEqual(frappe.db.get_value("Serial No", "QC-TYPED-001", "warehouse"), REAL_WH)

	def test_receipt_inspection_serials_must_match_the_receipt(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCPR.#####"}
		)

		# a serial of the same item from an unrelated receipt
		make_stock_entry(
			item_code=item.name, qty=1, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		foreign_serial = frappe.get_all("Serial No", filters={"item_code": item.name}, pluck="name")[0]

		# the receipt's serials are auto-created at submission — nothing on the
		# draft row for validate-time checks to see
		receipt = make_purchase_receipt(
			item_code=item.name, qty=2, warehouse=REAL_WH, rate=100, do_not_submit=True
		)
		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"item_code": item.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"manual_inspection": 1,
				"status": "Accepted",
				"serial_no": foreign_serial,
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()  # the draft row carries no serials yet: nothing to compare

		# at receipt submission the serials exist — the foreign sample is caught
		receipt.reload()
		self.assertRaises(frappe.ValidationError, receipt.submit)

	def test_customer_return_is_quarantined_and_released(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Sales Return WH")
		store = make_warehouse("_Test QC Sales Return Store", quality_warehouse=qc)

		# returned goods must be re-inspected before they re-enter the store
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Delivery Note",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
			),
		)
		item.save()

		make_stock_entry(item_code=item.name, qty=5, to_warehouse=store, purpose="Material Receipt", rate=100)
		delivery = create_delivery_note(item_code=item.name, warehouse=store, qty=5)

		# the customer sends the goods back: the return is routed into quarantine
		sales_return = make_return_doc("Delivery Note", delivery.name)
		sales_return.save()
		sales_return.submit()
		self.assertEqual(sales_return.items[0].warehouse, qc)
		self.assertEqual(get_qty(item.name, qc), 5)

		lot = quality_control_lots_for(sales_return.name, "Delivery Note")[0].name

		# the inspection decision releases the returned goods back to the store
		submit_inspection_for_lot(lot, status="Accepted")
		self.assertEqual(get_qty(item.name, store), 5)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

	def test_purchase_return_books_against_rejected_lot(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		qc = make_qc_warehouse("_Test QC Return WH")
		item = make_quarantine_item(qc, "Purchase Receipt")
		receipt = make_purchase_receipt(item_code=item, qty=4, warehouse=qc, rate=100)
		lot = quality_control_lots_for(receipt.name, "Purchase Receipt")[0].name

		# a return before any rejection has nothing to draw from quarantine —
		# the mapping itself refuses
		self.assertRaises(frappe.ValidationError, make_return_doc, "Purchase Receipt", receipt.name)

		submit_inspection_for_lot(lot, status="Rejected")

		# now the return books cleanly against the rejected lot
		return_doc = make_return_doc("Purchase Receipt", receipt.name)
		return_doc.save()
		return_doc.submit()
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "returned_qty"), 4)
		self.assertEqual(get_qty(item, qc), 0)

		# cancelling the return books the allocation back
		return_doc.cancel()
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "returned_qty"), 0)

	def test_each_quantity_inspection_sheds_lurking_readings(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Lurking WH")
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
				applicable_warehouse=qc,
			),
		)
		item.save()
		se = make_stock_entry(
			item_code=item.name, qty=1, to_warehouse=qc, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(se.name)[0].name

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				# a row lurking from an earlier template fetch — invisible on the
				# form, it must not block submission
				"readings": [{"specification": "_Test Lurking Parameter", "numeric": 0, "value": "Yes"}],
			}
		)
		frappe.get_doc(
			{"doctype": "Quality Inspection Parameter", "parameter": "_Test Lurking Parameter"}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
		inspection.insert(ignore_permissions=True)
		self.assertEqual(inspection.readings, [])

	def test_reading_bundle_born_from_inspection(self):
		from erpnext.stock.doctype.quality_inspection.quality_inspection import make_reading_bundle

		qc = make_qc_warehouse("_Test QC Born Bundle WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item,
				"sample_size": 1,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)

		# created server-side so the no_copy backlink survives: born linked, with
		# the item and the full quantity under inspection
		bundle = make_reading_bundle(inspection.name)
		self.assertEqual(bundle.quality_inspection, inspection.name)
		self.assertEqual(bundle.item_code, item)
		self.assertEqual(bundle.quantity, 3)

	def test_populated_bundle_carries_the_lot_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.quality_inspection.quality_inspection import make_reading_bundle
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			ensure_parameter,
		)

		qc = make_qc_warehouse("_Test QC Unit Serials WH")
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCUS.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
				applicable_warehouse=qc,
			),
		)
		item.save()

		template = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"quality_inspection_template_name": "_Test Unit Serial Template",
				"item_quality_inspection_parameter": [
					{"specification": ensure_parameter("_Test Unit Serial Parameter"), "value": "Yes"}
				],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		se = make_stock_entry(
			item_code=item.name, qty=2, to_warehouse=qc, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(se.name)[0].name
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": qc}, pluck="name", order_by="name"
		)

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item.name,
				"quality_inspection_template": template.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)

		bundle = make_reading_bundle(inspection.name)
		bundle.populate_units()
		bundle.insert(ignore_permissions=True)

		# the lot's source receipt names the serials under inspection: prefilled
		self.assertEqual([entry.serial_no for entry in bundle.entries], serials)

		# a lot-flow bundle of a serialized item must identify every unit
		for entry in bundle.entries:
			entry.reading_value = "Yes"
			entry.serial_no = None
		bundle.save()
		self.assertRaises(frappe.ValidationError, bundle.submit)

		bundle.reload()
		for entry, serial in zip(bundle.entries, serials, strict=True):
			entry.reading_value = "Yes"
			entry.serial_no = serial
		bundle.save()
		bundle.submit()
		self.assertEqual(bundle.docstatus, 1)

	def test_receipt_return_prefilled_with_rejected_details(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		qc = make_qc_warehouse("_Test QC Prefill WH")
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCPF.#####"}
		)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Quarantine",
				inspection_basis="Each Quantity",
				applicable_warehouse=qc,
			),
		)
		item.save()

		receipt = make_purchase_receipt(item_code=item.name, qty=3, warehouse=qc, rate=100)
		lot = quality_control_lots_for(receipt.name, "Purchase Receipt")[0].name
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": qc}, pluck="name", order_by="name"
		)

		bundle = make_bundle(
			3,
			{1: ["Accepted"], 2: ["Accepted"], 3: ["Rejected"]},
			item_code=item.name,
			unit_serials={1: serials[0], 2: serials[1], 3: serials[2]},
		)
		submit_inspection_for_lot(lot, reading_bundle=bundle.name)

		# the receipt's own Create > Purchase Return arrives shaped around the
		# verdict: only the rejected unit, identified by its serial
		return_doc = make_return_doc("Purchase Receipt", receipt.name)
		self.assertEqual(len(return_doc.items), 1)
		self.assertEqual(return_doc.items[0].qty, -1)
		self.assertEqual(return_doc.items[0].serial_no, serials[2])

		return_doc.save()
		return_doc.submit()
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "returned_qty"), 1)
		self.assertNotEqual(frappe.db.get_value("Serial No", serials[2], "warehouse"), qc)

	def test_block_flow_return_prefilled_with_rejected_count(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.quality_inspection_reading_bundle.test_quality_inspection_reading_bundle import (
			make_bundle,
		)

		# Block holds the document, not the stock: the receipt lands in the store
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Block",
				inspection_basis="Each Quantity",
			),
		)
		item.save()

		receipt = make_purchase_receipt(
			item_code=item.name, qty=3, warehouse=REAL_WH, rate=100, do_not_submit=True
		)

		bundle = make_bundle(3, {1: ["Accepted"], 2: ["Accepted"], 3: ["Rejected"]}, item_code=item.name)
		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"item_code": item.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"reading_bundle": bundle.name,
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()
		self.assertEqual(inspection.status, "Partially Accepted")

		receipt.reload()
		receipt.submit()  # the gate passes: an inspection decided the row

		# the return proposes the rejected count as an editable default
		return_doc = make_return_doc("Purchase Receipt", receipt.name)
		self.assertEqual(return_doc.items[0].qty, -1)

	def test_purchase_return_created_from_the_lot(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.services.quality_quarantine import make_purchase_return_for_lot

		qc = make_qc_warehouse("_Test QC Lot Return WH")
		item = make_quarantine_item(qc, "Purchase Receipt")
		other_item = make_item(properties={"is_stock_item": 1}).name

		# a receipt with a second, untriggered item — the return must not drag it along
		receipt = make_purchase_receipt(item_code=item, qty=4, warehouse=qc, rate=100, do_not_submit=True)
		receipt.append(
			"items", {"item_code": other_item, "qty": 2, "warehouse": REAL_WH, "rate": 50, "received_qty": 2}
		)
		receipt.save()
		receipt.submit()

		lot = quality_control_lots_for(receipt.name, "Purchase Receipt")[0].name

		# nothing rejected yet: no return to make
		self.assertRaises(frappe.ValidationError, make_purchase_return_for_lot, lot)

		submit_inspection_for_lot(lot, status="Rejected")

		return_doc = make_purchase_return_for_lot(lot)
		self.assertEqual(len(return_doc.items), 1)
		self.assertEqual(return_doc.items[0].item_code, item)
		self.assertEqual(return_doc.items[0].qty, -4)
		self.assertEqual(return_doc.items[0].warehouse, qc)

		return_doc.save()
		return_doc.submit()
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "returned_qty"), 4)
		self.assertEqual(get_qty(item, qc), 0)

	def test_stock_reconciliation_blocked_on_quality_warehouse(self):
		qc = make_qc_warehouse()
		item = make_quarantine_item(qc)

		reconciliation = frappe.new_doc("Stock Reconciliation")
		reconciliation.company = "_Test Company"
		reconciliation.purpose = "Stock Reconciliation"
		reconciliation.append("items", {"item_code": item, "warehouse": qc, "qty": 10, "valuation_rate": 100})
		self.assertRaises(frappe.ValidationError, reconciliation.save)

	def test_quarantine_requires_configured_quality_warehouse(self):
		store = make_warehouse("_Test QC Unconfigured Store")  # no quality_warehouse
		item = self._quarantine_item()

		self.assertRaises(
			frappe.ValidationError,
			make_stock_entry,
			item_code=item,
			qty=1,
			to_warehouse=store,
			purpose="Material Receipt",
			rate=100,
		)
