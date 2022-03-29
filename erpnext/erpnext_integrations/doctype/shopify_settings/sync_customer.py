import frappe
from frappe import _


def create_customer(shopify_customer, shopify_settings):
	import frappe.utils.nestedset

	cust_name = (
		(
			shopify_customer.get("first_name")
			+ " "
			+ (shopify_customer.get("last_name") and shopify_customer.get("last_name") or "")
		)
		if shopify_customer.get("first_name")
		else shopify_customer.get("email")
	)

	try:
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"name": shopify_customer.get("id"),
				"customer_name": cust_name,
				"shopify_customer_id": shopify_customer.get("id"),
				"sync_with_shopify": 1,
				"customer_group": shopify_settings.customer_group,
				"territory": frappe.utils.nestedset.get_root_of("Territory"),
				"customer_type": _("Individual"),
			}
		)
		customer.flags.ignore_mandatory = True
		customer.insert(ignore_permissions=True)

		if customer:
			create_customer_address(customer, shopify_customer)

		frappe.db.commit()

	except Exception as e:
		raise e


def create_customer_address(customer, shopify_customer):
	addresses = shopify_customer.get("addresses", [])

	if not addresses and "default_address" in shopify_customer:
		addresses.append(shopify_customer["default_address"])

	for i, address in enumerate(addresses):
		address_title, address_type = get_address_title_and_type(customer.customer_name, i)
		try:
			frappe.get_doc(
				{
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
					"links": [{"link_doctype": "Customer", "link_name": customer.name}],
				}
			).insert(ignore_mandatory=True)

		except Exception as e:
			raise e


def get_address_title_and_type(customer_name, index):
	address_type = _("Billing")
	address_title = customer_name
	if frappe.db.get_value("Address", "{0}-{1}".format(customer_name.strip(), address_type)):
		address_title = "{0}-{1}".format(customer_name.strip(), index)

	return address_title, address_type
