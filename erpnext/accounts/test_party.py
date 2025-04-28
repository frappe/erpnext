import frappe
<<<<<<< HEAD
from frappe.tests import IntegrationTestCase
=======
from frappe.tests.utils import FrappeTestCase
>>>>>>> 7c4cf3e834 (Favicon.svg)

from erpnext.accounts.party import get_default_price_list


<<<<<<< HEAD
class PartyTestCase(IntegrationTestCase):
=======
class PartyTestCase(FrappeTestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	def test_get_default_price_list_should_return_none_for_invalid_group(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "test customer",
			}
		).insert(ignore_permissions=True, ignore_mandatory=True)
		customer.customer_group = None
		customer.save()
		price_list = get_default_price_list(customer)
		assert price_list is None
