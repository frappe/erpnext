# see license.txt

from __future__ import unicode_literals
import frappe, base64, hashlib, hmac, json
from frappe import _

def verify_request():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	sig = base64.b64encode(
		hmac.new(
			woocommerce_settings.secret.encode(),
			str(frappe.request.data),
			hashlib.sha256
		).digest()
	)
	print("verify_request", sig, frappe.get_request_header("X-Wc-Webhook-Signature"))
	if frappe.request.data and \
		frappe.get_request_header("X-Wc-Webhook-Signature") and \
		not sig == frappe.get_request_header("X-Wc-Webhook-Signature"):
			frappe.throw(_("Unverified Webhook Data"))
	frappe.set_user("Administrator")

# @frappe.whitelist(allow_guest=True)
# def create_coupon():
# 	verify_request()
# 	print("yay!")

# @frappe.whitelist(allow_guest=True)
# def update_coupon():
# 	print(frappe.request.headers)
# 	print(frappe.request.headers.get("X-Wc-Webhook-Event"))
# 	print(frappe.request.headers.get("X-Wc-Webhook-Resource"))
# 	verify_request()
# 	print("yay!")

# @frappe.whitelist(allow_guest=True)
# def delete_coupon():
# 	pass

# @frappe.whitelist(allow_guest=True)
# def restore_coupon():
# 	pass

@frappe.whitelist(allow_guest=True)
def customer():
	verify_request()
	fd = json.loads(frappe.request.data)
	print(fd)
	event = frappe.get_request_header("X-Wc-Webhook-Event")

	if event == "updated":
		try:
			existing_customer = frappe.get_doc("Customer",{"woocommerce_id": fd.get("id")})

			edit_existing_customer(existing_customer,fd)

			# print("THis Complete 1", existing_customer.customer_name)

			# make_address = frappe.new_doc("Address")
			# make_address.address_line1 = "Not Provided" if not fd.get("address_1") else fd.get("address_1")
			# make_address.address_line2 = "Not Provided" if not fd.get("address_2") else fd.get("address_2")
			# make_address.city = "Not Provided" if not fd.get("city") else fd.get("city")
			# make_address.country = fd.get("country")
			# make_address.state = fd.get("state")
			# make_address.pincode = str(fd.get("postcode"))
			# make_address.phone = str(fd.get("phone"))
			# make_address.email = str(fd.get("email"))

			# make_address.append("links", {
			# 	"link_doctype": "Customer",
			# 	"link_name": str(fd.get("first_name"))
			# })

			
			# make_address.save()
			
		except frappe.DoesNotExistError as e:

			create_customer(fd)
			# print("THis Complete 2")
			
		except Exception as e:
			print("Error ",e)

	# elif event == "updated":
	# 	pass
	# elif event == "deleted":
	# 	pass



# @frappe.whitelist(allow_guest=True)
# def product():
# 	# print("hello"*1000)
# 	verify_request()
# 	print(frappe.local.form_dict)
# 	fd = json.loads(frappe.request.data)
# 	event = frappe.get_request_header("X-Wc-Webhook-Event")
# 	print(event)
# 	if event == "created":
# 		print("inif?")
# 		print(
# 			fd.get("name"),
# 			"woocommerce - " + str(fd.get("id")),
# 			str(fd.get("id")),
# 			0 if (fd.get("stock_quantity") == None) else fd.get("stock_quantity")
# 		)
# 		try:
# 			item = frappe.new_doc("Item")
# 			item.item_name = str(fd.get("name"))
# 			item.item_code = "woocommerce - " + str(fd.get("id"))
# 			# item.woocommerce_id = str(fd.get("id"))
# 			item.item_group = "Products"
# 			item.opening_stock = 0 if (fd.get("stock_quantity") == None) else str(fd.get("stock_quantity"))
# 			item.save()

# 			# note = frappe.new_doc("Note")
# 			# note.title = str(fd.get("name"))
# 			# # note.content = fd.get("name")
# 			# note.save(ignore_permissions=True)
# 			frappe.db.commit()
# 		except Exception as e:
# 			print("Exception", e)

# 	elif event == "updated":
# 		item = frappe.get_doc({"doctype":"Item", "item_code":fd.get("id")})

# 	elif event == "restored":
# 		pass
# 	elif event == "deleted":
# 		pass


# @frappe.whitelist(allow_guest=True)
# def order():
# 	pass
# 	verify_request()
# 	print(frappe.local.form_dict)
# 	fd = frappe.local.form_dict
# 	event = frappe.get_request_header("X-Wc-Webhook-Event")

# 	if event == "created":
# 		new_sales_order = frappe.new_doc("Sales Order")
# 		new_sales_order.customer = fd.get("first_name")+" "+fd.get("last_name")
# 		created_date = fd.get("date_created").split("T")
# 		new_sales_order.transaction_date = created_date[0]
# 		new_sales_order.po_no = fd.get("id")
# 		new_sales_order.Sales Order-woocommerce_id = fd.get("id")
# 		# new_sales_order.append("taxes",{
# 		# 				"charge_type":"Actual",
# 		# 				"account_head": "VAT 5% - Woo",
# 		# 				"tax_amount": charge_amount,
# 		# 				"description": charge_type
# 		# 				})
# 		ordered_items = fd.get("line_items")
# 		for item in ordered_items:

# # 			found_item = frappe.get_doc({"doctype":"Item","item_name":item.get("name")})
# # 			new_sales_order.append("items",{
# # 				"item_code": found_item.item_code,
# # 				"item_name": found_item.item_name,
# # 				"description": found_item.description,
# # 				"delivery_date":created_date[0],   #change delivery date after testing
# # 				"uom": "Nos",
# # 				"qty": item.get("quantity"),
# # 				"rate": item.get("price")
# # 				})

# # 		new_sales_order.save()

# # 	elif event == "updated":
# # 		pass
# # 	elif event == "restored":
# # 		pass
# # 	elif event == "deleted":
# # 		pass

# # 	frappe.db.commit()	



def create_customer(fd):

	new_customer = frappe.new_doc("Customer")
	# new_customer.customer_name = fd.get("first_name")+" "+fd.get("last_name")
	# new_customer.customer_name = "WC {id}".format(id=str(fd.get("id"))) if not fd.get("first_name") else str(fd.get("first_name"))

	if (not fd.get("first_name") and not fd.get("last_name")):
		# print("THis is if 21")
		new_customer.customer_name = "WC {id}".format(id=str(fd.get("id")))
		new_customer.woocommerce_id = str(fd.get("id"))
		new_customer.save()
		frappe.db.commit()
		# print("Completed 21")

	elif(fd.get("first_name") and not fd.get("last_name")):
		# print("THis is if 22")
		new_customer.customer_name = str(fd.get("first_name"))
		new_customer.woocommerce_id = str(fd.get("id"))
		new_customer.save()
		frappe.db.commit()

	elif(not fd.get("first_name") and fd.get("last_name")):
		# print("THis is if 23")
		new_customer.customer_name = str(fd.get("last_name"))
		new_customer.woocommerce_id = str(fd.get("id"))
		new_customer.save()
		frappe.db.commit()
		
	else:
		# print("THis is if 24")
		new_customer.customer_name = str(fd.get("first_name"))+ " "+str(fd.get("last_name"))
		new_customer.woocommerce_id = str(fd.get("id"))
		new_customer.save()
		frappe.db.commit()


def edit_existing_customer(existing_customer,fd):

	if (not fd.get("first_name") and not fd.get("last_name")):
		# print("THis is if 11")
		existing_customer.customer_name = "WC {id}".format(id=str(fd.get("id")))
		existing_customer.save()
		frappe.db.commit()
	# print("""if(fd.get("first_name") != None and fd.get("last_name") == None):""", (fd.get("first_name") != None and fd.get("last_name") == None), (fd.get("first_name") != None), (fd.get("last_name") == None))
	# print("""elif(fd.get("first_name") == None and fd.get("last_name") != None):""", (fd.get("first_name") == None and fd.get("last_name") != None), (fd.get("first_name") == None), (fd.get("last_name") != None))

	elif(fd.get("first_name") and not fd.get("last_name")):
		# print("THis is if 12")
		existing_customer.customer_name = fd.get("first_name")
		existing_customer.save()
		frappe.db.commit()

	elif(not fd.get("first_name") and fd.get("last_name")):
		# print("THis is if 13")
		existing_customer.customer_name = str(fd.get("last_name"))
		existing_customer.save()
		frappe.db.commit()

	else:
		# print("THis is if 14")
		existing_customer.customer_name = str(fd.get("first_name"))+ " "+str(fd.get("last_name"))
		existing_customer.save()
		frappe.db.commit()



