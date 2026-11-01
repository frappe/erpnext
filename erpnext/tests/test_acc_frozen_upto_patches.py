# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate

from erpnext.patches.v14_0.single_to_multi_dunning import get_accounts_closing_date
from erpnext.patches.v15_0.recalculate_amount_difference_field import get_acc_frozen_upto
from erpnext.tests.utils import ERPNextTestSuite

FROZEN_UPTO = "2099-12-31"


class TestAccFrozenUptoPatches(ERPNextTestSuite):
	"""Post-sync patches must still see the legacy freeze date left in tabSingles."""

	def setUp(self):
		singles = frappe.qb.DocType("Singles")
		condition = (singles.doctype == "Accounts Settings") & (singles.field == "acc_frozen_upto")
		frappe.qb.from_(singles).delete().where(condition).run()
		frappe.qb.into(singles).columns("doctype", "field", "value").insert(
			"Accounts Settings", "acc_frozen_upto", FROZEN_UPTO
		).run()

	def test_patches_read_legacy_freeze_date(self):
		self.assertFalse(frappe.get_meta("Accounts Settings").has_field("acc_frozen_upto"))
		self.assertEqual(get_accounts_closing_date(), getdate(FROZEN_UPTO))
		self.assertEqual(get_acc_frozen_upto(), getdate(FROZEN_UPTO))
