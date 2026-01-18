# Copyright (c) 2018, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from .quality_procedure import add_node


class TestQualityProcedure(IntegrationTestCase):
	def test_add_node(self):
		procedure = create_procedure(
			{
				"quality_procedure_name": "Test Procedure 1",
				"is_group": 1,
				"processes": [dict(process_description="Test Step 1")],
			}
		)

		frappe.local.form_dict = frappe._dict(
			doctype="Quality Procedure",
			quality_procedure_name="Test Child 1",
			parent_quality_procedure=procedure.name,
			cmd="test",
			is_root="false",
		)
		node = add_node()

		procedure.reload()

		self.assertEqual(procedure.is_group, 1)

		# child row created
		self.assertTrue([d for d in procedure.processes if d.procedure == node.name])

		node.delete()
		procedure.reload()

		# child unset
		self.assertFalse([d for d in procedure.processes if d.name == node.name])

	def test_remove_parent_from_old_child(self):
		child_qp = create_procedure(
			{
				"quality_procedure_name": "Test Child 1",
				"is_group": 0,
			}
		)
		group_qp = create_procedure(
			{
				"quality_procedure_name": "Test Group",
				"is_group": 1,
				"processes": [dict(procedure=child_qp.name)],
			}
		)

		child_qp.reload()
		self.assertEqual(child_qp.parent_quality_procedure, group_qp.name)

		group_qp.reload()
		del group_qp.processes[0]
		group_qp.save()

		child_qp.reload()
		self.assertEqual(child_qp.parent_quality_procedure, None)

	def remove_child_from_old_parent(self):
		child_qp = create_procedure(
			{
				"quality_procedure_name": "Test Child 1",
				"is_group": 0,
			}
		)
		group_qp = create_procedure(
			{
				"quality_procedure_name": "Test Group",
				"is_group": 1,
				"processes": [dict(procedure=child_qp.name)],
			}
		)

		group_qp.reload()
		self.assertTrue([d for d in group_qp.processes if d.procedure == child_qp.name])

		child_qp.reload()
		self.assertEqual(child_qp.parent_quality_procedure, group_qp.name)

		child_qp.parent_quality_procedure = None
		child_qp.save()

		group_qp.reload()
		self.assertFalse([d for d in group_qp.processes if d.procedure == child_qp.name])


def create_procedure(kwargs=None):
	kwargs = frappe._dict(kwargs or {})

	doc = frappe.new_doc("Quality Procedure")
	doc.quality_procedure_name = kwargs.quality_procedure_name or "_Test Procedure"
	doc.is_group = kwargs.is_group or 0

	for process in kwargs.processes or []:
		doc.append("processes", process)

	doc.insert()

	return doc
