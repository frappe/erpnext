# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
import json
from typing import Dict, List, Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	cint,
	cstr,
	flt,
	formatdate,
	get_link_to_form,
	getdate,
	now_datetime,
	nowtime,
	strip,
	strip_html,
)
from frappe.utils.html_utils import clean_html

import erpnext
from erpnext.controllers.item_variant import (
	ItemVariantExistsError,
	copy_attributes_to_variant,
	get_variant,
	make_variant_item_code,
	validate_item_variant_attributes,
)
from erpnext.setup.doctype.item_group.item_group import invalidate_cache_for
from erpnext.stock.doctype.item_default.item_default import ItemDefault


class DuplicateReorderRows(frappe.ValidationError):
	pass


class StockExistsForTemplate(frappe.ValidationError):
	pass


class InvalidBarcode(frappe.ValidationError):
	pass


class DataValidationError(frappe.ValidationError):
	pass


class Item(Document):
	def onload(self):
		self.set_onload("stock_exists", self.stock_ledger_created())
		self.set_onload("asset_naming_series", get_asset_naming_series())

	def autoname(self):
		if frappe.db.get_default("item_naming_by") == "Naming Series":
			if self.variant_of:
				if not self.item_code:
					template_item_name = frappe.db.get_value("Item", self.variant_of, "item_name")
					make_variant_item_code(self.variant_of, template_item_name, self)
			else:
				from frappe.model.naming import set_name_by_naming_series

				set_name_by_naming_series(self)
				self.item_code = self.name

		self.item_code = strip(self.item_code)
		self.name = self.item_code

	def after_insert(self):
		"""set opening stock and item price"""
		if self.standard_rate:
			for default in self.item_defaults or [frappe._dict()]:
				self.add_price(default.default_price_list)

		if self.opening_stock:
			self.set_opening_stock()

	def validate(self):
		if not self.item_name:
			self.item_name = self.item_code

		if not strip_html(cstr(self.description)).strip():
			self.description = self.item_name

		self.validate_uom()
		self.validate_description()
		self.add_default_uom_in_conversion_factor_table()
		self.validate_conversion_factor()
		self.validate_item_type()
		self.validate_naming_series()
		self.check_for_active_boms()
		self.fill_customer_code()
		self.check_item_tax()
		self.validate_barcode()
		self.validate_warehouse_for_reorder()
		self.update_bom_item_desc()

		self.validate_has_variants()
		self.validate_attributes_in_variants()
		self.validate_stock_exists_for_template_item()
		self.validate_attributes()
		self.validate_variant_attributes()
		self.validate_variant_based_on_change()
		self.validate_fixed_asset()
		self.clear_retain_sample()
		self.validate_retain_sample()
		self.validate_uom_conversion_factor()
		self.validate_customer_provided_part()
		self.update_defaults_from_item_group()
		self.validate_item_defaults()
		self.validate_auto_reorder_enabled_in_stock_settings()
		self.cant_change()
		self.validate_item_tax_net_rate_range()
		set_item_tax_from_hsn_code(self)

		if not self.is_new():
			self.old_item_group = frappe.db.get_value(self.doctype, self.name, "item_group")

	def on_update(self):
		invalidate_cache_for_item(self)
		self.update_variants()
		self.update_item_price()
		self.update_website_item()

	def validate_description(self):
		"""Clean HTML description if set"""
		if cint(frappe.db.get_single_value("Stock Settings", "clean_description_html")):
			self.description = clean_html(self.description)

	def validate_customer_provided_part(self):
		if self.is_customer_provided_item:
			if self.is_purchase_item:
				frappe.throw(_('"Customer Provided Item" cannot be Purchase Item also'))
			if self.valuation_rate:
				frappe.throw(_('"Customer Provided Item" cannot have Valuation Rate'))
			self.default_material_request_type = "Customer Provided"

	def add_price(self, price_list=None):
		"""Add a new price"""
		if not price_list:
			price_list = frappe.db.get_single_value(
				"Selling Settings", "selling_price_list"
			) or frappe.db.get_value("Price List", _("Standard Selling"))
		if price_list:
			item_price = frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": price_list,
					"item_code": self.name,
					"uom": self.stock_uom,
					"brand": self.brand,
					"currency": erpnext.get_default_currency(),
					"price_list_rate": self.standard_rate,
				}
			)
			item_price.insert()

	def set_opening_stock(self):
		"""set opening stock"""
		if not self.is_stock_item or self.has_serial_no or self.has_batch_no:
			return

		if not self.valuation_rate and self.standard_rate:
			self.valuation_rate = self.standard_rate

		if not self.valuation_rate and not self.is_customer_provided_item:
			frappe.throw(_("Valuation Rate is mandatory if Opening Stock entered"))

		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		# default warehouse, or Stores
		for default in self.item_defaults or [
			frappe._dict({"company": frappe.defaults.get_defaults().company})
		]:
			default_warehouse = default.default_warehouse or frappe.db.get_single_value(
				"Stock Settings", "default_warehouse"
			)
			if default_warehouse:
				warehouse_company = frappe.db.get_value("Warehouse", default_warehouse, "company")

			if not default_warehouse or warehouse_company != default.company:
				default_warehouse = frappe.db.get_value(
					"Warehouse", {"warehouse_name": _("Stores"), "company": default.company}
				)

			if default_warehouse:
				stock_entry = make_stock_entry(
					item_code=self.name,
					target=default_warehouse,
					qty=self.opening_stock,
					rate=self.valuation_rate,
					company=default.company,
					posting_date=getdate(),
					posting_time=nowtime(),
				)

				stock_entry.add_comment("Comment", _("Opening Stock"))

	def validate_fixed_asset(self):
		if self.is_fixed_asset:
			if self.is_stock_item:
				frappe.throw(_("Fixed Asset Item must be a non-stock item."))

			if not self.asset_category:
				frappe.throw(_("Asset Category is mandatory for Fixed Asset item"))

			if self.stock_ledger_created():
				frappe.throw(_("Cannot be a fixed asset item as Stock Ledger is created."))

		if not self.is_fixed_asset:
			asset = frappe.db.get_all("Asset", filters={"item_code": self.name, "docstatus": 1}, limit=1)
			if asset:
				frappe.throw(
					_('"Is Fixed Asset" cannot be unchecked, as Asset record exists against the item')
				)

	def validate_retain_sample(self):
		if self.retain_sample and not frappe.db.get_single_value(
			"Stock Settings", "sample_retention_warehouse"
		):
			frappe.throw(_("Please select Sample Retention Warehouse in Stock Settings first"))
		if self.retain_sample and not self.has_batch_no:
			frappe.throw(
				_(
					"{0} Retain Sample is based on batch, please check Has Batch No to retain sample of item"
				).format(self.item_code)
			)

	def clear_retain_sample(self):
		if not self.has_batch_no:
			self.retain_sample = None

		if not self.retain_sample:
			self.sample_quantity = None

	def add_default_uom_in_conversion_factor_table(self):
		if not self.is_new() and self.has_value_changed("stock_uom"):
			self.uoms = []
			frappe.msgprint(
				_("Successfully changed Stock UOM, please redefine conversion factors for new UOM."),
				alert=True,
			)

		uoms_list = [d.uom for d in self.get("uoms")]

		if self.stock_uom not in uoms_list:
			self.append("uoms", {"uom": self.stock_uom, "conversion_factor": 1})

	def update_website_item(self):
		"""Update Website Item if change in Item impacts it."""
		web_item = frappe.db.exists("Website Item", {"item_code": self.item_code})

		if web_item:
			changed = {}
			editable_fields = ["item_name", "item_group", "stock_uom", "brand", "description", "disabled"]
			doc_before_save = self.get_doc_before_save()

			for field in editable_fields:
				if doc_before_save.get(field) != self.get(field):
					if field == "disabled":
						changed["published"] = not self.get(field)
					else:
						changed[field] = self.get(field)

			if not changed:
				return

			web_item_doc = frappe.get_doc("Website Item", web_item)
			web_item_doc.update(changed)
			web_item_doc.save()

	def validate_item_tax_net_rate_range(self):
		for tax in self.get("taxes"):
			if flt(tax.maximum_net_rate) < flt(tax.minimum_net_rate):
				frappe.throw(_("Row #{0}: Maximum Net Rate cannot be greater than Minimum Net Rate"))

	def update_template_tables(self):
		template = frappe.get_doc("Item", self.variant_of)

		# add item taxes from template
		for d in template.get("taxes"):
			self.append("taxes", {"item_tax_template": d.item_tax_template})

		# copy re-order table if empty
		if not self.get("reorder_levels"):
			for d in template.get("reorder_levels"):
				n = {}
				for k in (
					"warehouse",
					"warehouse_reorder_level",
					"warehouse_reorder_qty",
					"material_request_type",
				):
					n[k] = d.get(k)
				self.append("reorder_levels", n)

	def validate_conversion_factor(self):
		check_list = []
		for d in self.get("uoms"):
			if cstr(d.uom) in check_list:
				frappe.throw(
					_("Unit of Measure {0} has been entered more than once in Conversion Factor Table").format(
						d.uom
					)
				)
			else:
				check_list.append(cstr(d.uom))

			if d.uom and cstr(d.uom) == cstr(self.stock_uom) and flt(d.conversion_factor) != 1:
				frappe.throw(
					_("Conversion factor for default Unit of Measure must be 1 in row {0}").format(d.idx)
				)

	def validate_item_type(self):
		if self.has_serial_no == 1 and self.is_stock_item == 0 and not self.is_fixed_asset:
			frappe.throw(_("'Has Serial No' can not be 'Yes' for non-stock item"))

		if self.has_serial_no == 0 and self.serial_no_series:
			self.serial_no_series = None

	def validate_naming_series(self):
		for field in ["serial_no_series", "batch_number_series"]:
			series = self.get(field)
			if series and "#" in series and "." not in series:
				frappe.throw(
					_("Invalid naming series (. missing) for {0}").format(
						frappe.bold(self.meta.get_field(field).label)
					)
				)

	def check_for_active_boms(self):
		if self.default_bom:
			bom_item = frappe.db.get_value("BOM", self.default_bom, "item")
			if bom_item not in (self.name, self.variant_of):
				frappe.throw(
					_("Default BOM ({0}) must be active for this item or its template").format(bom_item)
				)

	def fill_customer_code(self):
		"""
		Append all the customer codes and insert into "customer_code" field of item table.
		Used to search Item by customer code.
		"""
		customer_codes = set(d.ref_code for d in self.get("customer_items", []))
		self.customer_code = ",".join(customer_codes)

	def check_item_tax(self):
		"""Check whether Tax Rate is not entered twice for same Tax Type"""
		check_list = []
		for d in self.get("taxes"):
			if d.item_tax_template:
				if d.item_tax_template in check_list:
					frappe.throw(_("{0} entered twice in Item Tax").format(d.item_tax_template))
				else:
					check_list.append(d.item_tax_template)

	def validate_barcode(self):
		from stdnum import ean

		if len(self.barcodes) > 0:
			for item_barcode in self.barcodes:
				options = frappe.get_meta("Item Barcode").get_options("barcode_type").split("\n")
				if item_barcode.barcode:
					duplicate = frappe.db.sql(
						"""select parent from `tabItem Barcode` where barcode = %s and parent != %s""",
						(item_barcode.barcode, self.name),
					)
					if duplicate:
						frappe.throw(
							_("Barcode {0} already used in Item {1}").format(item_barcode.barcode, duplicate[0][0])
						)

					item_barcode.barcode_type = (
						"" if item_barcode.barcode_type not in options else item_barcode.barcode_type
					)
					if item_barcode.barcode_type and item_barcode.barcode_type.upper() in (
						"EAN",
						"UPC-A",
						"EAN-13",
						"EAN-8",
					):
						if not ean.is_valid(item_barcode.barcode):
							frappe.throw(
								_("Barcode {0} is not a valid {1} code").format(
									item_barcode.barcode, item_barcode.barcode_type
								),
								InvalidBarcode,
							)

	def validate_warehouse_for_reorder(self):
		"""Validate Reorder level table for duplicate and conditional mandatory"""
		warehouse = []
		for d in self.get("reorder_levels"):
			if not d.warehouse_group:
				d.warehouse_group = d.warehouse
			if d.get("warehouse") and d.get("warehouse") not in warehouse:
				warehouse += [d.get("warehouse")]
			else:
				frappe.throw(
					_("Row {0}: An Reorder entry already exists for this warehouse {1}").format(
						d.idx, d.warehouse
					),
					DuplicateReorderRows,
				)

			if d.warehouse_reorder_level and not d.warehouse_reorder_qty:
				frappe.throw(_("Row #{0}: Please set reorder quantity").format(d.idx))

	def stock_ledger_created(self):
		if not hasattr(self, "_stock_ledger_created"):
			self._stock_ledger_created = len(
				frappe.db.sql(
					"""select name from `tabStock Ledger Entry`
				where item_code = %s and is_cancelled = 0 limit 1""",
					self.name,
				)
			)
		return self._stock_ledger_created

	def update_item_price(self):
		frappe.db.sql(
			"""
				UPDATE `tabItem Price`
				SET
					item_name=%(item_name)s,
					item_description=%(item_description)s,
					brand=%(brand)s
				WHERE item_code=%(item_code)s
			""",
			dict(
				item_name=self.item_name,
				item_description=self.description,
				brand=self.brand,
				item_code=self.name,
			),
		)

	def on_trash(self):
		frappe.db.sql("""delete from tabBin where item_code=%s""", self.name)
		frappe.db.sql("delete from `tabItem Price` where item_code=%s", self.name)
		for variant_of in frappe.get_all("Item", filters={"variant_of": self.name}):
			frappe.delete_doc("Item", variant_of.name)

	def before_rename(self, old_name, new_name, merge=False):
		if self.item_name == old_name:
			frappe.db.set_value("Item", old_name, "item_name", new_name)

		if merge:
			self.validate_properties_before_merge(new_name)
			self.validate_duplicate_product_bundles_before_merge(old_name, new_name)
			self.validate_duplicate_website_item_before_merge(old_name, new_name)
			self.delete_old_bins(old_name)

	def after_rename(self, old_name, new_name, merge):
		if merge:
			self.validate_duplicate_item_in_stock_reconciliation(old_name, new_name)
			frappe.msgprint(
				_("It can take upto few hours for accurate stock values to be visible after merging items."),
				indicator="orange",
				title=_("Note"),
			)

		if self.published_in_website:
			invalidate_cache_for_item(self)

		frappe.db.set_value("Item", new_name, "item_code", new_name)

		if merge:
			self.set_last_purchase_rate(new_name)
			self.recalculate_bin_qty(new_name)

		for dt in ("Sales Taxes and Charges", "Purchase Taxes and Charges"):
			for d in frappe.db.sql(
				"""select name, item_wise_tax_detail from `tab{0}`
					where ifnull(item_wise_tax_detail, '') != ''""".format(
					dt
				),
				as_dict=1,
			):

				item_wise_tax_detail = json.loads(d.item_wise_tax_detail)
				if isinstance(item_wise_tax_detail, dict) and old_name in item_wise_tax_detail:
					item_wise_tax_detail[new_name] = item_wise_tax_detail[old_name]
					item_wise_tax_detail.pop(old_name)

					frappe.db.set_value(
						dt, d.name, "item_wise_tax_detail", json.dumps(item_wise_tax_detail), update_modified=False
					)

	def delete_old_bins(self, old_name):
		frappe.db.delete("Bin", {"item_code": old_name})

	def validate_duplicate_item_in_stock_reconciliation(self, old_name, new_name):
		records = frappe.db.sql(
			""" SELECT parent, COUNT(*) as records
			FROM `tabStock Reconciliation Item`
			WHERE item_code = %s and docstatus = 1
			GROUP By item_code, warehouse, parent
			HAVING records > 1
		""",
			new_name,
			as_dict=1,
		)

		if not records:
			return
		document = _("Stock Reconciliation") if len(records) == 1 else _("Stock Reconciliations")

		msg = _("The items {0} and {1} are present in the following {2} :").format(
			frappe.bold(old_name), frappe.bold(new_name), document
		)

		msg += " <br>"
		msg += (
			", ".join([get_link_to_form("Stock Reconciliation", d.parent) for d in records]) + "<br><br>"
		)

		msg += _(
			"Note: To merge the items, create a separate Stock Reconciliation for the old item {0}"
		).format(frappe.bold(old_name))

		frappe.throw(_(msg), title=_("Cannot Merge"), exc=DataValidationError)

	def validate_properties_before_merge(self, new_name):
		# Validate properties before merging
		if not frappe.db.exists("Item", new_name):
			frappe.throw(_("Item {0} does not exist").format(new_name))

		field_list = ["stock_uom", "is_stock_item", "has_serial_no", "has_batch_no"]
		new_properties = [cstr(d) for d in frappe.db.get_value("Item", new_name, field_list)]

		if new_properties != [cstr(self.get(field)) for field in field_list]:
			msg = _("To merge, following properties must be same for both items")
			msg += ": \n" + ", ".join([self.meta.get_label(fld) for fld in field_list])
			frappe.throw(msg, title=_("Cannot Merge"), exc=DataValidationError)

	def validate_duplicate_product_bundles_before_merge(self, old_name, new_name):
		"Block merge if both old and new items have product bundles."
		old_bundle = frappe.get_value("Product Bundle", filters={"new_item_code": old_name})
		new_bundle = frappe.get_value("Product Bundle", filters={"new_item_code": new_name})

		if old_bundle and new_bundle:
			bundle_link = get_link_to_form("Product Bundle", old_bundle)
			old_name, new_name = frappe.bold(old_name), frappe.bold(new_name)

			msg = _("Please delete Product Bundle {0}, before merging {1} into {2}").format(
				bundle_link, old_name, new_name
			)
			frappe.throw(msg, title=_("Cannot Merge"), exc=DataValidationError)

	def validate_duplicate_website_item_before_merge(self, old_name, new_name):
		"""
		Block merge if both old and new items have website items against them.
		This is to avoid duplicate website items after merging.
		"""
		web_items = frappe.get_all(
			"Website Item",
			filters={"item_code": ["in", [old_name, new_name]]},
			fields=["item_code", "name"],
		)

		if len(web_items) <= 1:
			return

		old_web_item = [d.get("name") for d in web_items if d.get("item_code") == old_name][0]
		web_item_link = get_link_to_form("Website Item", old_web_item)
		old_name, new_name = frappe.bold(old_name), frappe.bold(new_name)

		msg = f"Please delete linked Website Item {frappe.bold(web_item_link)} before merging {old_name} into {new_name}"
		frappe.throw(_(msg), title=_("Cannot Merge"), exc=DataValidationError)

	def set_last_purchase_rate(self, new_name):
		last_purchase_rate = get_last_purchase_details(new_name).get("base_net_rate", 0)
		frappe.db.set_value("Item", new_name, "last_purchase_rate", last_purchase_rate)

	def recalculate_bin_qty(self, new_name):
		from erpnext.stock.stock_balance import repost_stock

		existing_allow_negative_stock = frappe.db.get_value(
			"Stock Settings", None, "allow_negative_stock"
		)
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

		repost_stock_for_warehouses = frappe.get_all(
			"Stock Ledger Entry",
			"warehouse",
			filters={"item_code": new_name},
			pluck="warehouse",
			distinct=True,
		)

		# Delete all existing bins to avoid duplicate bins for the same item and warehouse
		frappe.db.delete("Bin", {"item_code": new_name})

		for warehouse in repost_stock_for_warehouses:
			repost_stock(new_name, warehouse)

		frappe.db.set_value(
			"Stock Settings", None, "allow_negative_stock", existing_allow_negative_stock
		)

	def update_bom_item_desc(self):
		if self.is_new():
			return

		if self.db_get("description") != self.description:
			frappe.db.sql(
				"""
				update `tabBOM`
				set description = %s
				where item = %s and docstatus < 2
			""",
				(self.description, self.name),
			)

			frappe.db.sql(
				"""
				update `tabBOM Item`
				set description = %s
				where item_code = %s and docstatus < 2
			""",
				(self.description, self.name),
			)

			frappe.db.sql(
				"""
				update `tabBOM Explosion Item`
				set description = %s
				where item_code = %s and docstatus < 2
			""",
				(self.description, self.name),
			)

	def validate_item_defaults(self):
		companies = {row.company for row in self.item_defaults}

		if len(companies) != len(self.item_defaults):
			frappe.throw(_("Cannot set multiple Item Defaults for a company."))

		validate_item_default_company_links(self.item_defaults)

	def update_defaults_from_item_group(self):
		"""Get defaults from Item Group"""
		if self.item_defaults or not self.item_group:
			return

		item_defaults = frappe.db.get_values(
			"Item Default",
			{"parent": self.item_group},
			[
				"company",
				"default_warehouse",
				"default_price_list",
				"buying_cost_center",
				"default_supplier",
				"expense_account",
				"selling_cost_center",
				"income_account",
			],
			as_dict=1,
		)
		if item_defaults:
			for item in item_defaults:
				self.append(
					"item_defaults",
					{
						"company": item.company,
						"default_warehouse": item.default_warehouse,
						"default_price_list": item.default_price_list,
						"buying_cost_center": item.buying_cost_center,
						"default_supplier": item.default_supplier,
						"expense_account": item.expense_account,
						"selling_cost_center": item.selling_cost_center,
						"income_account": item.income_account,
					},
				)
		else:
			defaults = frappe.defaults.get_defaults() or {}

			# To check default warehouse is belong to the default company
			if (
				defaults.get("default_warehouse")
				and defaults.company
				and frappe.db.exists(
					"Warehouse", {"name": defaults.default_warehouse, "company": defaults.company}
				)
			):
				self.append(
					"item_defaults",
					{"company": defaults.get("company"), "default_warehouse": defaults.default_warehouse},
				)

	def update_variants(self):
		if self.flags.dont_update_variants or frappe.db.get_single_value(
			"Item Variant Settings", "do_not_update_variants"
		):
			return
		if self.has_variants:
			variants = frappe.db.get_all("Item", fields=["item_code"], filters={"variant_of": self.name})
			if variants:
				if len(variants) <= 30:
					update_variants(variants, self, publish_progress=False)
					frappe.msgprint(_("Item Variants updated"))
				else:
					frappe.enqueue(
						"erpnext.stock.doctype.item.item.update_variants",
						variants=variants,
						template=self,
						now=frappe.flags.in_test,
						timeout=600,
					)

	def validate_has_variants(self):
		if not self.has_variants and frappe.db.get_value("Item", self.name, "has_variants"):
			if frappe.db.exists("Item", {"variant_of": self.name}):
				frappe.throw(_("Item has variants."))

	def validate_attributes_in_variants(self):
		if not self.has_variants or self.is_new():
			return

		old_doc = self.get_doc_before_save()
		old_doc_attributes = set([attr.attribute for attr in old_doc.attributes])
		own_attributes = [attr.attribute for attr in self.attributes]

		# Check if old attributes were removed from the list
		# Is old_attrs is a subset of new ones
		# that means we need not check any changes
		if old_doc_attributes.issubset(set(own_attributes)):
			return

		from collections import defaultdict

		# get all item variants
		items = [item["name"] for item in frappe.get_all("Item", {"variant_of": self.name})]

		# get all deleted attributes
		deleted_attribute = list(old_doc_attributes.difference(set(own_attributes)))

		# fetch all attributes of these items
		item_attributes = frappe.get_all(
			"Item Variant Attribute",
			filters={"parent": ["in", items], "attribute": ["in", deleted_attribute]},
			fields=["attribute", "parent"],
		)
		not_included = defaultdict(list)

		for attr in item_attributes:
			if attr["attribute"] not in own_attributes:
				not_included[attr["parent"]].append(attr["attribute"])

		if not len(not_included):
			return

		def body(docnames):
			docnames.sort()
			return "<br>".join(docnames)

		def table_row(title, body):
			return """<tr>
				<td>{0}</td>
				<td>{1}</td>
			</tr>""".format(
				title, body
			)

		rows = ""
		for docname, attr_list in not_included.items():
			link = "<a href='/app/Form/Item/{0}'>{0}</a>".format(frappe.bold(_(docname)))
			rows += table_row(link, body(attr_list))

		error_description = _(
			"The following deleted attributes exist in Variants but not in the Template. You can either delete the Variants or keep the attribute(s) in template."
		)

		message = """
			<div>{0}</div><br>
			<table class="table">
				<thead>
					<td>{1}</td>
					<td>{2}</td>
				</thead>
				{3}
			</table>
		""".format(
			error_description, _("Variant Items"), _("Attributes"), rows
		)

		frappe.throw(message, title=_("Variant Attribute Error"), is_minimizable=True, wide=True)

	def validate_stock_exists_for_template_item(self):
		if self.stock_ledger_created() and self._doc_before_save:
			if (
				cint(self._doc_before_save.has_variants) != cint(self.has_variants)
				or self._doc_before_save.variant_of != self.variant_of
			):
				frappe.throw(
					_(
						"Cannot change Variant properties after stock transaction. You will have to make a new Item to do this."
					).format(self.name),
					StockExistsForTemplate,
				)

			if self.has_variants or self.variant_of:
				if not self.is_child_table_same("attributes"):
					frappe.throw(
						_(
							"Cannot change Attributes after stock transaction. Make a new Item and transfer stock to the new Item"
						)
					)

	def validate_variant_based_on_change(self):
		if not self.is_new() and (
			self.variant_of or (self.has_variants and frappe.get_all("Item", {"variant_of": self.name}))
		):
			if self.variant_based_on != frappe.db.get_value("Item", self.name, "variant_based_on"):
				frappe.throw(_("Variant Based On cannot be changed"))

	def validate_uom(self):
		if not self.is_new():
			check_stock_uom_with_bin(self.name, self.stock_uom)
		if self.has_variants:
			for d in frappe.db.get_all("Item", filters={"variant_of": self.name}):
				check_stock_uom_with_bin(d.name, self.stock_uom)
		if self.variant_of:
			template_uom = frappe.db.get_value("Item", self.variant_of, "stock_uom")
			if template_uom != self.stock_uom:
				frappe.throw(
					_("Default Unit of Measure for Variant '{0}' must be same as in Template '{1}'").format(
						self.stock_uom, template_uom
					)
				)

	def validate_uom_conversion_factor(self):
		if self.uoms:
			for d in self.uoms:
				value = get_uom_conv_factor(d.uom, self.stock_uom)
				if value:
					d.conversion_factor = value

	def validate_attributes(self):
		if not (self.has_variants or self.variant_of):
			return

		if not self.variant_based_on:
			self.variant_based_on = "Item Attribute"

		if self.variant_based_on == "Item Attribute":
			attributes = []
			if not self.attributes:
				frappe.throw(_("Attribute table is mandatory"))
			for d in self.attributes:
				if d.attribute in attributes:
					frappe.throw(
						_("Attribute {0} selected multiple times in Attributes Table").format(d.attribute)
					)
				else:
					attributes.append(d.attribute)

	def validate_variant_attributes(self):
		if self.is_new() and self.variant_of and self.variant_based_on == "Item Attribute":
			# remove attributes with no attribute_value set
			self.attributes = [d for d in self.attributes if cstr(d.attribute_value).strip()]

			args = {}
			for i, d in enumerate(self.attributes):
				d.idx = i + 1
				args[d.attribute] = d.attribute_value

			variant = get_variant(self.variant_of, args, self.name)
			if variant:
				frappe.throw(
					_("Item variant {0} exists with same attributes").format(variant), ItemVariantExistsError
				)

			validate_item_variant_attributes(self, args)

			# copy variant_of value for each attribute row
			for d in self.attributes:
				d.variant_of = self.variant_of

	def cant_change(self):
		if self.is_new():
			return

		restricted_fields = ("has_serial_no", "is_stock_item", "valuation_method", "has_batch_no")

		values = frappe.db.get_value("Item", self.name, restricted_fields, as_dict=True)
		if not values:
			return

		if not values.get("valuation_method") and self.get("valuation_method"):
			values["valuation_method"] = (
				frappe.db.get_single_value("Stock Settings", "valuation_method") or "FIFO"
			)

		changed_fields = [
			field for field in restricted_fields if cstr(self.get(field)) != cstr(values.get(field))
		]
		if not changed_fields:
			return

		if linked_doc := self._get_linked_submitted_documents(changed_fields):
			changed_field_labels = [frappe.bold(self.meta.get_label(f)) for f in changed_fields]
			msg = _(
				"As there are existing submitted transactions against item {0}, you can not change the value of {1}."
			).format(self.name, ", ".join(changed_field_labels))

			if linked_doc and isinstance(linked_doc, dict):
				msg += "<br>"
				msg += _("Example of a linked document: {0}").format(
					frappe.get_desk_link(linked_doc.doctype, linked_doc.docname)
				)

			frappe.throw(msg, title=_("Linked with submitted documents"))

	def _get_linked_submitted_documents(self, changed_fields: List[str]) -> Optional[Dict[str, str]]:
		linked_doctypes = [
			"Delivery Note Item",
			"Sales Invoice Item",
			"POS Invoice Item",
			"Purchase Receipt Item",
			"Purchase Invoice Item",
			"Stock Entry Detail",
			"Stock Reconciliation Item",
		]

		# For "Is Stock Item", following doctypes is important
		# because reserved_qty, ordered_qty and requested_qty updated from these doctypes
		if "is_stock_item" in changed_fields:
			linked_doctypes += [
				"Sales Order Item",
				"Purchase Order Item",
				"Material Request Item",
				"Product Bundle",
			]

		for doctype in linked_doctypes:
			filters = {"item_code": self.name, "docstatus": 1}

			if doctype == "Product Bundle":
				filters = {"new_item_code": self.name}

			if doctype in (
				"Purchase Invoice Item",
				"Sales Invoice Item",
			):
				# If Invoice has Stock impact, only then consider it.
				if linked_doc := frappe.db.get_value(
					"Stock Ledger Entry",
					{"item_code": self.name, "is_cancelled": 0},
					["voucher_no as docname", "voucher_type as doctype"],
					as_dict=True,
				):
					return linked_doc

			elif linked_doc := frappe.db.get_value(
				doctype,
				filters,
				["parent as docname", "parenttype as doctype"],
				as_dict=True,
			):
				return linked_doc

	def validate_auto_reorder_enabled_in_stock_settings(self):
		if self.reorder_levels:
			enabled = frappe.db.get_single_value("Stock Settings", "auto_indent")
			if not enabled:
				frappe.msgprint(
					msg=_("You have to enable auto re-order in Stock Settings to maintain re-order levels."),
					title=_("Enable Auto Re-Order"),
					indicator="orange",
				)


def make_item_price(item, price_list_name, item_price):
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"price_list": price_list_name,
			"item_code": item,
			"price_list_rate": item_price,
		}
	).insert()


def get_timeline_data(doctype, name):
	"""get timeline data based on Stock Ledger Entry. This is displayed as heatmap on the item page."""

	items = frappe.db.sql(
		"""select unix_timestamp(posting_date), count(*)
							from `tabStock Ledger Entry`
							where item_code=%s and posting_date > date_sub(curdate(), interval 1 year)
							group by posting_date""",
		name,
	)

	return dict(items)


def validate_end_of_life(item_code, end_of_life=None, disabled=None):
	if (not end_of_life) or (disabled is None):
		end_of_life, disabled = frappe.db.get_value("Item", item_code, ["end_of_life", "disabled"])

	if end_of_life and end_of_life != "0000-00-00" and getdate(end_of_life) <= now_datetime().date():
		frappe.throw(
			_("Item {0} has reached its end of life on {1}").format(item_code, formatdate(end_of_life))
		)

	if disabled:
		frappe.throw(_("Item {0} is disabled").format(item_code))


def validate_is_stock_item(item_code, is_stock_item=None):
	if not is_stock_item:
		is_stock_item = frappe.db.get_value("Item", item_code, "is_stock_item")

	if is_stock_item != 1:
		frappe.throw(_("Item {0} is not a stock Item").format(item_code))


def validate_cancelled_item(item_code, docstatus=None):
	if docstatus is None:
		docstatus = frappe.db.get_value("Item", item_code, "docstatus")

	if docstatus == 2:
		frappe.throw(_("Item {0} is cancelled").format(item_code))


def get_last_purchase_details(item_code, doc_name=None, conversion_rate=1.0):
	"""returns last purchase details in stock uom"""
	# get last purchase order item details

	last_purchase_order = frappe.db.sql(
		"""\
		select po.name, po.transaction_date, po.conversion_rate,
			po_item.conversion_factor, po_item.base_price_list_rate,
			po_item.discount_percentage, po_item.base_rate, po_item.base_net_rate
		from `tabPurchase Order` po, `tabPurchase Order Item` po_item
		where po.docstatus = 1 and po_item.item_code = %s and po.name != %s and
			po.name = po_item.parent
		order by po.transaction_date desc, po.name desc
		limit 1""",
		(item_code, cstr(doc_name)),
		as_dict=1,
	)

	# get last purchase receipt item details
	last_purchase_receipt = frappe.db.sql(
		"""\
		select pr.name, pr.posting_date, pr.posting_time, pr.conversion_rate,
			pr_item.conversion_factor, pr_item.base_price_list_rate, pr_item.discount_percentage,
			pr_item.base_rate, pr_item.base_net_rate
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
		where pr.docstatus = 1 and pr_item.item_code = %s and pr.name != %s and
			pr.name = pr_item.parent
		order by pr.posting_date desc, pr.posting_time desc, pr.name desc
		limit 1""",
		(item_code, cstr(doc_name)),
		as_dict=1,
	)

	purchase_order_date = getdate(
		last_purchase_order and last_purchase_order[0].transaction_date or "1900-01-01"
	)
	purchase_receipt_date = getdate(
		last_purchase_receipt and last_purchase_receipt[0].posting_date or "1900-01-01"
	)

	if last_purchase_order and (
		purchase_order_date >= purchase_receipt_date or not last_purchase_receipt
	):
		# use purchase order

		last_purchase = last_purchase_order[0]
		purchase_date = purchase_order_date

	elif last_purchase_receipt and (
		purchase_receipt_date > purchase_order_date or not last_purchase_order
	):
		# use purchase receipt
		last_purchase = last_purchase_receipt[0]
		purchase_date = purchase_receipt_date

	else:
		return frappe._dict()

	conversion_factor = flt(last_purchase.conversion_factor)
	out = frappe._dict(
		{
			"base_price_list_rate": flt(last_purchase.base_price_list_rate) / conversion_factor,
			"base_rate": flt(last_purchase.base_rate) / conversion_factor,
			"base_net_rate": flt(last_purchase.base_net_rate) / conversion_factor,
			"discount_percentage": flt(last_purchase.discount_percentage),
			"purchase_date": purchase_date,
		}
	)

	conversion_rate = flt(conversion_rate) or 1.0
	out.update(
		{
			"price_list_rate": out.base_price_list_rate / conversion_rate,
			"rate": out.base_rate / conversion_rate,
			"base_rate": out.base_rate,
			"base_net_rate": out.base_net_rate,
		}
	)

	return out


def invalidate_cache_for_item(doc):
	"""Invalidate Item Group cache and rebuild ItemVariantsCacheManager."""
	invalidate_cache_for(doc, doc.item_group)

	if doc.get("old_item_group") and doc.get("old_item_group") != doc.item_group:
		invalidate_cache_for(doc, doc.old_item_group)

	invalidate_item_variants_cache_for_website(doc)


def invalidate_item_variants_cache_for_website(doc):
	"""Rebuild ItemVariantsCacheManager via Item or Website Item."""
	from erpnext.e_commerce.variant_selector.item_variants_cache import ItemVariantsCacheManager

	item_code = None
	is_web_item = doc.get("published_in_website") or doc.get("published")
	if doc.has_variants and is_web_item:
		item_code = doc.item_code
	elif doc.variant_of and frappe.db.get_value("Item", doc.variant_of, "published_in_website"):
		item_code = doc.variant_of

	if item_code:
		item_cache = ItemVariantsCacheManager(item_code)
		item_cache.rebuild_cache()


def check_stock_uom_with_bin(item, stock_uom):
	if stock_uom == frappe.db.get_value("Item", item, "stock_uom"):
		return

	ref_uom = frappe.db.get_value("Stock Ledger Entry", {"item_code": item}, "stock_uom")

	if ref_uom:
		if cstr(ref_uom) != cstr(stock_uom):
			frappe.throw(
				_(
					"Default Unit of Measure for Item {0} cannot be changed directly because you have already made some transaction(s) with another UOM. You will need to create a new Item to use a different Default UOM."
				).format(item)
			)

	bin_list = frappe.db.sql(
		"""
			select * from tabBin where item_code = %s
				and (reserved_qty > 0 or ordered_qty > 0 or indented_qty > 0 or planned_qty > 0)
				and stock_uom != %s
			""",
		(item, stock_uom),
		as_dict=1,
	)

	if bin_list:
		frappe.throw(
			_(
				"Default Unit of Measure for Item {0} cannot be changed directly because you have already made some transaction(s) with another UOM. You need to either cancel the linked documents or create a new Item."
			).format(item)
		)

	# No SLE or documents against item. Bin UOM can be changed safely.
	frappe.db.sql("""update tabBin set stock_uom=%s where item_code=%s""", (stock_uom, item))


def get_item_defaults(item_code, company):
	item = frappe.get_cached_doc("Item", item_code)

	out = item.as_dict()

	for d in item.item_defaults:
		if d.company == company:
			row = copy.deepcopy(d.as_dict())
			row.pop("name")
			out.update(row)
	return out


def set_item_default(item_code, company, fieldname, value):
	item = frappe.get_cached_doc("Item", item_code)

	for d in item.item_defaults:
		if d.company == company:
			if not d.get(fieldname):
				frappe.db.set_value(d.doctype, d.name, fieldname, value)
			return

	# no row found, add a new row for the company
	d = item.append("item_defaults", {fieldname: value, "company": company})
	d.db_insert()
	item.clear_cache()


@frappe.whitelist()
def get_item_details(item_code, company=None):
	out = frappe._dict()
	if company:
		out = get_item_defaults(item_code, company) or frappe._dict()

	doc = frappe.get_cached_doc("Item", item_code)
	out.update(doc.as_dict())

	return out


@frappe.whitelist()
def get_uom_conv_factor(uom, stock_uom):
	"""Get UOM conversion factor from uom to stock_uom
	e.g. uom = "Kg", stock_uom = "Gram" then returns 1000.0
	"""
	if uom == stock_uom:
		return 1.0

	from_uom, to_uom = uom, stock_uom  # renaming for readability

	exact_match = frappe.db.get_value(
		"UOM Conversion Factor", {"to_uom": to_uom, "from_uom": from_uom}, ["value"], as_dict=1
	)
	if exact_match:
		return exact_match.value

	inverse_match = frappe.db.get_value(
		"UOM Conversion Factor", {"to_uom": from_uom, "from_uom": to_uom}, ["value"], as_dict=1
	)
	if inverse_match:
		return 1 / inverse_match.value

	# This attempts to try and get conversion from intermediate UOM.
	# case:
	# 			 g -> mg = 1000
	# 			 g -> kg = 0.001
	# therefore	 kg -> mg = 1000  / 0.001 = 1,000,000
	intermediate_match = frappe.db.sql(
		"""
			select (first.value / second.value) as value
			from `tabUOM Conversion Factor` first
			join `tabUOM Conversion Factor` second
				on first.from_uom = second.from_uom
			where
				first.to_uom = %(to_uom)s
				and second.to_uom = %(from_uom)s
			limit 1
			""",
		{"to_uom": to_uom, "from_uom": from_uom},
		as_dict=1,
	)

	if intermediate_match:
		return intermediate_match[0].value


@frappe.whitelist()
def get_item_attribute(parent, attribute_value=""):
	"""Used for providing auto-completions in child table."""
	if not frappe.has_permission("Item"):
		frappe.throw(_("No Permission"))

	return frappe.get_all(
		"Item Attribute Value",
		fields=["attribute_value"],
		filters={"parent": parent, "attribute_value": ("like", f"%{attribute_value}%")},
	)


def update_variants(variants, template, publish_progress=True):
	total = len(variants)
	for count, d in enumerate(variants, start=1):
		variant = frappe.get_doc("Item", d)
		copy_attributes_to_variant(template, variant)
		variant.save()
		if publish_progress:
			frappe.publish_progress(count / total * 100, title=_("Updating Variants..."))


@erpnext.allow_regional
def set_item_tax_from_hsn_code(item):
	pass


def validate_item_default_company_links(item_defaults: List[ItemDefault]) -> None:
	for item_default in item_defaults:
		for doctype, field in [
			["Warehouse", "default_warehouse"],
			["Cost Center", "buying_cost_center"],
			["Cost Center", "selling_cost_center"],
			["Account", "expense_account"],
			["Account", "income_account"],
		]:
			if item_default.get(field):
				company = frappe.db.get_value(doctype, item_default.get(field), "company", cache=True)
				if company and company != item_default.company:
					frappe.throw(
						_("Row #{}: {} {} doesn't belong to Company {}. Please select valid {}.").format(
							item_default.idx,
							doctype,
							frappe.bold(item_default.get(field)),
							frappe.bold(item_default.company),
							frappe.bold(frappe.unscrub(field)),
						),
						title=_("Invalid Item Defaults"),
					)


@frappe.whitelist()
def get_asset_naming_series():
	from erpnext.assets.doctype.asset.asset import get_asset_naming_series

	return get_asset_naming_series()
