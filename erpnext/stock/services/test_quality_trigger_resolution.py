# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate

from erpnext.controllers.stock_controller import check_item_quality_inspection
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.item_quality_trigger.test_item_quality_trigger import (
	create_test_item_group,
	trigger_row,
)
from erpnext.stock.services.quality_trigger_resolution import (
	INBOUND,
	OUTBOUND,
	enforce_inspection_points,
	movements_of,
	resolve_inspection_points,
	resolve_job_card_inspection,
)
from erpnext.stock.services.test_quality_warehouse import make_warehouse
from erpnext.tests.utils import ERPNextTestSuite

REAL_WH = "_Test Warehouse - _TC"


def pr_doc(item_code, warehouse=REAL_WH, qty=5):
	# lightweight stand-in for a Purchase Receipt; resolution reads item rows and
	# warehouses, not a persisted document
	return frappe._dict(
		doctype="Purchase Receipt",
		items=[frappe._dict(item_code=item_code, warehouse=warehouse, qty=qty, stock_qty=qty)],
	)


class TestQualityTriggerResolution(ERPNextTestSuite):
	def test_movements_decomposition_and_update_stock_gating(self):
		# a Stock Entry transfer exposes both directions
		se = frappe._dict(
			doctype="Stock Entry",
			items=[frappe._dict(item_code="X", s_warehouse="A", t_warehouse="B", qty=1)],
		)
		self.assertEqual({role for _r, role, _w in movements_of(se)}, {INBOUND, OUTBOUND})

		# a Sales Invoice only moves stock when update_stock is set
		si = frappe._dict(
			doctype="Sales Invoice",
			update_stock=0,
			items=[frappe._dict(item_code="X", warehouse="A", qty=1)],
		)
		self.assertEqual(list(movements_of(si)), [])
		si.update_stock = 1
		self.assertEqual(next(movements_of(si))[1], OUTBOUND)

	def test_returns_reverse_the_movement_direction(self):
		# a customer return on a Delivery Note brings stock back in
		dn_return = frappe._dict(
			doctype="Delivery Note",
			is_return=1,
			items=[frappe._dict(item_code="X", warehouse=REAL_WH, qty=-1)],
		)
		self.assertEqual(next(movements_of(dn_return))[1], INBOUND)

		# a purchase return sends stock back out
		pr_return = frappe._dict(
			doctype="Purchase Receipt",
			is_return=1,
			items=[frappe._dict(item_code="X", warehouse=REAL_WH, qty=-1)],
		)
		self.assertEqual(next(movements_of(pr_return))[1], OUTBOUND)

	def test_inbound_trigger_matches_delivery_note_return(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Delivery Note", warehouse_role="Inbound", quality_control_mode="Block"
			),
		)
		item.save()

		# the return (inbound) matches…
		dn_return = frappe._dict(
			doctype="Delivery Note",
			is_return=1,
			items=[frappe._dict(item_code=item.name, warehouse=REAL_WH, qty=-1, idx=1)],
		)
		self.assertEqual(len(resolve_inspection_points(dn_return)), 1)

		# …while the normal delivery (outbound) does not
		self.assertEqual(resolve_inspection_points(dn_doc(item.name, docstatus=0)), [])

	def test_transit_warehouse_legs_are_skipped(self):
		transit = make_warehouse("_Test Transit WH", warehouse_type="Transit")

		# first transit entry (real source -> transit): only the source-out leg counts
		first = frappe._dict(
			doctype="Stock Entry",
			items=[frappe._dict(item_code="X", s_warehouse=REAL_WH, t_warehouse=transit)],
		)
		self.assertEqual([(role, wh) for _r, role, wh in movements_of(first)], [(OUTBOUND, REAL_WH)])

		# end transit entry (transit -> real target): only the target-in leg counts
		end = frappe._dict(
			doctype="Stock Entry",
			items=[frappe._dict(item_code="X", s_warehouse=transit, t_warehouse=REAL_WH)],
		)
		self.assertEqual([(role, wh) for _r, role, wh in movements_of(end)], [(INBOUND, REAL_WH)])

	def test_resolves_item_level_trigger(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row())  # Purchase Receipt / Inbound
		item.save()

		points = resolve_inspection_points(pr_doc(item.name))
		self.assertEqual(len(points), 1)
		self.assertEqual(points[0].quality_control_mode, "Quarantine")
		self.assertEqual(points[0].role, INBOUND)

	def test_no_trigger_yields_no_points(self):
		item = make_item(properties={"is_stock_item": 1})
		self.assertEqual(resolve_inspection_points(pr_doc(item.name)), [])

	def test_item_group_inheritance(self):
		group = create_test_item_group("_Test QC Resolution Group")
		doc = frappe.get_doc("Item Group", group)
		doc.set("quality_triggers", [])
		doc.append("quality_triggers", trigger_row())
		doc.save()

		item = make_item(properties={"is_stock_item": 1, "item_group": group})
		self.assertEqual(len(resolve_inspection_points(pr_doc(item.name))), 1)

	def test_item_level_overrides_item_group(self):
		group = create_test_item_group("_Test QC Override Group")
		doc = frappe.get_doc("Item Group", group)
		doc.set("quality_triggers", [])
		doc.append("quality_triggers", trigger_row(quality_control_mode="Monitor"))
		doc.save()

		item = make_item(properties={"is_stock_item": 1, "item_group": group})
		item.append("quality_triggers", trigger_row(quality_control_mode="Quarantine"))
		item.save()

		points = resolve_inspection_points(pr_doc(item.name))
		self.assertEqual(len(points), 1)
		self.assertEqual(points[0].quality_control_mode, "Quarantine")  # most-specific (item) wins

	def test_applicable_warehouse_filters_movements(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row(applicable_warehouse=REAL_WH))
		item.save()

		# movement into a different warehouse does not match
		self.assertEqual(resolve_inspection_points(pr_doc(item.name, warehouse="_Other - _TC")), [])
		# movement into the applicable warehouse matches
		self.assertEqual(len(resolve_inspection_points(pr_doc(item.name, warehouse=REAL_WH))), 1)


def dn_doc(item_code, quality_inspection=None, docstatus=1):
	# lightweight stand-in for a submitting Delivery Note
	return frappe._dict(
		doctype="Delivery Note",
		docstatus=docstatus,
		items=[
			frappe._dict(
				item_code=item_code,
				warehouse=REAL_WH,
				qty=1,
				idx=1,
				quality_inspection=quality_inspection,
			)
		],
	)


def make_submitted_inspection(item_code):
	qi = frappe.get_doc(
		{
			"doctype": "Quality Inspection",
			"inspection_type": "Outgoing",
			"reference_type": "Delivery Note",
			"reference_name": "_Test QC Reference",
			"item_code": item_code,
			"sample_size": 1,
			"report_date": nowdate(),
			"inspected_by": frappe.session.user,
		}
	)
	qi.flags.ignore_links = True
	qi.insert(ignore_permissions=True, ignore_links=True)
	qi.submit()
	return qi.name


class TestInspectionEnforcement(ERPNextTestSuite):
	def _item_with_outbound_trigger(self, quality_control_mode):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Delivery Note",
				quality_control_mode=quality_control_mode,
				warehouse_role="Outbound",
			),
		)
		item.save()
		return item.name

	def test_block_stops_submission_without_inspection(self):
		item = self._item_with_outbound_trigger("Block")
		self.assertRaises(frappe.ValidationError, enforce_inspection_points, dn_doc(item))

	def test_block_allows_submission_with_submitted_inspection(self):
		item = self._item_with_outbound_trigger("Block")
		qi = make_submitted_inspection(item)
		enforce_inspection_points(dn_doc(item, quality_inspection=qi))  # no exception

	def test_warn_does_not_block_submission(self):
		item = self._item_with_outbound_trigger("Warn")
		enforce_inspection_points(dn_doc(item))  # warns, but does not raise


class TestJobCardInspection(ERPNextTestSuite):
	def _job_card_item(self, inspection_point):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Job Card",
				warehouse_role=None,  # auto-set to Inbound
				quality_control_mode="Block",
				job_card_inspection_point=inspection_point,
			),
		)
		item.save()
		return item.name

	def job_card(self, finished_good, track_semi_finished_goods=1):
		return frappe._dict(
			doctype="Job Card",
			track_semi_finished_goods=track_semi_finished_goods,
			finished_good=finished_good,
			target_warehouse=REAL_WH,
		)

	def test_requires_track_semi_finished_goods(self):
		item = self._job_card_item("Every Job Card")
		card = self.job_card(item, track_semi_finished_goods=0)
		self.assertIsNone(resolve_job_card_inspection(card, production_item=item))

	def test_every_job_card_matches_intermediate_and_final(self):
		item = self._job_card_item("Every Job Card")
		card = self.job_card(item)
		# matches whether or not this job card produces the final output
		self.assertIsNotNone(resolve_job_card_inspection(card, production_item=item))
		self.assertIsNotNone(resolve_job_card_inspection(card, production_item="SOME-OTHER-ITEM"))

	def test_final_output_only_matches_just_the_final_job_card(self):
		item = self._job_card_item("Final Output Only")
		card = self.job_card(item)
		# intermediate operation (finished good != production item): no inspection
		self.assertIsNone(resolve_job_card_inspection(card, production_item="SOME-OTHER-ITEM"))
		# final operation: inspection required
		trigger = resolve_job_card_inspection(card, production_item=item)
		self.assertIsNotNone(trigger)
		self.assertEqual(trigger.quality_control_mode, "Block")


class TestMakeInspectionButton(ERPNextTestSuite):
	def test_only_triggered_items_are_offered(self):
		triggered = make_item(properties={"is_stock_item": 1})
		triggered.append("quality_triggers", trigger_row())  # Purchase Receipt
		triggered.save()
		plain = make_item(properties={"is_stock_item": 1})

		result = check_item_quality_inspection(
			"Purchase Receipt", 0, [{"item_code": triggered.name}, {"item_code": plain.name}]
		)
		self.assertEqual({i["item_code"] for i in result}, {triggered.name})

	def test_trigger_for_other_doctype_is_not_offered(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row())  # Purchase Receipt only
		item.save()

		# a Delivery Note should offer nothing for this item
		self.assertEqual(check_item_quality_inspection("Delivery Note", 0, [{"item_code": item.name}]), [])

	def test_stale_client_inspection_link_is_refreshed_from_the_database(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(document_type="Stock Entry", warehouse_role="Inbound", quality_control_mode="Block"),
		)
		item.save()

		entry = make_stock_entry(
			item_code=item.name, qty=1, to_warehouse=REAL_WH, purpose="Material Receipt", do_not_submit=True
		)

		# the browser still carries a link to an inspection cancelled meanwhile;
		# the database row has none, so the item must be offered again
		stale_row = {
			"item_code": item.name,
			"name": entry.items[0].name,
			"quality_inspection": "MAT-QA-STALE",
		}
		offered = check_item_quality_inspection("Stock Entry", 0, [stale_row])
		self.assertEqual(len(offered), 1)
		self.assertFalse(offered[0]["quality_inspection"])

	def test_offered_items_carry_their_inspection_basis(self):
		from erpnext.stock.services.quality_trigger_resolution import get_inspection_basis

		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row(inspection_basis="Each Quantity"))
		item.save()

		self.assertEqual(get_inspection_basis(item.name, "Purchase Receipt"), "Each Quantity")
		offered = check_item_quality_inspection("Purchase Receipt", 0, [{"item_code": item.name}])
		self.assertEqual(offered[0]["inspection_basis"], "Each Quantity")
		# no trigger for the doctype falls back to a sample inspection
		self.assertEqual(get_inspection_basis(item.name, "Delivery Note"), "Sample")
