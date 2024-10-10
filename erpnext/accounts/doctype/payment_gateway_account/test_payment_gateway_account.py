# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

from frappe.tests import IntegrationTestCase

# test_records = frappe.get_test_records('Payment Gateway Account')

IGNORE_TEST_RECORD_DEPENDENCIES = ["Payment Gateway"]


class TestPaymentGatewayAccount(IntegrationTestCase):
	pass
