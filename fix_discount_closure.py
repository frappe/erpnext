#!/usr/bin/env python3

"""
This is a temporary script to add the discount closure method to the Sales Invoice class.
The actual modification should be made in erpnext/accounts/doctype/sales_invoice/sales_invoice.py
by adding the _close_linked_sales_orders_on_discount method and calling it in on_submit.
"""

# The code modification needed:
# 1. Add this method to the SalesInvoice class:

def _close_linked_sales_orders_on_discount(self):
    """Auto-closes linked Sales Orders if fully billed/delivered and any discount (header or item-level) is applied."""
    # Check for header-level discounts
    has_any_discount = self.additional_discount_percentage > 0 or self.discount_amount > 0

    # If no header-level discount, check for item-level discounts
    if not has_any_discount:
        for item in self.items:
            if item.discount_percentage > 0 or item.discount_amount > 0:
                has_any_discount = True
                break

    if has_any_discount:
        # Get unique sales orders linked to this invoice
        linked_sales_orders = {item.sales_order for item in self.items if item.sales_order}
        for so_name in linked_sales_orders:
            so = frappe.get_doc("Sales Order", so_name)
            # Ensure the SO's status is re-evaluated based on latest billed/delivered quantities
            so.set_percent_billed_and_delivered()
            if so.per_billed >= 99.99 and so.per_delivered >= 99.99:
                if so.status != "Closed":
                    so.status = "Closed"
                    so.save(ignore_permissions=True)

# 2. Add this call in the on_submit method after self.update_prevdoc_status():
# self._close_linked_sales_orders_on_discount()

print("This script shows the modifications needed for issue #49130")
print("The actual fix should be applied to the sales_invoice.py file")
