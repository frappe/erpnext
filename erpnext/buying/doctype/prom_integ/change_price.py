import frappe
import json
from frappe.utils import comma_and
from decimal import Decimal

class Item():
      def __init__(self, sku, regular_price_id, regular_price) -> None:
            self.item_code = sku
            self.regular_price = float(regular_price)
            self.regular_price_id = regular_price_id
            self.website_item = None
            self.wholesale_price = None
            self.new_regular_price = None
            self.new_wholesale_price = []

            # True if can change without errors
            self.change = True
      
      def check_price_error(self):
            # Check if we can change price without errors for Prom
            if self.new_wholesale_price:
                  for i in self.new_wholesale_price:
                        if self.new_regular_price <= i['price']:
                              self.change = False 
            
                        
def fetch_new_price(old_price, change_type, value):
      # Returns new price depends on change type
      old_price = Decimal(old_price)
      value = Decimal(value)
      if change_type == 'Percent':
            new_price = old_price + (old_price * (value/100))
      else:
            new_price = old_price + value
      return new_price 


@frappe.whitelist()
def change_price(values):
      not_changed_items = []
      change_options = (
            'Change regular prices',
            'Change wholesale prices',
            'Change regular and wholesale prices')
      
      values = json.loads(values)
      main_filters = {'price_list': values['price_list_reference']}

      main_fields = [
            'name',
            'price_list_rate',
            'item_code',
            'item_code.brand',
            'item_code.item_group'
            ]

      price_item_list = frappe.db.get_list(
            "Item Price",
            fields=main_fields,
            filters=main_filters)
      

      # Group and brand filtering
      group = values.get('group')
      brand = values.get('brand')
      if group:
            price_item_list = [x for x in price_item_list if x['item_group'] == group]
      if brand:
            price_item_list = [x for x in price_item_list if x['brand'] == brand]
      
      # If list has no filtered items - stop function
      if not price_item_list:
            return 1

      item_list = []
      for item in price_item_list:
            cur_item = Item(
                  sku=item['item_code'],
                  regular_price_id=item['name'],
                  regular_price=item['price_list_rate'])

            website_item = frappe.db.get_list(
                  "Website Item",
                  fields=["name"],
                  filters={'item_code': item.item_code}
                  )
            if website_item:
                  cur_item.website_item = website_item[0]['name']
                  cur_item.wholesale_price = frappe.db.get_list(
                        "Wholesale prices",
                        fields=['name', 'price'],
                        filters={'parent': cur_item.website_item}
                        )
                  for price in cur_item.wholesale_price:
                        cur_item.new_wholesale_price.append({
                              'name': price['name'],
                              'price': fetch_new_price(price['price'], values['change_type'], values['value'])})
            item_list.append(cur_item)
                  
      # If user want to change regular prices
      if values.get('change_select') == change_options[0] or \
            values.get('change_select') == change_options[2]:
            for item in item_list:
                  item.new_regular_price = fetch_new_price(
                        item.regular_price,
                        values['change_type'],
                        values['value'])
      else:
            for item in item_list:
                  item.new_regular_price = item.regular_price
      
      # If user want to change wholesale prices
      if values.get('change_select') == change_options[1] or \
            values.get('change_select') == change_options[2]:
            for item in item_list:
                  if item.wholesale_price:
                        for price in item.wholesale_price:
                              item.new_wholesale_price.append({
                                    'name': price['name'],
                                    'price': fetch_new_price(price['price'], values['change_type'], values['value'])
                              })
      else:
            for item in item_list:
                  item.new_wholesale_price = item.wholesale_price
      
      for item in item_list:
            item.check_price_error()
            if item.change == False:
                  not_changed_items.append(item.website_item)
      
      if not_changed_items:
            # Print items that can not be changed
            text = "Changing can not be complete because of some items.\
                        After change their regular price will be less then wholesale.<br>Item(-s): "
            for i in not_changed_items:
                  text += '<a href="/app/Form/Website%20Item/{0}">{0}</a>'.format(i)
                  if i == not_changed_items[-1]:
                        text += '.'
                  else:
                        text += ', '
            frappe.msgprint(text)
      else:
            # Set new prices in Database
            for item in item_list:
                  if item.new_regular_price:
                        frappe.db.set_value('Item Price', item.regular_price_id, 'price_list_rate', item.new_regular_price)
                  if item.new_wholesale_price:
                        for j in item.new_wholesale_price:
                              frappe.db.set_value('Wholesale prices', j['name'], 'price', j['price'])
            return 0
