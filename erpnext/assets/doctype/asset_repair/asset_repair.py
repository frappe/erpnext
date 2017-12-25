# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import time_diff_in_hours
from frappe.model.document import Document

class AssetRepair(Document):
	def validate(self):
		if self.repair_status == "Completed" and not self.completion_date:
			frappe.throw(_("Please select Completion Date for Completed Repair"))


@frappe.whitelist()
def get_downtime(failure_date, completion_date):
	downtime = time_diff_in_hours(completion_date, failure_date)
	return round(downtime, 2)