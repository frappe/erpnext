# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
from webnotes.utils import comma_and
from webnotes.model.controller import DocListController

class ShoppingCartSetupError(webnotes.ValidationError): pass

class DocType(DocListController):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		if self.doc.enabled:
			self.validate_overlapping_territories("shopping_cart_price_lists", "price_list")
			self.validate_overlapping_territories("shopping_cart_taxes_and_charges_masters", 
				"sales_taxes_and_charges_master")
			self.validate_shipping_rules()
			self.validate_exchange_rates_exist()
	
	def validate_overlapping_territories(self, parentfield, fieldname):
		names = [doc.fields(fieldname) for doc in self.doclist.get({"parentfield": parentfield})]
		doctype = self.meta.get_field(parentfield).options
		parenttype = self.meta.get_field(fieldname, parentfield=parentfield).options
		
		if not names:
			msgprint(_("Please specify at least one") + " " + _(doctype),
				raise_exception=ShoppingCartSetupError)
		
		territory_name = webnotes.conn.sql("""select territory, parent from `tabFor Territory`
			where parenttype=%s and parent in (%s)""" % ("%s", ", ".join(["%s"]*names)), 
			tuple([parenttype] + names))
		
		territory_name_map = {}
		for territory, name in territory_name:
			territory_name_map.setdefault(territory, []).append(name)
			
		for territory, names in territory_name_map.items():
			if len(names) > 1:
				msgprint(_("Error for") + " " + _(doctype) + ": " + comma_and(names) +
					" " + _("have a common territory") + ": " + territory,
					raise_exception=ShoppingCartSetupError)
					
	def validate_shipping_rules(self):
		pass
					
	def validate_exchange_rates_exist(self):
		"""check if exchange rates exist for all Price List currencies (to company's currency)"""
		company_currency = webnotes.conn.get_value("Company", self.doc.company, "default_currency")
		if not company_currency:
			msgprint(_("Please specify currency in Company") + ": " + self.doc.company,
				raise_exception=ShoppingCartSetupError)
		
		price_list_currency_map = webnotes.conn.get_values("Price List", 
			[d.price_list for d in self.doclist.get({"parentfield": "shopping_cart_price_lists"})],
			"currency")
		
		expected_to_exist = [currency + "-" + company_currency 
			for currency in price_list_currency_map.values()
			if currency != company_currency]

		exists = webnotes.conn.sql_list("""select name from `tabCurrency Exchange`
			where name in (%s)""" % (", ".join(["%s"]*len(expected_to_exist)),),
			tuple(expected_to_exist))
		
		missing = list(set(expected_to_exist).difference(exists))
		
		if missing:
			msgprint(_("Missing Currency Exchange Rates for" + ": " + comma_and(missing)),
				raise_exception=ShoppingCartSetupError)
		
		