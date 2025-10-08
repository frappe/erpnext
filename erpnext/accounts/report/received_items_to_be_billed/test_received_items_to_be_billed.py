import frappe
from frappe.tests.utils import FrappeTestCase
from erpnext.accounts.report.received_items_to_be_billed import received_items_to_be_billed


class TestReceivedItemsToBeBilled(FrappeTestCase):

    def setUp(self):
        from erpnext.accounts.doctype.payment_request.test_payment_request import create_company
        from erpnext.stock.doctype.item.test_item import create_item
        from erpnext.buying.doctype.supplier.test_supplier import create_supplier
        from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
        from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year
        from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
        self.company = create_company()
        get_or_create_fiscal_year(company="_Test Company")
        self.item = create_item(item_code="_Test Item")
        self.supplier = create_supplier(supplier_name="_Test Supplier", default_currency="INR")
        create_warehouse(warehouse_name="_Test Warehouse", company="_Test Company")
        create_warehouse(warehouse_name="_Test Warehouse 1", company="_Test Company")
        if not frappe.db.exists("UOM", "_Test UOM"):
            frappe.get_doc({"doctype": "UOM", "uom_name": "_Test UOM"}).insert(ignore_permissions=True)
        self.purchase_receipt = make_purchase_receipt(
            item_code=self.item.item_code,
            supplier=self.supplier.name,
            warehouse="_Test Warehouse - _TC",
            qty=10,
            rate=1000,
            uom="_Test UOM"
        )
    def tearDown(self):
            frappe.db.rollback()

    def test_execute_with_recieved_items_to_be_billed_report_TC_ACC_584(self):
        filters = frappe._dict({
            "company": "_Test Company",
            "posting_date":
            frappe.utils.now(),
            "purchase_receipt": self.purchase_receipt.name
            })
        
        columns, data = received_items_to_be_billed.execute(filters=filters)
        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 0)

        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        expected_keys = [
            "name", "date", "supplier", "supplier_name", "item_code",
            "amount", "billed_amount", "returned_amount", "pending_amount",
            "item_name", "description", "project"
        ]
        
        for key in expected_keys:
            self.assertIn(key, data[0])