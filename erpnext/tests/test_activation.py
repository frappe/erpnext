from frappe.tests.utils import FrappeTestCase

from erpnext.utilities.activation import get_level


class TestActivation(FrappeTestCase):
	def test_activation(self):
		site_info = {"activation": {"activation_level": 0, "sales_data": []}}
		levels = get_level(site_info)
		self.assertTrue(levels)
