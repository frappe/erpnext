# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
<<<<<<< HEAD
from frappe.tests import IntegrationTestCase
=======
from frappe.tests.utils import FrappeTestCase
>>>>>>> 7c4cf3e834 (Favicon.svg)
from frappe.utils import add_days, today

from erpnext.maintenance.doctype.maintenance_schedule.test_maintenance_schedule import (
	make_serial_item_with_serial,
)


<<<<<<< HEAD
class TestStockLedgerReeport(IntegrationTestCase):
	def setUp(self) -> None:
		make_serial_item_with_serial(self, "_Test Stock Report Serial Item")
=======
class TestStockLedgerReeport(FrappeTestCase):
	def setUp(self) -> None:
		make_serial_item_with_serial("_Test Stock Report Serial Item")
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.filters = frappe._dict(
			company="_Test Company",
			from_date=today(),
			to_date=add_days(today(), 30),
<<<<<<< HEAD
			item_code=["_Test Stock Report Serial Item"],
=======
			item_code="_Test Stock Report Serial Item",
>>>>>>> 7c4cf3e834 (Favicon.svg)
		)

	def tearDown(self) -> None:
		frappe.db.rollback()
