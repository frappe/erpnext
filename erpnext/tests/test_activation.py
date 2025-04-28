<<<<<<< HEAD
from frappe.tests import IntegrationTestCase
=======
from frappe.tests.utils import FrappeTestCase
>>>>>>> 7c4cf3e834 (Favicon.svg)

from erpnext.utilities.activation import get_level


<<<<<<< HEAD
class TestActivation(IntegrationTestCase):
	def test_activation(self):
		site_info = {"activation": {"activation_level": 0, "sales_data": []}}
		levels = get_level(site_info)
=======
class TestActivation(FrappeTestCase):
	def test_activation(self):
		levels = get_level()
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.assertTrue(levels)
