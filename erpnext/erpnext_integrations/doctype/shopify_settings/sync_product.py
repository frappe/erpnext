import frappe
from frappe import _
from frappe.utils import cstr, cint, get_request_session
from erpnext.erpnext_integrations.doctype.shopify_settings.shopify_settings import get_shopify_url, get_header

shopify_variants_attr_list = ["option1", "option2", "option3"]

def sync_item_from_shopify(shopify_settings, item):
	url = get_shopify_url("/admin/products/{0}.json".format(item.get("product_id")), shopify_settings)
	session = get_request_session()

	try:
		res = session.get(url, headers=get_header(shopify_settings))
		res.raise_for_status()

		shopify_item = res.json()["product"]
		make_item(shopify_settings.warehouse, shopify_item)
	except Exception as e:
		raise e

def make_item(warehouse, shopify_item):
	add_item_weight(shopify_item)

	if has_variants(shopify_item):
		attributes = create_attribute(shopify_item)
		create_item(shopify_item, warehouse, 1, attributes)
		create_item_variants(shopify_item, warehouse, attributes, shopify_variants_attr_list)

	else:
		shopify_item["variant_id"] = shopify_item['variants'][0]["id"]
		create_item(shopify_item, warehouse)

def add_item_weight(shopify_item):
	shopify_item["weight"] = shopify_item['variants'][0]["weight"]
	shopify_item["weight_unit"] = shopify_item['variants'][0]["weight_unit"]

def has_variants(shopify_item):
	if len(shopify_item.get("options")) >= 1 and "Default Title" not in shopify_item.get("options")[0]["values"]:
		return True
	return False

def create_attribute(shopify_item):
	attribute = []
	# shopify item dict
	for attr in shopify_item.get('options'):
		if not frappe.db.get_value("Item Attribute", attr.get("name"), "name"):
			frappe.get_doc({
				"doctype": "Item Attribute",
				"attribute_name": attr.get("name"),
				"item_attribute_values": [
					{
						"attribute_value": attr_value,
						"abbr":attr_value
					}
					for attr_value in attr.get("values")
				]
			}).insert()
			attribute.append({"attribute": attr.get("name")})

		else:
			# check for attribute values
			item_attr = frappe.get_doc("Item Attribute", attr.get("name"))
			if not item_attr.numeric_values:
				set_new_attribute_values(item_attr, attr.get("values"))
				item_attr.save()
				attribute.append({"attribute": attr.get("name")})

			else:
				attribute.append({
					"attribute": attr.get("name"),
					"from_range": item_attr.get("from_range"),
					"to_range": item_attr.get("to_range"),
					"increment": item_attr.get("increment"),
					"numeric_values": item_attr.get("numeric_values")
				})

	return attribute

def set_new_attribute_values(item_attr, values):
	for attr_value in values:
		if not any((d.abbr.lower() == attr_value.lower() or d.attribute_value.lower() == attr_value.lower())\
		for d in item_attr.item_attribute_values):
			item_attr.append("item_attribute_values", {
				"attribute_value": attr_value,
				"abbr": attr_value
			})

def create_item(shopify_item, warehouse, has_variant=0, attributes=None,variant_of=None):
	item_dict = {
		"doctype": "Item",
		"shopify_product_id": shopify_item.get("id"),
		"shopify_variant_id": shopify_item.get("variant_id"),
		"variant_of": variant_of,
		"sync_with_shopify": 1,
		"is_stock_item": 1,
		"item_code": cstr(shopify_item.get("item_code")) or cstr(shopify_item.get("id")),
		"item_name": shopify_item.get("title", '').strip(),
		"description": shopify_item.get("body_html") or shopify_item.get("title"),
		"shopify_description": shopify_item.get("body_html") or shopify_item.get("title"),
		"item_group": get_item_group(shopify_item.get("product_type")),
		"has_variants": has_variant,
		"attributes":attributes or [],
		"stock_uom": shopify_item.get("uom") or _("Nos"),
		"stock_keeping_unit": shopify_item.get("sku") or get_sku(shopify_item),
		"default_warehouse": warehouse,
		"image": get_item_image(shopify_item),
		"weight_uom": shopify_item.get("weight_unit"),
		"weight_per_unit": shopify_item.get("weight"),
		"default_supplier": get_supplier(shopify_item)
	}

	if not is_item_exists(item_dict, attributes, variant_of=variant_of):
		item_details = get_item_details(shopify_item)
		name = ''

		if not item_details:
			new_item = frappe.get_doc(item_dict)
			new_item.insert()
			name = new_item.name

		if not name:
			name = item_details.name

		if not has_variant:
			add_to_price_list(shopify_item, name)

		frappe.db.commit()

def create_item_variants(shopify_item, warehouse, attributes, shopify_variants_attr_list):
	template_item = frappe.db.get_value("Item", filters={"shopify_product_id": shopify_item.get("id")},
		fieldname=["name", "stock_uom"], as_dict=True)

	if template_item:
		for variant in shopify_item.get("variants"):
			shopify_item_variant = {
				"id" : variant.get("id"),
				"item_code": variant.get("id"),
				"title": variant.get("title"),
				"product_type": shopify_item.get("product_type"),
				"sku": variant.get("sku"),
				"uom": template_item.stock_uom or _("Nos"),
				"item_price": variant.get("price"),
				"variant_id": variant.get("id"),
				"weight_unit": variant.get("weight_unit"),
				"weight": variant.get("weight")
			}

			for i, variant_attr in enumerate(shopify_variants_attr_list):
				if variant.get(variant_attr):
					attributes[i].update({"attribute_value": get_attribute_value(variant.get(variant_attr), attributes[i])})
			create_item(shopify_item_variant, warehouse, 0, attributes, template_item.name)

def get_attribute_value(variant_attr_val, attribute):
	attribute_value = frappe.db.sql("""select attribute_value from `tabItem Attribute Value`
		where parent = %s and (abbr = %s or attribute_value = %s)""", (attribute["attribute"], variant_attr_val,
		variant_attr_val), as_list=1)
	return attribute_value[0][0] if len(attribute_value)>0 else cint(variant_attr_val)

def get_item_group(product_type=None):
	import frappe.utils.nestedset
	parent_item_group = frappe.utils.nestedset.get_root_of("Item Group")

	if product_type:
		if not frappe.db.get_value("Item Group", product_type, "name"):
			item_group = frappe.get_doc({
				"doctype": "Item Group",
				"item_group_name": product_type,
				"parent_item_group": parent_item_group,
				"is_group": "No"
			}).insert()
			return item_group.name
		else:
			return product_type
	else:
		return parent_item_group


def get_sku(item):
	if item.get("variants"):
		return item.get("variants")[0].get("sku")
	return ""

def add_to_price_list(item, name):
	shopify_settings = frappe.db.get_value("Shopify Settings", None, ["price_list", "update_price_in_erpnext_price_list"], as_dict=1)
	if not shopify_settings.update_price_in_erpnext_price_list:
		return

	item_price_name = frappe.db.get_value("Item Price",
		{"item_code": name, "price_list": shopify_settings.price_list}, "name")

	if not item_price_name:
		frappe.get_doc({
			"doctype": "Item Price",
			"price_list": shopify_settings.price_list,
			"item_code": name,
			"price_list_rate": item.get("item_price") or item.get("variants")[0].get("price")
		}).insert()
	else:
		item_rate = frappe.get_doc("Item Price", item_price_name)
		item_rate.price_list_rate = item.get("item_price") or item.get("variants")[0].get("price")
		item_rate.save()

def get_item_image(shopify_item):
	if shopify_item.get("image"):
		return shopify_item.get("image").get("src")
	return None

def get_supplier(shopify_item):
	if shopify_item.get("vendor"):
		supplier = frappe.db.sql("""select name from tabSupplier
			where name = %s or shopify_supplier_id = %s """, (shopify_item.get("vendor"),
			shopify_item.get("vendor").lower()), as_list=1)

		if not supplier:
			supplier = frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": shopify_item.get("vendor"),
				"shopify_supplier_id": shopify_item.get("vendor").lower(),
				"supplier_group": get_supplier_group()
			}).insert()
			return supplier.name
		else:
			return shopify_item.get("vendor")
	else:
		return ""

def get_supplier_group():
	supplier_group = frappe.db.get_value("Supplier Group", _("Shopify Supplier"))
	if not supplier_group:
		supplier_group = frappe.get_doc({
			"doctype": "Supplier Group",
			"supplier_group_name": _("Shopify Supplier")
		}).insert()
		return supplier_group.name
	return supplier_group

def get_item_details(shopify_item):
	item_details = {}

	item_details = frappe.db.get_value("Item", {"shopify_product_id": shopify_item.get("id")},
		["name", "stock_uom", "item_name"], as_dict=1)

	if item_details:
		return item_details

	else:
		item_details = frappe.db.get_value("Item", {"shopify_variant_id": shopify_item.get("id")},
			["name", "stock_uom", "item_name"], as_dict=1)
		return item_details

def is_item_exists(shopify_item, attributes=None, variant_of=None):
	if variant_of:
		name = variant_of
	else:
		name = frappe.db.get_value("Item", {"item_name": shopify_item.get("item_name")})

	if name:
		item = frappe.get_doc("Item", name)
		item.flags.ignore_mandatory=True

		if not variant_of and not item.shopify_product_id:
			item.shopify_product_id = shopify_item.get("shopify_product_id")
			item.shopify_variant_id = shopify_item.get("shopify_variant_id")
			item.save()
			return True

		if item.shopify_product_id and attributes and attributes[0].get("attribute_value"):
			if not variant_of:
				variant_of = frappe.db.get_value("Item",
					{"shopify_product_id": item.shopify_product_id}, "variant_of")

			# create conditions for all item attributes,
			# as we are putting condition basis on OR it will fetch all items matching either of conditions
			# thus comparing matching conditions with len(attributes)
			# which will give exact matching variant item.

			conditions = ["(iv.attribute='{0}' and iv.attribute_value = '{1}')"\
				.format(attr.get("attribute"), attr.get("attribute_value")) for attr in attributes]

			conditions = "( {0} ) and iv.parent = it.name ) = {1}".format(" or ".join(conditions), len(attributes))

			parent = frappe.db.sql(""" select * from tabItem it where
				( select count(*) from `tabItem Variant Attribute` iv
					where {conditions} and it.variant_of = %s """.format(conditions=conditions) ,
				variant_of, as_list=1)

			if parent:
				variant = frappe.get_doc("Item", parent[0][0])
				variant.flags.ignore_mandatory = True

				variant.shopify_product_id = shopify_item.get("shopify_product_id")
				variant.shopify_variant_id = shopify_item.get("shopify_variant_id")
				variant.save()
			return False

		if item.shopify_product_id and item.shopify_product_id != shopify_item.get("shopify_product_id"):
			return False

		return True

	else:
		return False
