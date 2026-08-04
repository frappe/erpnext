# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.services.quality_trigger_resolution import get_row_serial_nos
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


def ensure_parameter(name):
	if not frappe.db.exists("Quality Inspection Parameter", name):
		frappe.get_doc({"doctype": "Quality Inspection Parameter", "parameter": name}).insert(
			ignore_permissions=True
		)
	return name


def unit_reading_rows(unit_results, unit_serials=None):
	"""unit_results: {unit_no: [status, status, ...]} — one status per parameter row."""
	rows = []
	for unit_no, statuses in unit_results.items():
		for index, status in enumerate(statuses):
			rows.append(
				{
					"unit_no": unit_no,
					"serial_no": (unit_serials or {}).get(unit_no),
					"specification": ensure_parameter(f"_Test Unit Parameter {index}"),
					# a manual observation: no acceptance criteria, so the given status holds
					"reading_value": "observed",
					"status": status,
				}
			)
	return rows


def submit_inspection_for_lot(
	lot_name,
	status="Accepted",
	unit_results=None,
	unit_serials=None,
	manual_inspection=0,
	inspection_basis=None,
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
			"unit_readings": unit_reading_rows(unit_results, unit_serials) if unit_results else [],
			# the tranche declares how many units it inspects
			"unit_quantity": max(unit_results) if unit_results else 0,
			# per-unit results are an Each Quantity inspection by definition
			"inspection_basis": inspection_basis or ("Each Quantity" if unit_results else None),
		}
	)
	if not manual_inspection and not unit_results:
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

	def test_auto_created_tracking_reaches_the_lot(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		# nothing typed, no manual bundle: serial numbers, the batch and the
		# bundle are all auto-created from the item's series during submission,
		# stamped on the database row only — the in-memory row stays bare
		qc = make_qc_warehouse("_Test QC Auto Tracking WH")
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "QCAT.#####",
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "QCATB.#####",
			}
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
			item_code=item.name, qty=2, to_warehouse=qc, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(se.name)[0].name

		batch_no = frappe.db.get_value("Quality Control Lot", lot, "batch_no")
		self.assertTrue(batch_no)
		self.assertEqual(
			frappe.db.get_value(
				"Serial and Batch Entry",
				{
					"parent": frappe.db.get_value(
						"Stock Entry Detail", {"parent": se.name}, "serial_and_batch_bundle"
					)
				},
				"batch_no",
			),
			batch_no,
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"disable_automatic_quality_control_release": 1})
	def test_setting_turns_off_the_automatic_release(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.services.quality_release import make_release_for_lot

		qc = make_qc_warehouse("_Test QC NoAuto WH")
		store = make_warehouse("_Test QC NoAuto Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry", warehouse_role="Inbound", quality_control_mode="Quarantine"
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=3, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name

		# a unique release warehouse exists, but the site opted for manual
		# releases: the verdict books, nothing moves
		submit_inspection_for_lot(lot, status="Accepted")
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Awaiting Release")
		self.assertEqual(get_qty(item.name, store), 0)
		self.assertEqual(get_qty(item.name, qc), 3)

		# one candidate store: the release dialog defaults to it
		lot_doc = frappe.get_doc("Quality Control Lot", lot)
		lot_doc.run_method("onload")
		self.assertEqual(lot_doc.get_onload("default_release_warehouse"), store)

		# the manual path stays open
		release = make_release_for_lot(lot, store)
		release.insert()
		release.submit()
		self.assertEqual(get_qty(item.name, store), 3)

	def test_manual_release_built_from_the_lot(self):
		from erpnext.stock.services.quality_release import make_release_for_lot

		# two stores share the Quality Control warehouse: no unique release
		# target, so nothing auto-releases on inspection submission
		qc = make_qc_warehouse("_Test QC Ambiguous WH")
		store_one = make_warehouse("_Test QC Ambiguous Store One", quality_warehouse=qc)
		make_warehouse("_Test QC Ambiguous Store Two", quality_warehouse=qc)

		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=4, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# the maker refuses while the inspection is pending
		self.assertRaises(frappe.ValidationError, make_release_for_lot, lot)

		submit_inspection_for_lot(lot)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "pending_qty"), 4)
		# decided but nothing has physically left quarantine yet
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Awaiting Release")

		# two candidate stores: the release dialog gets no default
		lot_doc = frappe.get_doc("Quality Control Lot", lot)
		lot_doc.run_method("onload")
		self.assertFalse(lot_doc.get_onload("default_release_warehouse"))

		# the form prefill (picking the lot on a Stock Entry) carries the same
		# row: accepted quantity out of the Quality Control warehouse, target open
		from erpnext.stock.services.quality_release import get_release_prefill_for_lot

		prefill = get_release_prefill_for_lot(lot)
		self.assertEqual(prefill["row"]["qty"], 4)
		self.assertEqual(prefill["row"]["s_warehouse"], qc)
		self.assertFalse(prefill["row"]["t_warehouse"])

		# pre-filled with the accepted quantity; the user picked the store
		release = make_release_for_lot(lot, store_one)
		self.assertEqual(release.items[0].qty, 4)
		self.assertEqual(release.items[0].s_warehouse, qc)
		self.assertEqual(release.items[0].t_warehouse, store_one)
		release.insert()
		release.submit()

		self.assertEqual(get_qty(item, store_one), 4)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

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

	def test_one_action_drafts_an_inspection_for_every_open_lot(self):
		import json

		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.quality_control_lot.quality_control_lot import (
			make_inspections_for_lots,
		)

		qc = make_qc_warehouse("_Test QC Bulk WH")
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "QCBLK.#####",
			}
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

		receipt = frappe.new_doc("Stock Entry")
		receipt.purpose = "Material Receipt"
		receipt.stock_entry_type = "Material Receipt"
		receipt.company = "_Test Company"
		for qty in (2, 3):
			receipt.append(
				"items", {"item_code": item.name, "qty": qty, "t_warehouse": qc, "basic_rate": 100}
			)
		receipt.insert()
		receipt.submit()

		lots = [lot.name for lot in quality_control_lots_for(receipt.name)]
		self.assertEqual(len(lots), 2)

		created = make_inspections_for_lots(json.dumps(lots))
		self.assertEqual(len(created), 2)
		self.assertEqual(
			{frappe.db.get_value("Quality Inspection", name, "reference_name") for name in created},
			set(lots),
		)

		# a decided lot is skipped rather than drafted again
		submit_inspection_for_lot(lots[0])
		second_round = make_inspections_for_lots(json.dumps(lots))
		self.assertEqual(
			[frappe.db.get_value("Quality Inspection", name, "reference_name") for name in second_round],
			[lots[1]],
		)

	def test_one_action_releases_every_lot_awaiting_one(self):
		import json

		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.services.quality_release import make_releases_for_lots

		qc = make_qc_warehouse("_Test QC BulkRel WH")
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "QCBR.#####",
			}
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

		receipt = frappe.new_doc("Stock Entry")
		receipt.purpose = "Material Receipt"
		receipt.stock_entry_type = "Material Receipt"
		receipt.company = "_Test Company"
		for qty in (2, 3):
			receipt.append(
				"items", {"item_code": item.name, "qty": qty, "t_warehouse": qc, "basic_rate": 100}
			)
		receipt.insert()
		receipt.submit()

		lots = [lot.name for lot in quality_control_lots_for(receipt.name)]
		self.assertEqual(len(lots), 2)
		for lot in lots:
			submit_inspection_for_lot(lot)
			self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Awaiting Release")

		released = make_releases_for_lots(json.dumps(lots), REAL_WH)
		self.assertEqual(len(released), 2)
		for lot in lots:
			self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

		# nothing left awaiting release: the action refuses rather than making empty entries
		self.assertRaises(frappe.ValidationError, make_releases_for_lots, json.dumps(lots), REAL_WH)

	def test_readings_copy_from_another_inspection(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.quality_inspection.quality_inspection import get_readings_to_copy

		qc = make_qc_warehouse("_Test QC Copy WH")
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "QCCP.#####",
			}
		)
		template = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"quality_inspection_template_name": "_Test Copy Readings Template",
				"item_quality_inspection_parameter": [
					{
						"specification": ensure_parameter("_Test Copy Parameter"),
						"numeric": 1,
						"min_value": 1,
						"max_value": 10,
					}
				],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				applicable_warehouse=qc,
				inspection_template=template.name,
			),
		)
		item.save()

		receipt = frappe.new_doc("Stock Entry")
		receipt.purpose = "Material Receipt"
		receipt.stock_entry_type = "Material Receipt"
		receipt.company = "_Test Company"
		for qty in (2, 3):
			receipt.append(
				"items", {"item_code": item.name, "qty": qty, "t_warehouse": qc, "basic_rate": 100}
			)
		receipt.insert()
		receipt.submit()

		lots = [lot.name for lot in quality_control_lots_for(receipt.name)]

		def draft_for(lot_name):
			return frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": "Quality Control Lot",
					"reference_name": lot_name,
					"item_code": item.name,
					"quality_inspection_template": template.name,
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
					"sample_size": 1,
				}
			).insert(ignore_permissions=True)

		first = draft_for(lots[0])
		first.readings[0].reading_1 = "5"
		first.save(ignore_permissions=True)

		copied = get_readings_to_copy(first.name)
		self.assertEqual(copied[0]["specification"], "_Test Copy Parameter")
		self.assertEqual(copied[0]["reading_1"], "5")

		second = draft_for(lots[1])
		for row in second.readings:
			for source in copied:
				if source["specification"] == row.specification:
					row.reading_1 = source["reading_1"]
		second.save(ignore_permissions=True)

		self.assertEqual(second.readings[0].reading_1, "5")
		self.assertEqual(second.readings[0].status, "Accepted")

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

		# the lot's batch is a fact the verdict mirrors — a wrong claim cannot survive
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
		self.assertEqual(mismatched.batch_no, batch_one)
		mismatched.delete()

		submit_inspection_for_lot(lot_one)

		# the release must carry the lot's own batch — another batch of the same
		# item in the same warehouse is refused, as is a batchless release
		self.assertRaises(frappe.ValidationError, make_release, lot_one, 2, REAL_WH, batch_no=batch_two)
		self.assertRaises(frappe.ValidationError, make_release, lot_one, 2, REAL_WH)
		make_release(lot_one, 2, REAL_WH, batch_no=batch_one)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot_one, "status"), "Released")

		# the lot's batch view reconciles the live quarantine balance
		from erpnext.stock.doctype.quality_control_lot.quality_control_lot import get_batch_summary

		self.assertEqual(
			get_batch_summary(lot_one), {"batch_no": batch_one, "held_qty": 0, "expected_qty": 0}
		)
		self.assertEqual(
			get_batch_summary(lot_two), {"batch_no": batch_two, "held_qty": 2, "expected_qty": 2}
		)

	def test_release_moves_exactly_the_accepted_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

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
		submit_inspection_for_lot(
			lot,
			unit_results={1: ["Accepted"], 2: ["Rejected"], 3: ["Accepted"]},
			unit_serials={1: serials[0], 2: serials[1], 3: serials[2]},
		)

		# exactly the accepted serials were released; the rejected one stays held
		self.assertEqual(frappe.db.get_value("Serial No", serials[0], "warehouse"), store)
		self.assertEqual(frappe.db.get_value("Serial No", serials[2], "warehouse"), store)
		self.assertEqual(frappe.db.get_value("Serial No", serials[1], "warehouse"), qc)

	def test_rejected_stock_moves_to_a_rejected_warehouse(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.services.quality_release import make_rejected_stock_transfer_for_lot

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		if not frappe.db.exists("Warehouse Type", "Rejected"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Rejected"}).insert(ignore_permissions=True)

		qc = make_qc_warehouse("_Test QC Disposition WH")
		make_warehouse("_Test QC Disposition Store", quality_warehouse=qc)
		rejected_warehouse = make_warehouse("_Test QC Disposition Rejects", warehouse_type="Rejected")

		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCDS.#####"}
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

		submit_inspection_for_lot(
			lot,
			unit_results={1: ["Accepted"], 2: ["Rejected"], 3: ["Accepted"]},
			unit_serials={1: serials[0], 2: serials[1], 3: serials[2]},
		)

		# an accepted serial cannot be smuggled into the Rejected warehouse
		self.assertRaises(
			frappe.ValidationError, make_release, lot, 1, rejected_warehouse, serial_no=serials[0]
		)

		# the pre-filled disposition carries exactly the rejected serial
		entry = make_rejected_stock_transfer_for_lot(lot)
		row = entry.items[0]
		self.assertEqual(row.qty, 1)
		self.assertEqual(row.serial_no, serials[1])
		self.assertEqual(row.s_warehouse, qc)
		row.t_warehouse = rejected_warehouse
		entry.insert()
		entry.submit()

		# quarantine is drained: the rejected unit sits in the Rejected warehouse,
		# booked on the lot as disposed
		self.assertEqual(frappe.db.get_value("Serial No", serials[1], "warehouse"), rejected_warehouse)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "disposed_qty"), 1)
		self.assertEqual(get_qty(item.name, qc), 0)

		# nothing rejected remains in quarantine: a second disposition is refused
		self.assertRaises(frappe.ValidationError, make_rejected_stock_transfer_for_lot, lot)

		# the lot's serial view tells where every unit went
		from erpnext.stock.doctype.quality_control_lot.quality_control_lot import get_serial_numbers

		self.assertEqual(
			[(row["serial_no"], row["verdict"], row["state"]) for row in get_serial_numbers(lot)],
			[
				(serials[0], "Accepted", "Released"),
				(serials[1], "Rejected", "Rejected Stock"),
				(serials[2], "Accepted", "Released"),
			],
		)

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

		# a serialized verdict must name the units it sampled
		anonymous = build_inspection()
		anonymous.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, anonymous.submit)
		anonymous.reload()
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
		self.assertRaises(frappe.ValidationError, stray_inspection.insert, ignore_permissions=True)

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

		submit_inspection_for_lot(
			lot,
			unit_results={1: ["Accepted"], 2: ["Rejected"], 3: ["Accepted"]},
			unit_serials={1: serials[0], 2: serials[1], 3: serials[2]},
		)

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
		from erpnext.stock.services.quality_returns import _rejected_outstanding_lots

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

	def test_cancel_blocked_once_the_lot_released(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Cancel WH")
		store = make_warehouse("_Test QC Cancel Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry", warehouse_role="Inbound", quality_control_mode="Quarantine"
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=2, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name

		# acceptance releases the stock out of quarantine; the deposit can no
		# longer be reversed, so the guard must refuse — with its own message,
		# not the stock ledger's negative-stock error
		submit_inspection_for_lot(lot, status="Accepted")
		self.assertRaisesRegex(frappe.ValidationError, "released or rejected", receipt.cancel)

		# nothing was unwound: the lot survives and the released stock stands
		self.assertTrue(frappe.db.exists("Quality Control Lot", lot))
		receipt.reload()
		self.assertEqual(receipt.docstatus, 1)
		self.assertEqual(get_qty(item.name, store), 2)

	def test_cancel_succeeds_after_full_unwind(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Unwind WH")
		store = make_warehouse("_Test QC Unwind Store", quality_warehouse=qc)

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry", warehouse_role="Inbound", quality_control_mode="Quarantine"
			),
		)
		item.save()

		receipt = make_stock_entry(
			item_code=item.name, qty=2, to_warehouse=store, purpose="Material Receipt", rate=100
		)
		lot = quality_control_lots_for(receipt.name)[0].name

		# accept (auto-release), then unwind: cancelling the inspection cascades
		# to its release and puts the stock back under quarantine
		inspection = submit_inspection_for_lot(lot, status="Accepted")
		release = frappe.db.get_value("Stock Entry", {"quality_control_lot": lot, "docstatus": 1}, "name")
		frappe.get_doc("Quality Inspection", inspection.name).cancel()
		self.assertEqual(frappe.db.get_value("Stock Entry", release, "docstatus"), 2)

		# the cancelled release and inspection still reference the lot; the
		# source cancellation must shed those links and delete the lot anyway
		receipt.reload()
		receipt.cancel()
		self.assertFalse(frappe.db.exists("Quality Control Lot", lot))
		self.assertFalse(frappe.db.get_value("Stock Entry", release, "quality_control_lot"))
		self.assertFalse(frappe.db.get_value("Quality Inspection", inspection.name, "reference_name"))

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
		qc = make_qc_warehouse("_Test QC Split WH")
		store = make_warehouse("_Test QC Split Store", quality_warehouse=qc)
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# 5 units inspected individually: 3 pass, 2 fail
		inspection = submit_inspection_for_lot(
			lot,
			status="Accepted",
			unit_results={
				1: ["Accepted"],
				2: ["Accepted"],
				3: ["Rejected"],
				4: ["Accepted"],
				5: ["Rejected"],
			},
		)
		# a mixed outcome is named, not collapsed into Accepted
		self.assertEqual(inspection.status, "Partially Accepted")

		# accepted units released to the store, rejected units stay quarantined
		self.assertEqual(get_qty(item, store), 3)
		self.assertEqual(get_qty(item, qc), 2)
		lot_doc = frappe.get_doc("Quality Control Lot", lot)
		self.assertEqual(lot_doc.accepted_qty, 3)
		self.assertEqual(lot_doc.rejected_qty, 2)
		self.assertEqual(lot_doc.pending_qty, 0)

	def test_each_quantity_basis_is_stamped_and_requires_unit_readings(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

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

		# readings covering fewer units form a tranche: they decide just those
		submit_inspection_for_lot(lot, unit_results={1: ["Accepted"]})
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "decided_qty"), 1)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Partially Released")

		# the remainder is decided by a second inspection
		submit_inspection_for_lot(lot, unit_results={1: ["Accepted"]})
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "decided_qty"), 2)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

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

	def test_cancelling_an_inspection_voids_its_unit_readings(self):
		qc = make_qc_warehouse("_Test QC Cancel Bundle WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=2, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		inspection = submit_inspection_for_lot(lot, unit_results={1: ["Accepted"], 2: ["Accepted"]})

		# a voided inspection voids its per-unit readings with it — they live on
		# the document and freeze and cancel as one
		inspection.cancel()
		self.assertEqual(inspection.docstatus, 2)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Under Inspection")

	def test_unit_readings_roll_up_and_derive(self):
		qc = make_qc_warehouse("_Test QC Unit Roll Up WH")
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
				"inspection_basis": "Each Quantity",
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		parameter = ensure_parameter("_Test Derived Status Parameter")
		entry_rows = [
			# numeric: inside and outside [1, 10]
			{"unit_no": 1, "numeric": 1, "min_value": 1, "max_value": 10, "reading_value": "5"},
			{"unit_no": 2, "numeric": 1, "min_value": 1, "max_value": 10, "reading_value": "12"},
			# non-numeric: case-insensitive match against the criteria value
			{"unit_no": 1, "numeric": 0, "value": "Yes", "reading_value": " yes "},
			{"unit_no": 3, "numeric": 0, "value": "Yes", "reading_value": "no"},
		]
		for row in entry_rows:
			row["specification"] = parameter
			inspection.append("unit_readings", row)
		inspection.insert(ignore_permissions=True)

		self.assertEqual(
			[entry.status for entry in inspection.unit_readings],
			["Accepted", "Rejected", "Accepted", "Rejected"],
		)
		# a unit is rejected if any of its readings rejected
		self.assertEqual(inspection.accepted_unit_quantity, 1)
		self.assertEqual(inspection.rejected_unit_quantity, 2)
		self.assertEqual(inspection.status, "Partially Accepted")

	def test_unit_readings_submission_gates(self):
		qc = make_qc_warehouse("_Test QC Unit Gates WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		def build(unit_results):
			return frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": "Quality Control Lot",
					"reference_name": lot,
					"item_code": item,
					"inspection_basis": "Each Quantity",
					"unit_readings": unit_reading_rows(unit_results),
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
				}
			)

		# unit numbers must fit the quantity under inspection
		self.assertRaises(frappe.ValidationError, build({5: ["Accepted"]}).insert)

		# 3 declared units but only 2 with readings: not every unit was inspected
		short = build({1: ["Accepted"], 2: ["Accepted"]})
		short.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, short.submit)
		short.delete()

		# an entry without a reading would pass on its default status unseen
		unread = build({1: ["Accepted"], 2: ["Accepted"], 3: ["Accepted"]})
		unread.unit_readings[2].reading_value = ""
		unread.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, unread.submit)
		unread.delete()

	def test_sample_cannot_exceed_decided_quantity(self):
		qc = make_qc_warehouse("_Test QC Sample Bound WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item,
				"manual_inspection": 1,
				"status": "Accepted",
				"sample_size": 5,
				"decided_quantity": 2,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		# creation lands the draft, prefills and all — but a sample of 5 cannot
		# decide only 2, and the first save says so without waiting for submission
		inspection.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, inspection.save)
		inspection.delete()

		# left blank, the decided quantity fills with everything undecided on save
		blank = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item,
				"manual_inspection": 1,
				"status": "Accepted",
				"sample_size": 5,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		blank.insert(ignore_permissions=True)
		self.assertEqual(blank.decided_quantity, 5)

	def test_lot_decided_in_parts(self):
		qc = make_qc_warehouse("_Test QC Tranche WH")
		store = make_warehouse("_Test QC Tranche Store", quality_warehouse=qc)
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# first tranche: 2 of 5 inspected per unit, one rejected
		first = submit_inspection_for_lot(lot, unit_results={1: ["Accepted"], 2: ["Rejected"]})
		lot_doc = frappe.get_doc("Quality Control Lot", lot)
		self.assertEqual(lot_doc.decided_qty, 2)
		self.assertEqual(lot_doc.rejected_qty, 1)
		self.assertEqual(lot_doc.accepted_qty, 1)  # auto-released
		self.assertEqual(lot_doc.status, "Partially Released")
		self.assertEqual(get_qty(item, store), 1)

		# the 3 undecided units cannot leave, even though they are pending
		self.assertRaises(frappe.ValidationError, make_release, lot, 2, store)

		# the remainder is decided by a verdict-less sample acceptance
		submit_inspection_for_lot(lot)
		lot_doc.reload()
		self.assertEqual(lot_doc.decided_qty, 5)
		self.assertEqual(lot_doc.accepted_qty, 4)
		self.assertEqual(lot_doc.status, "Released")
		self.assertEqual(get_qty(item, store), 4)
		self.assertEqual(get_qty(item, qc), 1)  # the rejected unit awaits return

		# cancelling the first tranche is refused: the releases already moved
		# more accepted stock than the remaining verdict covers
		self.assertRaises(frappe.ValidationError, first.cancel)

	def test_serialized_lot_decided_in_parts(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		qc = make_qc_warehouse("_Test QC Serial Tranche WH")
		store = make_warehouse("_Test QC Serial Tranche Store", quality_warehouse=qc)
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCST.#####"}
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

		# a partial verdict on a serialized item must name its units
		partial = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item.name,
				"inspection_basis": "Sample",
				"manual_inspection": 1,
				"status": "Accepted",
				"sample_size": 1,
				"decided_quantity": 1,
				"serial_no": serials[0],
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		partial.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, partial.submit)
		partial.delete()

		# first tranche rejects one named unit
		submit_inspection_for_lot(lot, unit_results={1: ["Rejected"]}, unit_serials={1: serials[0]})
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "rejected_qty"), 1)

		# a serial decided once cannot be decided again
		self.assertRaises(
			frappe.ValidationError,
			submit_inspection_for_lot,
			lot,
			unit_results={1: ["Accepted"]},
			unit_serials={1: serials[0]},
		)

		# the remaining tranche accepts the other two — exactly those release
		submit_inspection_for_lot(
			lot,
			unit_results={1: ["Accepted"], 2: ["Accepted"]},
			unit_serials={1: serials[1], 2: serials[2]},
		)
		self.assertEqual(frappe.db.get_value("Serial No", serials[0], "warehouse"), qc)
		self.assertEqual(frappe.db.get_value("Serial No", serials[1], "warehouse"), store)
		self.assertEqual(frappe.db.get_value("Serial No", serials[2], "warehouse"), store)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "status"), "Released")

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

		# a manual verdict needs no counted sample — it stands on the inspector
		zero = build_inspection()
		zero.manual_inspection = 1
		zero.sample_size = 0
		zero.insert(ignore_permissions=True)
		zero.submit()
		zero.cancel()
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
		self.assertRaises(frappe.ValidationError, wrong.insert, ignore_permissions=True)

		# sampling a returned serial passes — the sample vouches for the row
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
				"unit_readings": unit_reading_rows(
					{1: ["Accepted"], 2: ["Accepted"]}, {1: serials[0], 2: serials[1]}
				),
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

	def test_transaction_units_name_their_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCTU.#####"}
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
			item_code=item.name, qty=2, to_warehouse=REAL_WH, purpose="Material Receipt", rate=100
		)
		serials = frappe.get_all(
			"Serial No", filters={"item_code": item.name, "warehouse": REAL_WH}, pluck="name", order_by="name"
		)
		issue = make_stock_entry(
			item_code=item.name,
			qty=2,
			from_warehouse=REAL_WH,
			purpose="Material Issue",
			serial_no="\n".join(serials),
			use_serial_batch_fields=1,
			do_not_submit=True,
		)

		# the row names its serials, so every inspected unit must too
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
				"unit_readings": unit_reading_rows({1: ["Accepted"], 2: ["Accepted"]}),
			}
		)
		inspection.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, inspection.submit)

		inspection.reload()
		for entry, serial in zip(inspection.unit_readings, serials, strict=True):
			entry.serial_no = serial
		inspection.save(ignore_permissions=True)
		inspection.submit()
		self.assertEqual(inspection.docstatus, 1)

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
		self.assertRaises(frappe.ValidationError, wrong.insert, ignore_permissions=True)

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

		batch_one, _serial_one, receipt_one = receive_batch("_Test QC Agree One")
		_batch_two, serial_two, _ = receive_batch("_Test QC Agree Two")

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

	def test_block_receipt_reconciles_typed_batches(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Block",
			),
		)
		item.save()
		batch_one = (
			frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": item.name + "-B1"})
			.insert()
			.name
		)
		batch_two = (
			frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": item.name + "-B2"})
			.insert()
			.name
		)

		receipt = make_purchase_receipt(
			item_code=item.name, qty=2, warehouse=REAL_WH, rate=100, do_not_submit=True
		)
		receipt.items[0].batch_no = batch_one
		receipt.items[0].use_serial_batch_fields = 1
		receipt.save()

		def verdict(batch_no=None):
			doc = frappe.get_doc(
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
					"batch_no": batch_no,
				}
			)
			doc.insert(ignore_permissions=True)
			doc.submit()
			return doc

		# a verdict naming no batch cannot say which batch it judged — it must
		# be cancelled before the receipt may submit
		anonymous = verdict()
		receipt.reload()
		self.assertRaises(frappe.ValidationError, receipt.submit)
		anonymous.cancel()

		inspected = verdict(batch_one)
		self.assertEqual(inspected.get_reference_row_identity(), {"has_batch": True, "has_serials": False})

		# the row changed after inspection — its verdicts no longer describe it
		receipt.reload()
		receipt.items[0].batch_no = batch_two
		receipt.save()
		self.assertRaises(frappe.ValidationError, receipt.submit)

		# back on the inspected batch, identity and verdicts reconcile
		receipt.reload()
		receipt.items[0].batch_no = batch_one
		receipt.save()
		receipt.submit()
		self.assertEqual(receipt.docstatus, 1)

	def test_serialized_verdict_must_name_its_sample(self):
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

		receipt = make_purchase_receipt(
			item_code=item.name, qty=2, warehouse=REAL_WH, rate=100, do_not_submit=True
		)
		receipt.items[0].serial_no = "QC-ANON-001\nQC-ANON-002"
		receipt.items[0].use_serial_batch_fields = 1
		receipt.save()

		def verdict(serial_no=None):
			doc = frappe.get_doc(
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
					"serial_no": serial_no,
				}
			)
			doc.insert(ignore_permissions=True)
			return doc

		# an unnamed serialized verdict refuses to submit at the source: the
		# sampled serials are the proof a sample was taken
		anonymous = verdict()
		self.assertRaises(frappe.ValidationError, anonymous.submit)
		anonymous.reload()
		anonymous.delete()

		# a sampled serial vouches for the row
		verdict("QC-ANON-001").submit()
		receipt.reload()
		receipt.submit()
		self.assertEqual(receipt.docstatus, 1)

	def test_batch_sample_cannot_exceed_the_rows_batch_qty(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 0)
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1})
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

		def receive(batch_id):
			batch = frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": batch_id}).insert(
				ignore_permissions=True
			)
			make_stock_entry(
				item_code=item.name,
				qty=3,
				to_warehouse=REAL_WH,
				purpose="Material Receipt",
				rate=100,
				batch_no=batch.name,
				use_serial_batch_fields=1,
			)
			return batch.name

		batch_one = receive(item.name + "-B1")
		batch_two = receive(item.name + "-B2")

		# one issue row drawing on both batches through a bundle
		issue = make_stock_entry(
			item_code=item.name,
			qty=4,
			from_warehouse=REAL_WH,
			purpose="Material Issue",
			do_not_submit=True,
		)
		bundle = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": item.name,
				"warehouse": REAL_WH,
				"voucher_type": "Stock Entry",
				"type_of_transaction": "Outward",
				"company": issue.company,
				"entries": [
					{"batch_no": batch_one, "qty": -2, "warehouse": REAL_WH},
					{"batch_no": batch_two, "qty": -2, "warehouse": REAL_WH},
				],
			}
		).insert(ignore_permissions=True)
		issue.items[0].serial_and_batch_bundle = bundle.name
		issue.save()

		def verdict(batch_no, sample_size):
			doc = frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Outgoing",
					"reference_type": "Stock Entry",
					"reference_name": issue.name,
					"item_code": item.name,
					"sample_size": sample_size,
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
					"manual_inspection": 1,
					"status": "Accepted",
					"batch_no": batch_no,
				}
			)
			doc.insert(ignore_permissions=True)
			doc.submit()
			return doc

		# 3 sampled units fit the row (4) but not the batch (2)
		oversized = verdict(batch_one, 3)
		self.assertRaises(frappe.ValidationError, issue.submit)

		oversized.cancel()
		verdict(batch_one, 2)
		verdict(batch_two, 2)
		issue.reload()
		issue.submit()
		self.assertEqual(issue.docstatus, 1)

	def test_unborn_identity_is_cleared_off_the_inspection(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Block",
			),
		)
		item.save()
		stray = (
			frappe.get_doc({"doctype": "Batch", "item": item.name, "batch_id": item.name + "-STRAY"})
			.insert()
			.name
		)

		# the row types no batch — its identity is born at submission, so a
		# batch named now could only contradict it
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
				"batch_no": stray,
			}
		)
		inspection.insert(ignore_permissions=True)
		self.assertFalse(inspection.batch_no)
		self.assertEqual(inspection.get_reference_row_identity(), {"has_batch": False, "has_serials": False})

	def test_receipt_inspection_cannot_name_unborn_serials(self):
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

		# the receipt's serials are auto-created at submission — nothing exists
		# for the inspection to name, so the foreign serial is cleared on save
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
				"serial_no": foreign_serial,
			}
		)
		inspection.insert(ignore_permissions=True)
		self.assertFalse(inspection.serial_no)
		inspection.submit()

		# with nothing foreign on record, the receipt submits clean
		receipt.reload()
		receipt.submit()
		self.assertEqual(receipt.docstatus, 1)

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

	def test_a_lot_sees_only_its_own_rows_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Row Scope WH")
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "QCRS.#####"}
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
				"quality_inspection_template_name": "_Test Row Scope Template",
				"item_quality_inspection_parameter": [
					{
						"specification": ensure_parameter("_Test Row Scope Parameter"),
						"numeric": 0,
						"value": "Yes",
					}
				],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		receipt = frappe.new_doc("Stock Entry")
		receipt.purpose = "Material Receipt"
		receipt.stock_entry_type = "Material Receipt"
		receipt.company = "_Test Company"
		for qty in (2, 3):
			receipt.append(
				"items", {"item_code": item.name, "qty": qty, "t_warehouse": qc, "basic_rate": 100}
			)
		receipt.insert()
		receipt.submit()
		receipt.reload()

		lots = quality_control_lots_for(receipt.name)
		self.assertEqual(len(lots), 2)

		by_row = {
			frappe.db.get_value("Quality Control Lot", lot.name, "source_document_row"): lot.name
			for lot in lots
		}
		for row in receipt.items:
			expected = set(get_row_serial_nos(row))
			inspection = frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": "Quality Control Lot",
					"reference_name": by_row[row.name],
					"item_code": item.name,
					"quality_inspection_template": template.name,
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
				}
			).insert(ignore_permissions=True)

			inspection.populate_units()
			# both rows put the same item in the same warehouse; each lot may still
			# only see the units that arrived on its own row
			self.assertEqual({entry.serial_no for entry in inspection.unit_readings}, expected)

	def test_populate_units_builds_the_unit_readings(self):
		qc = make_qc_warehouse("_Test QC Born Bundle WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		template = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"quality_inspection_template_name": "_Test Populate Units Template",
				"item_quality_inspection_parameter": [
					{
						"specification": ensure_parameter("_Test Populate Units Parameter"),
						"numeric": 0,
						"value": "Yes",
					}
				],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item,
				"quality_inspection_template": template.name,
				"inspection_basis": "Each Quantity",
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)

		# the unit quantity defaults to the full quantity under inspection, and
		# Populate Units builds one row per unit and template parameter
		self.assertEqual(inspection.unit_quantity, 3)
		inspection.populate_units()
		self.assertEqual(len(inspection.unit_readings), 3)
		self.assertEqual([entry.unit_no for entry in inspection.unit_readings], [1, 2, 3])

	def test_populated_units_carry_the_lot_serials(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

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
					{
						"specification": ensure_parameter("_Test Unit Serial Parameter"),
						"numeric": 0,
						"value": "Yes",
					}
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

		inspection.populate_units()
		for entry in inspection.unit_readings:
			entry.reading_value = "Yes"
		inspection.save(ignore_permissions=True)

		# the lot's source receipt names the serials under inspection: prefilled
		self.assertEqual([entry.serial_no for entry in inspection.unit_readings], serials)

		# a lot-flow inspection of a serialized item must identify every unit —
		# refused at save, no need to wait for submission
		for entry in inspection.unit_readings:
			entry.serial_no = None
		self.assertRaises(frappe.ValidationError, inspection.save)

		inspection.reload()
		for entry, serial in zip(inspection.unit_readings, serials, strict=True):
			entry.reading_value = "Yes"
			entry.serial_no = serial
		inspection.save(ignore_permissions=True)
		inspection.submit()
		self.assertEqual(inspection.docstatus, 1)

	def test_receipt_return_prefilled_with_rejected_details(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

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

		submit_inspection_for_lot(
			lot,
			unit_results={1: ["Accepted"], 2: ["Accepted"], 3: ["Rejected"]},
			unit_serials={1: serials[0], 2: serials[1], 3: serials[2]},
		)

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

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"item_code": item.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
				"inspection_basis": "Each Quantity",
				"unit_readings": unit_reading_rows({1: ["Accepted"], 2: ["Accepted"], 3: ["Rejected"]}),
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

	def test_wholly_rejected_verdict_is_received_as_rejected_only(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Purchase Receipt",
				warehouse_role=None,
				quality_control_mode="Block",
			),
		)
		item.save()

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
				"status": "Rejected",
			}
		)
		inspection.insert(ignore_permissions=True)
		inspection.submit()

		# accepting any of it defies the verdict
		receipt.reload()
		self.assertRaises(frappe.ValidationError, receipt.submit)

		# nothing accepted, everything rejected: the verdict is honoured
		receipt.reload()
		receipt.items[0].qty = 0
		receipt.items[0].rejected_qty = 2
		receipt.items[0].rejected_warehouse = make_warehouse(
			"_Test QC Rejected Intake", warehouse_type="Rejected"
		)
		receipt.save()
		receipt.submit()
		self.assertEqual(receipt.docstatus, 1)

	def test_inspection_outcome_proposes_the_document_split(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.services.quality_trigger_resolution import get_inspection_outcomes

		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1})
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

		template = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"quality_inspection_template_name": "_Test Outcome Split Template",
				"item_quality_inspection_parameter": [
					{
						"specification": ensure_parameter("_Test Outcome Split Parameter"),
						"numeric": 0,
						"value": "Yes",
					}
				],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		# Block inspects the draft: the typed serials exist nowhere else yet
		serials = [f"QCOUT-{item.name}-{index}" for index in range(3)]
		receipt = make_purchase_receipt(
			item_code=item.name, qty=3, warehouse=REAL_WH, rate=100, do_not_submit=True
		)
		row = receipt.items[0]
		row.serial_no = "\n".join(serials)
		row.use_serial_batch_fields = 1
		receipt.save()

		inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"item_code": item.name,
				"quality_inspection_template": template.name,
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		inspection.insert(ignore_permissions=True)

		# the unit readings carry the unborn typed serials, vouched for by the row
		inspection.populate_units()
		self.assertEqual([entry.serial_no for entry in inspection.unit_readings], serials)
		for entry in inspection.unit_readings:
			entry.reading_value = "no" if entry.serial_no == serials[1] else "Yes"
		inspection.save(ignore_permissions=True)
		inspection.submit()

		receipt.reload()
		outcomes = get_inspection_outcomes(receipt.as_dict())

		# the verdict becomes the row's split: 2 accepted, 1 rejected, with the
		# rejected serial moved to the rejected serial field
		self.assertEqual(len(outcomes), 1)
		outcome = outcomes[0]
		self.assertEqual(outcome["qty"], 2)
		self.assertEqual(outcome["rejected_qty"], 1)
		self.assertEqual(outcome["serial_no"].split("\n"), [serials[0], serials[2]])
		self.assertEqual(outcome["rejected_serial_no"], serials[1])

		# applying the split and asking again proposes nothing further
		row = receipt.items[0]
		row.rejected_qty = 1
		row.qty = 2
		row.serial_no = outcome["serial_no"]
		row.rejected_serial_no = outcome["rejected_serial_no"]
		self.assertEqual(get_inspection_outcomes(receipt.as_dict()), [])

	def test_purchase_return_created_from_the_lot(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.services.quality_returns import make_purchase_return_for_lot

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

	def test_return_books_against_its_own_receipts_lot(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		qc = make_qc_warehouse("_Test QC Own Lot WH")
		item = make_item(properties={"is_stock_item": 1})
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

		def receive_and_reject():
			receipt = make_purchase_receipt(item_code=item.name, qty=2, warehouse=qc, rate=100)
			lot = quality_control_lots_for(receipt.name, "Purchase Receipt")[0].name
			submit_inspection_for_lot(lot, status="Rejected")
			return receipt, lot

		_first_receipt, first_lot = receive_and_reject()
		second_receipt, second_lot = receive_and_reject()

		# the return is against the second receipt: it books against that
		# receipt's lot, not the oldest lot of the same item in the warehouse
		return_doc = make_return_doc("Purchase Receipt", second_receipt.name)
		return_doc.insert()
		return_doc.submit()

		self.assertEqual(frappe.db.get_value("Quality Control Lot", first_lot, "returned_qty"), 0)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", second_lot, "returned_qty"), 2)

	def test_inspected_item_must_be_on_the_reference(self):
		# the form's picker only offers the reference's items; the server is
		# the authority — an unrelated item cannot decide a lot or a document
		qc = make_qc_warehouse("_Test QC Wrong Item WH")
		item = make_quarantine_item(qc)
		stranger = make_item(properties={"is_stock_item": 1}).name

		se = make_stock_entry(item_code=item, qty=1, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		def build(reference_type, reference_name):
			return frappe.get_doc(
				{
					"doctype": "Quality Inspection",
					"inspection_type": "Incoming",
					"reference_type": reference_type,
					"reference_name": reference_name,
					"item_code": stranger,
					"sample_size": 1,
					"report_date": nowdate(),
					"inspected_by": frappe.session.user,
				}
			)

		self.assertRaises(frappe.ValidationError, build("Quality Control Lot", lot).insert)
		self.assertRaises(frappe.ValidationError, build("Stock Entry", se.name).insert)

	def test_each_quantity_refuses_fractional_quantities(self):
		from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import trigger_row

		qc = make_qc_warehouse("_Test QC Fractional WH")
		item_doc = make_item(properties={"is_stock_item": 1, "stock_uom": "Kg"})
		item_doc.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				warehouse_role="Inbound",
				quality_control_mode="Quarantine",
				applicable_warehouse=qc,
			),
		)
		item_doc.save()
		item = item_doc.name
		se = make_stock_entry(item_code=item, qty=2.5, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		# 2.5 units cannot be read per unit — rounding would quietly leave a
		# fraction undecided forever
		fractional = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"reference_type": "Quality Control Lot",
				"reference_name": lot,
				"item_code": item,
				"inspection_basis": "Each Quantity",
				"report_date": nowdate(),
				"inspected_by": frappe.session.user,
			}
		)
		self.assertRaises(frappe.ValidationError, fractional.insert)

		# the Sample basis decides fractional stock fine
		submit_inspection_for_lot(lot)
		self.assertEqual(frappe.db.get_value("Quality Control Lot", lot, "decided_qty"), 2.5)

	def test_pending_inspection_reminder_notifies_quality_managers(self):
		from erpnext.stock.services.quality_quarantine import remind_pending_quality_inspections

		qc = make_qc_warehouse("_Test QC Reminder WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=3, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name

		manager = "_test_quality_manager@example.com"
		if not frappe.db.exists("User", manager):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": manager,
					"first_name": "Quality",
					"roles": [{"role": "Quality Manager"}],
				}
			).insert(ignore_permissions=True)

		frappe.db.set_single_value("Stock Settings", "pending_quality_inspection_reminder_days", 2)

		frappe.db.set_value(
			"Quality Control Lot",
			lot,
			"creation",
			frappe.utils.add_days(nowdate(), -3),
			update_modified=False,
		)
		frappe.db.delete("Notification Log", {"for_user": manager})
		remind_pending_quality_inspections()
		self.assertEqual(frappe.db.count("Notification Log", {"for_user": manager}), 0)

		frappe.db.set_value(
			"Quality Control Lot",
			lot,
			"source_posting_datetime",
			frappe.utils.add_days(nowdate(), -3),
			update_modified=False,
		)

		frappe.db.delete("Notification Log", {"for_user": manager})
		remind_pending_quality_inspections()

		notifications = frappe.get_all("Notification Log", filters={"for_user": manager}, fields=["subject"])
		self.assertEqual(len(notifications), 1)
		self.assertIn("awaiting inspection", notifications[0].subject)

		# a decided lot stops nagging
		frappe.db.delete("Notification Log", {"for_user": manager})
		submit_inspection_for_lot(lot)
		remind_pending_quality_inspections()
		self.assertEqual(frappe.db.count("Notification Log", {"for_user": manager}), 0)
		frappe.db.set_single_value("Stock Settings", "pending_quality_inspection_reminder_days", 0)

	def test_quality_reports_run(self):
		from erpnext.stock.report.quality_inspection_turnaround.quality_inspection_turnaround import (
			execute as turnaround,
		)
		from erpnext.stock.report.quality_rejection_analysis.quality_rejection_analysis import (
			execute as rejection_analysis,
		)

		qc = make_qc_warehouse("_Test QC Reports WH")
		item = make_quarantine_item(qc)
		se = make_stock_entry(item_code=item, qty=4, to_warehouse=qc, purpose="Material Receipt", rate=100)
		lot = quality_control_lots_for(se.name)[0].name
		submit_inspection_for_lot(lot, unit_results={1: ["Accepted"], 2: ["Rejected"]})

		_columns, rows = rejection_analysis({"group_by": "Item", "item_code": item})
		row = next(r for r in rows if r["group_value"] == item)
		self.assertEqual(row["rejected_qty"], 1)

		_columns, rows = rejection_analysis({"group_by": "Parameter"})
		self.assertTrue(any(r["rejections"] >= 1 for r in rows))

		_columns, rows = turnaround({"item_code": item})
		row = next(r for r in rows if r["quality_control_lot"] == lot)
		self.assertEqual(row["undecided_qty"], 2)
		self.assertIsNotNone(row["first_verdict_on"])
		self.assertIsNone(row["fully_decided_on"])

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
