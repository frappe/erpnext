from frappe.tests import IntegrationTestCase

from erpnext.utilities.activation import get_level


class TestActivation(IntegrationTestCase):
	def test_activation(self):
		levels = get_level()
		self.assertTrue(levels)
