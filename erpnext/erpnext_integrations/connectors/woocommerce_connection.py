
from __future__ import unicode_literals
import frappe, base64, hashlib, hmac, json
from frappe import _

def verify_request():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	sig = base64.b64encode(
		hmac.new(
			woocommerce_settings.secret.encode('utf8'),
			frappe.request.data,
			hashlib.sha256
		).digest()
	)

	if frappe.request.data and \
		frappe.get_request_header("X-Wc-Webhook-Signature") and \
		not sig == bytes(frappe.get_request_header("X-Wc-Webhook-Signature").encode()):
			frappe.throw(_("Unverified Webhook Data"))
	frappe.set_user(woocommerce_settings.creation_user)

@frappe.whitelist(allow_guest=True)
def order(*args, **kwargs):
	try:
		_order(*args, **kwargs)
	except Exception:
		error_message = frappe.get_traceback()+"\n\n Request Data: \n"+json.loads(frappe.request.data).__str__()
		frappe.log_error(error_message, "WooCommerce Error")
		raise

def _order(*args, **kwargs):
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	if frappe.flags.woocomm_test_order_data:
		order = frappe.flags.woocomm_test_order_data
		event = "created"

	elif frappe.request and frappe.request.data:
		verify_request()
		try:
			order = json.loads(frappe.request.data)
		except ValueError:
			#woocommerce returns 'webhook_id=value' for the first request which is not JSON
			order = frappe.request.data
		event = frappe.get_request_header("X-Wc-Webhook-Event")

	else:
		return "success"

	if event == "created":
		#Get user ID and check GST
		raw_billing_data = order.get("billing")
		metaDataList = order.get("meta_data")
		gstInclusive = "True"
		customerID = None
		for meta in metaDataList:
			if meta.get("key") == "store_code":
				customerID = meta.get("value")
			elif meta.get("key") == "order_type" and meta.get("value") == "quick_order":
				gstInclusive = "False"

		if (customerID):
			frappe.log_error(customerID)
			link_customer_and_address(raw_billing_data,1, customerID)
		else:
			frappe.log_error("Cant find Customer")
			link_customer_and_address(raw_billing_data,0)

		items_list = order.get("line_items")
		for item in items_list:
			itemID = item.get("sku")
			frappe.log_error(itemID)
			if frappe.get_value("Item",{"name": itemID}):
				#Edit
				link_item(item,1)
			else:
				link_item(item,0)

		#customer_name = raw_billing_data.get("first_name") + " " + raw_billing_data.get("last_name")
		customer = frappe.get_doc("Customer",{"name": customerID})
		newSI = frappe.new_doc("Sales Invoice")
		newSI.customer = customer.name

		created_date = order.get("date_created").split("T")
		newSI.transaction_date = created_date[0]

		newSI.po_no = order.get("id")
		newSI.woocommerce_id = order.get("id")
		newSI.naming_series = "ACC-SINV-.YYYY.-"

		placed_order_date = created_date[0]
		raw_date = datetime.datetime.strptime(placed_order_date, "%Y-%m-%d")
		raw_delivery_date = frappe.utils.add_to_date(raw_date,days = 7)
		order_delivery_date_str = raw_delivery_date.strftime('%Y-%m-%d')
		order_delivery_date = str(order_delivery_date_str)

		newSI.delivery_date = order_delivery_date
		default_set_company = frappe.get_doc("Global Defaults")
		company = default_set_company.default_company
		found_company = frappe.get_doc("Company",{"name":company})
		company_abbr = found_company.abbr

		newSI.company = company
		
		if customer:
			if customer.territory == "WA":
				warehouse = "Perth" + " - " + company_abbr
			else:
				warehouse = "Brisbane" + " - " + company_abbr
		else:
			warehouse = "Brisbane" + " - " + company_abbr

		for item in items_list:
			itemID = item.get("sku")
			found_item = frappe.get_doc("Item",{"name": itemID})
			
			if gstInclusive == "True":
				rate = item.get("price")
				ordered_items_tax = item.get("total_tax")
			else:
				itemTax = item.get("taxes")
				rate = float(item.get("price")) + float(itemTax[0].get("total")/item.get("quantity"))
				ordered_items_tax = rate * 0.1

			newSI.append("items",{
				"item_code": found_item.item_code,
				"item_name": found_item.item_name,
				"description": found_item.item_name,
				"delivery_date":order_delivery_date,
				"uom": "Unit",
				"qty": item.get("quantity"),
				"rate": rate,
				"warehouse": warehouse
				})

			add_tax_details(newSI,ordered_items_tax,"Ordered Item tax",0)

		# shipping_details = forder.get("shipping_lines") # used for detailed order
		shipping_total = order.get("shipping_total")
		shipping_tax = int(float(shipping_total)) * 0.1

		add_tax_details(newSI,shipping_tax,"Shipping Tax",1)
		add_tax_details(newSI,shipping_total,"Shipping Total",1)

		#newSI.submit()

		frappe.db.commit()

def link_customer_and_address(raw_billing_data,customer_status, customerID):

	#Check Customer Status
	if customer_status == 0:
		# create
		frappe.log_error(raw_billing_data,"Customer doesn't exist")

	elif customer_status == 1:
		# Edit
		customer = frappe.get_doc("Customer",{"name": customerID})

		#Check Address
		customer_woo_com_email = raw_billing_data.get("email")
		
		addressSQL = frappe.db.sql("SELECT * FROM `tabAddress` WHERE woocommerce_email = '" + customer_woo_com_email + "'", as_dict=True)

		if (addressSQL):
			frappe.log_error(addressSQL, "Found Address")
		else:
			frappe.log_error(addressSQL, "New Address")
			address = frappe.new_doc("Address")

		address.address_line1 = raw_billing_data.get("address_1", "Not Provided")
		address.address_line2 = raw_billing_data.get("address_2", "Not Provided")
		address.city = raw_billing_data.get("city", "Not Provided")
		address.woocommerce_email = str(raw_billing_data.get("email"))
		address.address_type = "Shipping"
		address.country = frappe.get_value("Country", filters={"code":raw_billing_data.get("country", "IN").lower()})
		address.state =  raw_billing_data.get("state")
		address.pincode =  str(raw_billing_data.get("postcode"))
		address.phone = str(raw_billing_data.get("phone"))
		address.email_id = str(raw_billing_data.get("email"))

		address.append("links", {
			"link_doctype": "Customer",
			"link_name": customer.name
		})

		address.save()
		frappe.db.commit()

		address = frappe.get_doc("Address",{"woocommerce_email":customer_woo_com_email})
		old_address_title = address.name
		new_address_title = customer.customer_name + "-billing"
		address.address_title = customer.customer_name
		address.save()

		frappe.rename_doc("Address", old_address_title, new_address_title)
		frappe.db.commit()

def link_item(item_data,item_status):
	#woocommerce_settings = frappe.get_doc("Woocommerce Settings")

	if item_status == 0:
		#Create Item - Log Error
		frappe.log_error(item_data,"Item doesn't exist")

	#else if item_status == 1:
	#	#Edit Item
	#	itemID = item_data.get("sku")
	#	item = frappe.get_doc("Item",{"name": itemID})

	#item.item_code = str(item_data.get("sku"))
	#item.item_name = str(item_data.get("name"))
	#item.brand = str(item_data.get("brand"))
	#item.item_group = str(item_data.get("item_group"))
	#item.stock_uom = str(item_data.get("stock_uom"))
	#item.save()
	#frappe.db.commit()

def add_tax_details(newSI,price,desc,status):

	woocommerce_settings = frappe.get_doc("Woocommerce Settings")

	if status == 0:
		# Product taxes
		account_head_type = woocommerce_settings.tax_account
	frappe.db.commit()
  
	newSI.append("taxes",{
			"charge_type":"Actual",
			"account_head": account_head_type,
			"tax_amount": price,
			"description": desc
			})