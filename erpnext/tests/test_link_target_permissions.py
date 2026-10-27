import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission, remove_user_permission

from erpnext.tests.utils import ERPNextTestSuite


class TestLinkTargetSelectPermissions(ERPNextTestSuite):
	"""A role that can write a form must be able to use that form's link pickers.

	The DocPerm rows behind this grant `select` on the link target and nothing else, so
	each case asserts both halves: the picker fills, and no `read` arrives with it.
	Support Team on Lead stands in for the 313 rows; it holds no other right on Lead.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user = create_user("_test_link_target_select@example.com", "Support Team").name
		cls.lead = cls.make_lead("_Test Link Target Lead")
		cls.other_lead = cls.make_lead("_Test Link Target Lead 2")

	@staticmethod
	def make_lead(lead_name):
		if existing := frappe.db.get_value("Lead", {"lead_name": lead_name}):
			return existing

		return (
			frappe.get_doc({"doctype": "Lead", "lead_name": lead_name}).insert(ignore_permissions=True).name
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_granted_role_can_search_the_link_target(self):
		frappe.set_user(self.user)

		self.assertTrue(frappe.has_permission("Lead", "select"))
		self.assertIn(self.lead, frappe.get_list("Lead", pluck="name"))

	def test_select_does_not_grant_read(self):
		self.assertFalse(frappe.has_permission("Lead", "read", user=self.user))
		self.assertFalse(frappe.has_permission("Lead", "write", user=self.user))

	def test_select_exposes_search_fields_only(self):
		frappe.set_user(self.user)

		row = frappe.get_list("Lead", filters={"name": self.lead}, fields=["name", "email_id"])[0]

		# email_id is not a Lead search field, so a select-only role never receives it
		self.assertIn("name", row)
		self.assertNotIn("email_id", row)

	def test_doctype_without_a_grant_stays_denied(self):
		frappe.set_user(self.user)

		self.assertRaises(frappe.PermissionError, frappe.get_list, "Sales Invoice")

	def test_user_permissions_still_filter_a_select_only_target(self):
		add_user_permission("Lead", self.lead, self.user)
		try:
			frappe.set_user(self.user)
			self.assertEqual(frappe.get_list("Lead", pluck="name"), [self.lead])
		finally:
			frappe.set_user("Administrator")
			remove_user_permission("Lead", self.lead, self.user)
