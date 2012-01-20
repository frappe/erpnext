"""Global Defaults"""
import webnotes

keydict = {
	"fiscal_year": "current_fiscal_year",
    'company': 'default_company',
    'currency': 'default_currency',
    'price_list_name': 'default_price_list',
	'price_list_currency': 'default_price_list_currency',
    'item_group': 'default_item_group',
    'customer_group': 'default_customer_group',
    'cust_master_name': 'cust_master_name', 
    'supplier_type': 'default_supplier_type',
    'supp_master_name': 'supp_master_name', 
    'territory': 'default_territory',
    'stock_uom': 'default_stock_uom',
    'fraction_currency': 'default_currency_fraction',
    'valuation_method': 'default_valuation_method',
	'date_format': 'date_format',
	'currency_format':'default_currency_format',
	'account_url':'account_url'
}

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def get_bal(self,arg):
		"""get account balance (??)"""
		from webnotes.utils import fmt_money, flt
		bal = webnotes.conn.sql("select `tabAccount Balance`.balance,`tabAccount`.debit_or_credit from `tabAccount`,`tabAccount Balance` where `tabAccount Balance`.account=%s and `tabAccount Balance`.period=%s and `tabAccount Balance`.account=`tabAccount`.name ",(arg,self.doc.current_fiscal_year))
		if bal:
			return fmt_money(flt(bal[0][0])) + ' ' + bal[0][1]
	
	def validate(self):
		"""validate"""
		if not (self.doc.account_url and (self.doc.account_url.startswith('http://') \
			or self.doc.account_url.startswith('https://'))):
			webnotes.msgprint("Account URL must start with 'http://' or 'https://'", raise_exception=1)
	
	def on_update(self):
		"""update defaults"""
		self.validate()
		
		for key in keydict:
			webnotes.conn.set_default(key, self.doc.fields.get(keydict[key], ''))
			
		# update year start date and year end date from fiscal_year
		ysd = webnotes.conn.sql("""select year_start_date from `tabFiscal Year` 
			where name=%s""", self.doc.fiscal_year)
			
		ysd = ysd and ysd[0][0] or ''
		from webnotes.utils import get_first_day, get_last_day
		if ysd:
			webnotes.conn.set_default('year_start_date', ysd.strftime('%Y-%m-%d'))
			webnotes.conn.set_default('year_end_date', \
				get_last_day(get_first_day(ysd,0,11)).strftime('%Y-%m-%d'))
		
	def get_defaults(self):
		return webnotes.conn.get_defaults()