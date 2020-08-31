# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
import frappe
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

