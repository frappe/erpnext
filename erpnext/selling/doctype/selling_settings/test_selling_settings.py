# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from erpnext.tests.utils import ERPNextTestSuite
from unittest.mock import patch

class TestSellingSettings(ERPNextTestSuite):
    def test_defaults_populated(self):
        # Setup default values are not populated on migrate, this test checks
        # if setup was completed correctly
        default = frappe.db.get_single_value("Selling Settings", "maintain_same_rate_action")
        self.assertEqual("Stop", default)

    def test_validate_allows_insert_when_no_prior_doc(self):
        class_under_test = frappe.get_doc({
            "doctype": "Selling Settings",
            "enable_discount_accounting": 1,
            "enable_tracking_sales_commissions": 1,
            "enable_utm": 1,
            "fallback_to_default_price_list": 1,
            "hide_tax_id": 1,
            "maintain_same_rate_action": "Stop",
            "maintain_same_sales_rate": 1,
            "sales_update_frequency": "Monthly",
            "use_legacy_js_reactivity": 1,
            "validate_selling_price": 1,
        })

        # monkeypatch get_doc_before_save here is unnecessary but added for safety;
        # if other tests in future override, we need to ensure this test is not affected
        class_under_test.get_doc_before_save = lambda: None

        try:
            # Use insert instead of validate to test the whole flow,
            # since validate is called by insert
            class_under_test.insert()
        except Exception as exc:
            self.fail(f"validate() raised an unexpected exception: {exc}")
    
    @patch("erpnext.selling.doctype.selling_settings.selling_settings.toggle_tracking_sales_commissions_section")
    @patch("erpnext.selling.doctype.selling_settings.selling_settings.toggle_utm_analytics_section")
    def test_validate_doesnt_call_toggle_functions_when_old_doc_is_None(self, mock_toggle_tracking_sales_commissions_section, mock_toggle_utm):
        class_under_test = frappe.get_doc({
            "doctype": "Selling Settings",
            "enable_discount_accounting": 1,
            "enable_tracking_sales_commissions": 1,
            "enable_utm": 1,
            "fallback_to_default_price_list": 1,
            "hide_tax_id": 1,
            "maintain_same_rate_action": "Stop",
            "maintain_same_sales_rate": 1,
            "sales_update_frequency": "Monthly",
            "use_legacy_js_reactivity": 1,
            "validate_selling_price": 1,
        })
          
        # monkeypatch get_doc_before_save here is unnecessary but added for safety;
        # if other tests in future override, we need to ensure this test is not affected
        class_under_test.get_doc_before_save = lambda: None

        class_under_test.insert()
        mock_toggle_tracking_sales_commissions_section.assert_not_called()
        mock_toggle_utm.assert_not_called()

    @patch("erpnext.selling.doctype.selling_settings.selling_settings.toggle_tracking_sales_commissions_section")
    @patch("erpnext.selling.doctype.selling_settings.selling_settings.toggle_utm_analytics_section")
    def test_validate_doesnt_call_toggle_functions_when_old_doc_has_same_values(self, mock_toggle_tracking_sales_commissions_section, mock_toggle_utm):
        class_under_test = frappe.get_doc({
            "doctype": "Selling Settings",
            "enable_discount_accounting": 1,
            "enable_tracking_sales_commissions": 1,
            "enable_utm": 1,
            "fallback_to_default_price_list": 1,
            "hide_tax_id": 1,
            "maintain_same_rate_action": "Stop",
            "maintain_same_sales_rate": 1,
            "sales_update_frequency": "Monthly",
            "use_legacy_js_reactivity": 1,
            "validate_selling_price": 1,
        })
          
        # monkeypatch get_doc_before_save here is unnecessary but added for safety;
        # if other tests in future override, we need to ensure this test is not affected
        class_under_test.get_doc_before_save = lambda: class_under_test

        class_under_test.insert()
        mock_toggle_tracking_sales_commissions_section.assert_not_called()
        mock_toggle_utm.assert_not_called()
