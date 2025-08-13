import frappe
from frappe import _
from frappe.utils import cint

def close_linked_sales_orders_on_discount(self):
	"""Close linked Sales Orders when any discount is applied and the order is fully billed/delivered."""
	
	# Check if any discount is applied (both header-level and line-item level)
	has_discount = False
	
	# Check for header-level discount (Additional Discount)
	if self.additional_discount_percentage or self.discount_amount:
		has_discount = True
	
	# Check for line-item level discounts
	if not has_discount:
		for item in self.items:
			if item.discount_percentage or item.discount_amount:
				has_discount = True
				break
	
	if not has_discount:
		return
	
	# Get all linked Sales Orders
	linked_sales_orders = set()
	for item in self.items:
		if item.sales_order:
			linked_sales_orders.add(item.sales_order)
	
	if not linked_sales_orders:
		return
	
	# Check each Sales Order for full billing/delivery and close if eligible
	for sales_order_name in linked_sales_orders:
		try:
			sales_order = frappe.get_doc("Sales Order", sales_order_name)
			
			# Check if the Sales Order is fully billed and delivered 
			# (using 99.99% threshold for floating-point precision)
			if (sales_order.per_billed >= 99.99 and 
				sales_order.per_delivered >= 99.99 and 
				sales_order.status not in ["Closed", "Cancelled"]):
				
				# Set status to Closed
				sales_order.db_set("status", "Closed")
				sales_order.set_indicator()
				
				frappe.msgprint(
					_("Sales Order {0} has been automatically closed due to discount application and full fulfillment.").format(
						sales_order_name
					), 
					alert=True
				)
				
		except frappe.DoesNotExistError:
			# Sales Order might have been deleted
			continue
		except Exception as e:
			# Log error but don't fail the invoice submission
			frappe.log_error(
				message=f"Error closing Sales Order {sales_order_name}: {str(e)}", 
				title="Auto-close Sales Order Error"
			)

# Monkey patch to add the method to SalesInvoice class
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

# Add the method to SalesInvoice class
SalesInvoice._close_linked_sales_orders_on_discount = close_linked_sales_orders_on_discount

# Override the on_submit method
original_on_submit = SalesInvoice.on_submit

def patched_on_submit(self):
	"""Enhanced on_submit method that includes auto-closing sales orders on discount."""
	# Call the original on_submit method
	original_on_submit(self)
	
	# Add our custom logic for auto-closing sales orders
	if not self.is_return:
		self._close_linked_sales_orders_on_discount()

# Replace the on_submit method
SalesInvoice.on_submit = patched_on_submit
