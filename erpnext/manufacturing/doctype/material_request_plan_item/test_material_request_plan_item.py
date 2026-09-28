# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.patches.v15_0 import set_main_item_code_in_material_request_plan_item as patch_module
from erpnext.tests.utils import ERPNextTestSuite


class TestMaterialRequestPlanItem(ERPNextTestSuite):
	def test_main_item_code_patch_uses_bulk_update(self):
		rows = [
			frappe._dict(name="ROW-1", main_item_code=None),
			frappe._dict(name="ROW-2", main_item_code="EXISTING"),
			frappe._dict(name="ROW-3", main_item_code=None),
		]

		with (
			patch.object(frappe, "reload_doc"),
			patch.object(frappe.db, "has_column", return_value=True),
			patch.object(frappe.db, "bulk_update") as bulk_update,
			patch.object(patch_module, "get_material_request_plan_items", return_value=rows),
			patch.object(patch_module, "get_main_item_code", side_effect=["ITEM-1", None]),
		):
			patch_module.execute()

		bulk_update.assert_called_once_with(
			"Material Request Plan Item",
			{"ROW-1": {"main_item_code": "ITEM-1"}},
			update_modified=False,
		)
