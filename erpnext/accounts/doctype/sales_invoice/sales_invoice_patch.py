# Patch for Sales Invoice to auto-close Sales Orders when line item discounts are applied
# This patch addresses issue #49130

# Method to add to SalesInvoice class:

def _close_linked_sales_orders_on_discount(self):
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
			
			# Check if the Sales Order is fully billed and delivered (using 99.99% threshold for floating-point precision)
			if (sales_order.per_billed >= 99.99 and 
				sales_order.per_delivered >= 99.99 and 
				sales_order.status != "Closed"):
				
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


# Modified on_submit method (add this after self.update_prevdoc_status())
# Line to add after update_prevdoc_status():

	# Auto-close linked Sales Orders when discounts are applied
	if not self.is_return:
		self._close_linked_sales_orders_on_discount()