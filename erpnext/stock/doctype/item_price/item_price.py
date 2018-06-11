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
            frappe.db.get_value("Price List", 
                                {"name": self.price_list, "enabled": 1},
                                ["buying", "selling", "currency"])

    def update_item_details(self):
        self.item_name, self.item_description, self.uom = frappe.db.get_value("Item",self.item_code,["item_name", "description", "stock_uom"])

    def check_duplicates(self):
        conditions = """
            where item_code=%(item_code)s
            and price_list=%(price_list)s
            and min_qty=%(min_qty)s
            and uom=%(uom)s
            and price_list_rate=%(price_list_rate)s
            and valid_from = %(valid_from)s
            and valid_upto = %(valid_upto)s
            and packing_unit=%(packing_unit)s
        """
        
        if self.customer and not self.supplier:
            conditions += "and customer= %(customer)s"

        if self.supplier and not self.customer:
            conditions += "and supplier= %(supplier)s" 


        price_list_rate = frappe.db.sql("""
            SELECT price_list_rate
            FROM `tabItem Price`
              {conditions} """.format(conditions=conditions), self.as_dict())

        if price_list_rate :
            frappe.throw(_(
                "Item Price appears multiple times based on Price List, Supplier/Customer, Currency, Item, UOM, Qty and Dates."))

    def before_save(self):
        if self.selling:
            self.reference = self.customer
        if self.buying:
            self.reference = self.supplier