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

	if frappe.request.data:
		verify_request()
		fd = json.loads(frappe.request.data)
		print(fd)
		event = frappe.get_request_header("X-Wc-Webhook-Event")
		for x in xrange(1,10):
			print(event)
		if event == "updated":
			try:
				existing_customer = frappe.get_doc("Customer",{"woocommerce_id": fd.get("id")})

				edit_existing_customer(existing_customer,fd)
				# print("THis Complete 1", existing_customer.customer_name)
				existing_customer = frappe.get_doc("Customer",{"woocommerce_id": fd.get("id")})
				create_or_edit_address(existing_customer,fd,1)

				
			except frappe.DoesNotExistError as e:

				# new_customer = frappe.new_doc("Customer")
				create_customer(fd)
				new_existing_customer = frappe.get_doc("Customer",{"woocommerce_id": fd.get("id")})
				create_or_edit_address(new_existing_customer,fd,0)
				# print("THis Complete 2")

			# except frappe.MandatoryError as e:
			# 	new_existing_customer = frappe.get_doc("Customer",{"woocommerce_id": fd.get("id")})
			# 	create_or_edit_address(new_existing_customer,fd,0)
				
			except Exception as e:
				print("Error ",e)

		# elif event == "updated":
		# 	pass

	# 	if event == "deleted":
	# 		try:
	# 			delete_customer = frappe.get_doc("Customer",{"woocommerce_id":fd.get("id")})
	# +			delete = frappe.delete_doc("Customer",delete_customer.name)
	# +			frappe.db.commit()
				
	# 		except Exception as e:
	# 			print ("delete Error", e)




@frappe.whitelist(allow_guest=True)
def product():
	# pass
	# print("hello"*1000)
	verify_request()
	print(frappe.local.form_dict)
	if frappe.request.data:
		fd = json.loads(frappe.request.data)
	else:
		return "success"
	event = frappe.get_request_header("X-Wc-Webhook-Event")
	print(event*100	)
	# try:
		
	if event == "created":
		print("inif?")
		print(
			fd.get("name"),
			"woocommerce - " + str(fd.get("id")),
			str(fd.get("id")),
			0 if (fd.get("stock_quantity") == None) else fd.get("stock_quantity")
		)

		print (fd)
		product_raw_image = fd.get("images") 
		try:
			item = frappe.new_doc("Item")
			item.item_name = str(fd.get("name"))
			item.item_code = "woocommerce - " + str(fd.get("id"))
			item.woocommerce_id = str(fd.get("id"))
			item.item_group = "WooCommerce Products"
			item.description = str(fd.get("description"))
			item.image = product_raw_image[0].get("src")
			item.opening_stock = 0 if (fd.get("stock_quantity") == None) else str(fd.get("stock_quantity"))
			item.save()

			# note = frappe.new_doc("Note")
			# note.title = str(fd.get("name"))
			# # note.content = fd.get("name")
			# note.save(ignore_permissions=True)
			frappe.db.commit()
		except Exception as e:
			print("Exception", e)

	elif event == "updated":
		print("Entered into updated")
		
		# print("I am into updated method")
		# try:
		print(fd)
		existing_item = frappe.get_doc("Item",{"woocommerce_id":fd.get("id")})
		print(existing_item.item_name)
		existing_item.item_name = str(fd.get("name")) 
		existing_item.description = str(fd.get("description"))
		existing_item.opening_stock = 0 if (fd.get("stock_quantity") == None) else str(fd.get("stock_quantity"))

		product_raw_image = fd.get("images") 
		existing_item.image = "" if not product_raw_image[0].get("src") else product_raw_image[0].get("src")
		existing_item.save()
		frappe.db.commit()
			
		# except Exception as e:
		# 	print("This is product exception", e*10)
		# print("Completed updated method")
		# pass
	# except Exception as a:
	# 	print("This is main exception in product",a*10)

	elif event == "restored":
		print("Inside product restore")
		print(fd)

		restoring_item = frappe.get_doc("Item",{"woocommerce_id":fd.get("id")})
		restoring_item.woocommerce_check = 0
		restoring_item.save()

		frappe.db.commit()
		print("Successfully restored")

	elif event == "deleted":
		print("Inside product delete")
		print(fd)
		deleting_item = frappe.get_doc("Item",{"woocommerce_id":fd.get("id")})
		deleting_item.woocommerce_check = 1
		deleting_item.save()

		frappe.db.commit()
		print("Successfully deleted")


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

		# existing_customer.customer_name = "WC {id}".format(id=str(fd.get("id")))
		# existing_customer.save()
		# frappe.db.commit()
		name =  "WC {id}".format(id=str(fd.get("id")))
		frappe.rename_doc("Customer", existing_customer.customer_name, name)
	# print("""if(fd.get("first_name") != None and fd.get("last_name") == None):""", (fd.get("first_name") != None and fd.get("last_name") == None), (fd.get("first_name") != None), (fd.get("last_name") == None))
	# print("""elif(fd.get("first_name") == None and fd.get("last_name") != None):""", (fd.get("first_name") == None and fd.get("last_name") != None), (fd.get("first_name") == None), (fd.get("last_name") != None))

	elif(fd.get("first_name") and not fd.get("last_name")):
		# print("THis is if 12")

		# existing_customer.customer_name = fd.get("first_name")
		name = fd.get("first_name")
		frappe.rename_doc("Customer", existing_customer.customer_name, name)
		# existing_customer.save()
		# frappe.db.commit()

	elif(not fd.get("first_name") and fd.get("last_name")):
		# print("THis is if 13")

		# existing_customer.customer_name = str(fd.get("last_name"))
		name = str(fd.get("last_name"))
		frappe.rename_doc("Customer", existing_customer.customer_name, name)
		# existing_customer.save()
		# frappe.db.commit()

	else:
		# print("THis is if 14")

		# existing_customer.customer_name = str(fd.get("first_name"))+ " "+str(fd.get("last_name"))
		name = str(fd.get("first_name"))+ " "+str(fd.get("last_name"))
		frappe.rename_doc("Customer", existing_customer.customer_name, name)
		# existing_customer.save()
		# frappe.db.commit()


def create_or_edit_address(customer,fd,customer_status):

	if customer_status == 0:
		make_address = frappe.new_doc("Address")

	if customer_status == 1:
		make_address = frappe.get_doc("Address",{"woocommerce_id": fd.get("id")})
		new_address_title = customer.customer_name+"-billing"
		make_address.address_title = customer.customer_name
		make_address.save()

		frappe.rename_doc("Address",make_address.name,new_address_title)

		make_address = frappe.get_doc("Address",{"woocommerce_id": fd.get("id")})

	raw_address = fd.get("billing")
	print("This is address")
	print(raw_address)

	make_address.address_line1 = raw_address.get("address_1", "Not Provided")
	make_address.address_line2 = raw_address.get("address_2", "Not Provided")
	make_address.city = raw_address.get("city", "Not Provided")
	make_address.woocommerce_id = str(fd.get("id"))
	make_address.address_type = "Shipping"
	make_address.country = frappe.get_value("Country", filters={"code":raw_address.get("country", "IN").lower()})
	make_address.state =  raw_address.get("state")
	make_address.pincode =  str(raw_address.get("postcode"))
	make_address.phone = str(raw_address.get("phone"))
	make_address.email_id = str(raw_address.get("email"))

	make_address.append("links", {
		"link_doctype": "Customer",
		"link_name": customer.customer_name
	})

	make_address.save()

	frappe.db.commit()
