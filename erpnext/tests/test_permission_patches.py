import frappe
from frappe.core.page.permission_manager.permission_manager import remove
from frappe.permissions import setup_custom_perms

from erpnext.patches.v16_0 import (
	mirror_release_perms_to_custom_docperm,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestPermissionPatches(ERPNextTestSuite):
	def tearDown(self):
		super().tearDown()
		for doctype in ("Payment Term", "Account", "Payment Terms Template", "Address"):
			frappe.clear_cache(doctype=doctype)

	def custom_rule(self, doctype, role):
		return frappe.db.get_value(
			"Custom DocPerm",
			{"parent": doctype, "role": role, "permlevel": 0},
			["select", "read"],
			as_dict=True,
		)

	def test_mirror_leaves_an_admin_removed_pair_alone(self):
		setup_custom_perms("Payment Term")
		remove("Payment Term", "Manufacturing Manager", 0)
		mirror_release_perms_to_custom_docperm.execute()
		self.assertIsNone(self.custom_rule("Payment Term", "Manufacturing Manager"))
