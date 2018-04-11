import frappe
from frappe import _
from erpnext.erpnext_integrations.doctype.shopify_log.shopify_log import make_shopify_log

def create_customer(shopify_customer, shopify_settings):
	import frappe.utils.nestedset

	cust_name = (shopify_customer.get("first_name") + " " + (shopify_customer.get("last_name") \
		and  shopify_customer.get("last_name") or "")) if shopify_customer.get("first_name")\
		else shopify_customer.get("email")

	try:
		customer = frappe.get_doc({
			"doctype": "Customer",
			"name": shopify_customer.get("id"),
			"customer_name" : cust_name,
			"shopify_customer_id": shopify_customer.get("id"),
			"sync_with_shopify": 1,
			"customer_group": shopify_settings.customer_group,
			"territory": frappe.utils.nestedset.get_root_of("Territory"),
			"customer_type": _("Individual")
		})
		customer.flags.ignore_mandatory = True
		customer.insert()
	
		if customer:
			create_customer_address(customer, shopify_customer)

		frappe.db.commit()
		
	except Exception as e:
		if e.args[0] and e.args[0].startswith("402"):
			make_shopify_log(status="Error", method="create_customer", message=e.message,
				request_data=shopify_customer, exception=True)
		else:
			make_shopify_log(status="Error", method="create_customer", message=frappe.get_traceback(),
				request_data=shopify_customer, exception=True)

def create_customer_address(customer, shopify_customer):
	if not shopify_customer.get("addresses"):
		return

	for i, address in enumerate(shopify_customer.get("addresses")):
		address_title, address_type = get_address_title_and_type(customer.customer_name, i)
		try :
			frappe.get_doc({
				"doctype": "Address",
				"shopify_address_id": address.get("id"),
				"address_title": address_title,
				"address_type": address_type,
				"address_line1": address.get("address1") or "Address 1",
				"address_line2": address.get("address2"),
				"city": address.get("city") or "City",
				"state": address.get("province"),
				"pincode": address.get("zip"),
				"country": address.get("country"),
				"phone": address.get("phone"),
				"email_id": shopify_customer.get("email"),
				"links": [{
					"link_doctype": "Customer",
					"link_name": customer.name
				}]
			}).insert(ignore_mandatory=True)
		
		except Exception:
			make_shopify_log(status="Error", method="create_customer_address", message=frappe.get_traceback(),
				request_data=shopify_customer, exception=True)

def get_address_title_and_type(customer_name, index):
	address_type = _("Billing")
	address_title = customer_name
	if frappe.db.get_value("Address", "{0}-{1}".format(customer_name.strip(), address_type)):
		address_title = "{0}-{1}".format(customer_name.strip(), index)
	
	return address_title, address_type
