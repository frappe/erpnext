# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


class ItemPriceDuplicateItem(frappe.ValidationError): pass


from frappe.model.document import Document


class ItemPrice(Document):
    def validate(self):
        self.validate_item()
        self.validate_dates()
        self.update_price_list_details()
        self.update_item_details()
        self.check_duplicates()

    def validate_item(self):
        if not frappe.db.exists("Item", self.item_code):
            frappe.throw(_("Item {0} not found").format(self.item_code))

    def validate_dates(self):
        if self.valid_from and self.valid_upto:
            if self.valid_from > self.valid_upto:
                frappe.throw(_("Valid From Date must be lesser than Valid Upto Date."))

    def update_price_list_details(self):
        self.buying, self.selling, self.currency = \
            frappe.db.get_value("Price List", {"name": self.price_list, "enabled": 1},
                                ["buying", "selling", "currency"])

    def update_item_details(self):
        self.item_name, self.item_description, self.uom = frappe.db.get_value("Item",self.item_code,["item_name", "description", "stock_uom"])

    def check_duplicates(self):
        conditions = "WHERE item_code = '%s' AND price_list = '%s' AND min_qty = '%s' AND uom = '%s' AND price_list_rate = '%s' " \
                       "AND (valid_from is null or valid_from <= '%s') AND (valid_upto is null or valid_upto >= '%s') AND packing_unit = '%s'" \
                        % (self.item_code, self.price_list, self.min_qty, self.uom, self.price_list_rate, self.valid_from, self.valid_upto, self.packing_unit)

        if self.customer and not self.supplier:
            conditions += "AND customer= '%s'" % (self.customer)

        if self.supplier and not self.customer:
            conditions += "AND supplier= '%s'" % (self.supplier)

        price_list_rate = frappe.db.sql("""
            SELECT price_list_rate
            FROM `tabItem Price`
              %s """ % (conditions))

        if price_list_rate :
            frappe.throw(_(
                "Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, UOM, Qty and Dates."))