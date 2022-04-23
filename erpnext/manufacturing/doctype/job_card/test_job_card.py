# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
import frappe
from frappe.utils import random_string
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.job_card.job_card import OperationMismatchError

class TestJobCard(unittest.TestCase):
	def test_job_card(self):
		data = frappe.get_cached_value('BOM',
			{'docstatus': 1, 'with_operations': 1, 'company': '_Test Company'}, ['name', 'item'])

		if data:
			bom, bom_item = data

			work_order = make_wo_order_test_record(item=bom_item, qty=1, bom_no=bom)

			job_cards = frappe.get_all('Job Card',
				filters = {'work_order': work_order.name}, fields = ["operation_id", "name"])

			if job_cards:
				job_card = job_cards[0]
				frappe.db.set_value("Job Card", job_card.name, "operation_row_number", job_card.operation_id)

				doc = frappe.get_doc("Job Card", job_card.name)
				doc.operation_id = "Test Data"
				self.assertRaises(OperationMismatchError, doc.save)

			for d in job_cards:
				frappe.delete_doc("Job Card", d.name)

	def test_job_card_with_different_work_station(self):
		data = frappe.get_cached_value('BOM',
			{'docstatus': 1, 'with_operations': 1, 'company': '_Test Company'}, ['name', 'item'])

		if data:
			bom, bom_item = data

			work_order = make_wo_order_test_record(item=bom_item, qty=1, bom_no=bom)

			job_cards = frappe.get_all('Job Card',
				filters = {'work_order': work_order.name},
				fields = ["operation_id", "workstation", "name", "for_quantity"])

			job_card = job_cards[0]

			if job_card:
				workstation = frappe.db.get_value("Workstation",
					{"name": ("not in", [job_card.workstation])}, "name")

				if not workstation or job_card.workstation == workstation:
					workstation = make_workstation(workstation_name=random_string(5)).name

				doc = frappe.get_doc("Job Card", job_card.name)
				doc.workstation = workstation
				doc.append("time_logs", {
					"from_time": "2009-01-01 12:06:25",
					"to_time": "2009-01-01 12:37:25",
					"time_in_mins": "31.00002",
					"completed_qty": job_card.for_quantity
				})
				doc.submit()

				completed_qty = frappe.db.get_value("Work Order Operation", job_card.operation_id, "completed_qty")
				self.assertEqual(completed_qty, job_card.for_quantity)

				doc.cancel()

			for d in job_cards:
				frappe.delete_doc("Job Card", d.name)