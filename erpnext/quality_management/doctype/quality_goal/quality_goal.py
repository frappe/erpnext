# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class QualityGoal(Document):
	def create_review(self):
		objectives = frappe.get_all("Quality Objective", filters={'parent': ''+ self.name +''}, fields=['objective', 'target', 'unit'])
		doc = frappe.get_doc({
			"doctype": "Quality Review",
			"goal": self.name,
			"date": frappe.utils.nowdate(),
			"measurable": self.measurable,
		})
		for objective in objectives:
			print(self.measurable, objective.objective, objective.target, objective.unit)
		if self.measurable == 'Yes':
			for objective in objectives:
				doc.append("values",{
					'objective': objective.objective,
					'target': objective.target,
					'achieved': 0,
					'unit': objective.unit
				})
		else:
			for objective in objectives:
				doc.append("values",{
					'objective': objective.objective,
				})
		doc.insert()
		frappe.db.commit()

