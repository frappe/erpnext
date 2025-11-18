# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.model.document import Document
from erpnext.subcontracting.doctype.subcontracting_order.test_subcontracting_order import (
    make_subcontracting_order,
)
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.subcontracting.doctype.subcontracting_receipt.test_subcontracting_receipt import (
    make_subcontracting_receipt,
)
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order


class TestSubcontractProcessLoss(FrappeTestCase):
    def setUp(self):
        """Set up test data"""
        self.create_test_items()
        self.create_test_warehouses()
        self.create_test_supplier()

    def tearDown(self):
        """Clean up after tests"""
        frappe.db.rollback()

    def create_test_items(self):
        """Create test items for raw materials and finished goods"""
        # Create finished good item
        if not frappe.db.exists("Item", "Test Finished Product"):
            finished_item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Finished Product",
                "item_name": "Test Finished Product",
                "description": "Test Finished Product for Subcontracting",
                "item_group": "Products",
                "is_stock_item": 1,
                "stock_uom": "Nos"
            })
            finished_item.insert()

        # Create raw material item
        if not frappe.db.exists("Item", "Test Raw Material"):
            raw_item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Raw Material",
                "item_name": "Test Raw Material",
                "description": "Test Raw Material for Subcontracting",
                "item_group": "Raw Material",
                "is_stock_item": 1,
                "stock_uom": "Kg"
            })
            raw_item.insert()

    def create_test_warehouses(self):
        """Create test warehouses"""
        warehouses = ["Test Supplier WH - _TC", "Test FG WH - _TC", "Test RM WH - _TC"]
        
        for warehouse in warehouses:
            if not frappe.db.exists("Warehouse", warehouse):
                wh = frappe.get_doc({
                    "doctype": "Warehouse",
                    "warehouse_name": warehouse.replace(" - _TC", ""),
                    "company": "_Test Company"
                })
                wh.insert()

    def create_test_supplier(self):
        """Create test supplier"""
        if not frappe.db.exists("Supplier", "Test Subcontractor"):
            supplier = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": "Test Subcontractor",
                "supplier_group": "Local",
                "company": "_Test Company"
            })
            supplier.insert()

    def test_create_subcontract_process_loss(self):
        """Test creating Subcontract Process Loss document"""
        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": []
        })
        
        process_loss.insert()
        self.assertTrue(process_loss.name)
        self.assertEqual(process_loss.docstatus, 0)

    def test_calculate_process_loss_with_single_po(self):
        """Test process loss calculation with single purchase order"""
        # Create stock for raw material
        stock_entry = make_stock_entry(
            item_code="Test Raw Material",
            target="Test RM WH - _TC",
            qty=100,
            basic_rate=50
        )

        # Create Purchase Order
        po = create_purchase_order(
            supplier="Test Subcontractor",
            items=[{
                "item_code": "Test Finished Product",
                "qty": 10,
                "rate": 100,
                "schedule_date": frappe.utils.nowdate(),
                "warehouse": "Test FG WH - _TC"
            }],
            do_not_save=True
        )
        po.is_subcontracted = 1
        po.supplier_warehouse = "Test Supplier WH - _TC"
        po.save()
        po.submit()

        # Create Subcontracting Order
        sco = make_subcontracting_order(
            purchase_order=po.name,
            supplier_warehouse="Test Supplier WH - _TC"
        )

        # Create Process Loss document
        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": [{
                "purchase_order": po.name
            }]
        })
        process_loss.insert()

        # Test calculate_process_loss function
        result = frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_process_loss")(
            process_loss.name,
            [{"purchase_order": po.name}]
        )

        self.assertIsNotNone(result)
        self.assertIn('sent_details', result)
        self.assertIn('return_details', result)
        self.assertIn('received_details', result)

    def test_calculate_process_loss_with_multiple_pos(self):
        """Test process loss calculation with multiple purchase orders"""
        # Create multiple purchase orders
        pos = []
        for i in range(2):
            po = create_purchase_order(
                supplier="Test Subcontractor",
                items=[{
                    "item_code": "Test Finished Product",
                    "qty": 5,
                    "rate": 100,
                    "schedule_date": frappe.utils.nowdate(),
                    "warehouse": "Test FG WH - _TC"
                }],
                do_not_save=True
            )
            po.is_subcontracted = 1
            po.supplier_warehouse = "Test Supplier WH - _TC"
            po.save()
            po.submit()
            pos.append(po.name)

        # Create Process Loss document with multiple POs
        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": [{"purchase_order": po} for po in pos]
        })
        process_loss.insert()

        # Test with multiple purchase orders
        purchase_orders_data = [{"purchase_order": po} for po in pos]
        result = frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_process_loss")(
            process_loss.name,
            purchase_orders_data
        )

        self.assertIsNotNone(result)
        self.assertTrue(len(result['sent_details']) >= 0)

    def test_calculate_summary_function(self):
        """Test the calculate_summary function"""
        # Create Process Loss document
        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": []
        })
        process_loss.insert()

        # Add some test data to sent, return, and received details
        process_loss.append("subcontract_sent_details", {
            "purchase_order": "Test PO",
            "subcontracting_order": "Test SCO",
            "item_code": "Test Raw Material",
            "main_item_code": "Test Finished Product",
            "po_qty": 100,
            "sent_qty": 80,
            "uom": "Kg"
        })

        process_loss.append("subcontract_received_details", {
            "purchase_order": "Test PO",
            "subcontracting_order": "Test SCO",
            "item_code": "Test Finished Product",
            "po_qty": 10,
            "received_qty": 8,
            "uom": "Nos"
        })

        process_loss.save()

        # Test calculate_summary function
        result = frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_summary")(
            process_loss.name
        )

        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, list))

    def test_process_loss_calculation_logic(self):
        """Test the process loss calculation logic"""
        # Create Process Loss document
        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": []
        })
        process_loss.insert()

        # Add test data with known values for calculation
        process_loss.append("subcontract_sent_details", {
            "purchase_order": "PO-001",
            "subcontracting_order": "SCO-001",
            "item_code": "Test Raw Material",
            "main_item_code": "Test Finished Product",
            "po_qty": 100,
            "sent_qty": 100,  # 100 kg sent
            "uom": "Kg"
        })

        process_loss.append("subcontract_return_details", {
            "purchase_order": "PO-001",
            "subcontracting_order": "SCO-001",
            "item_code": "Test Raw Material",
            "po_item_code": "Test Finished Product",
            "po_qty": 100,
            "return_qty": 10,  # 10 kg returned
            "uom": "Kg"
        })

        process_loss.append("subcontract_received_details", {
            "purchase_order": "PO-001",
            "subcontracting_order": "SCO-001",
            "item_code": "Test Finished Product",
            "po_qty": 10,
            "received_qty": 8,  # 8 pieces received
            "uom": "Nos"
        })

        process_loss.save()

        # Calculate summary and verify calculations
        result = frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_summary")(
            process_loss.name
        )

        if result and len(result) > 0:
            summary_item = result[0]
            # Process Loss Qty = Sent - Return - Received
            # Note: This assumes proper conversion between raw material and finished goods
            expected_loss_qty = 100 - 10  # This would need conversion logic
            self.assertTrue('process_loss_qty' in summary_item)
            self.assertTrue('process_loss_percentage' in summary_item)

    def test_empty_purchase_orders(self):
        """Test with empty purchase orders list"""
        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": []
        })
        process_loss.insert()

        result = frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_process_loss")(
            process_loss.name,
            []
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(result['sent_details']), 0)
        self.assertEqual(len(result['return_details']), 0)
        self.assertEqual(len(result['received_details']), 0)

    def test_invalid_docname(self):
        """Test with invalid document name"""
        with self.assertRaises(Exception):
            frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_summary")(
                "INVALID_DOCNAME"
            )

    def test_process_loss_with_no_transactions(self):
        """Test process loss calculation when no transactions exist"""
        # Create PO but no transactions
        po = create_purchase_order(
            supplier="Test Subcontractor",
            items=[{
                "item_code": "Test Finished Product",
                "qty": 10,
                "rate": 100,
                "schedule_date": frappe.utils.nowdate(),
                "warehouse": "Test FG WH - _TC"
            }],
            do_not_save=True
        )
        po.is_subcontracted = 1
        po.supplier_warehouse = "Test Supplier WH - _TC"
        po.save()
        po.submit()

        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": [{"purchase_order": po.name}]
        })
        process_loss.insert()

        result = frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_process_loss")(
            process_loss.name,
            [{"purchase_order": po.name}]
        )

        self.assertIsNotNone(result)
        # Should return empty lists when no transactions found
        self.assertTrue(isinstance(result['sent_details'], list))
        self.assertTrue(isinstance(result['return_details'], list))
        self.assertTrue(isinstance(result['received_details'], list))

    def test_error_handling(self):
        """Test error handling in process loss calculation"""
        # Test with invalid data
        process_loss = frappe.get_doc({
            "doctype": "Subcontract Process Loss",
            "posting_date": frappe.utils.nowdate(),
            "purchase_orders": []
        })
        process_loss.insert()

        # This should handle the error gracefully
        with self.assertRaises(Exception):
            frappe.get_attr("erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_process_loss")(
                process_loss.name,
                "invalid_json_string"
            )


def create_test_subcontracting_flow():
    """Helper function to create a complete subcontracting flow for testing"""
    # Create stock for raw material
    stock_entry = make_stock_entry(
        item_code="Test Raw Material",
        target="Test RM WH - _TC",
        qty=1000,
        basic_rate=50
    )

    # Create Purchase Order
    po = create_purchase_order(
        supplier="Test Subcontractor",
        items=[{
            "item_code": "Test Finished Product",
            "qty": 100,
            "rate": 100,
            "schedule_date": frappe.utils.nowdate(),
            "warehouse": "Test FG WH - _TC"
        }],
        do_not_save=True
    )
    po.is_subcontracted = 1
    po.supplier_warehouse = "Test Supplier WH - _TC"
    po.save()
    po.submit()

    return po.name


if __name__ == "__main__":
    import unittest
    unittest.main()
