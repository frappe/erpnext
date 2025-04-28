# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
<<<<<<< HEAD
import unittest

from frappe.tests import IntegrationTestCase

IGNORE_TEST_RECORD_DEPENDENCIES = ["Payment Gateway"]


class TestPaymentGatewayAccount(IntegrationTestCase):
=======

import unittest

# test_records = frappe.get_test_records('Payment Gateway Account')

test_ignore = ["Payment Gateway"]


class TestPaymentGatewayAccount(unittest.TestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	pass
