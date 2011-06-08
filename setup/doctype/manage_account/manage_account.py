# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cint, cstr, get_defaults, set_default, fmt_money, get_last_day, get_first_day
from webnotes import session, form, is_testing, msgprint, errprint

sql = webnotes.conn.sql

	
# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self, d, dl):
    self.doc, self.doclist = d, dl

#---------------------------------------------------------------------------------------------------------------------------------------------  
  def get_bal(self,arg):
    bal = sql("select `tabAccount Balance`.balance,`tabAccount`.debit_or_credit from `tabAccount`,`tabAccount Balance` where `tabAccount Balance`.account=%s and `tabAccount Balance`.period=%s and `tabAccount Balance`.account=`tabAccount`.name ",(arg,self.doc.current_fiscal_year))
    if bal:
      return fmt_money(flt(bal[0][0])) + ' ' + bal[0][1]


# =========================================================================================================================================

  # Update Default
  # ---------------
  def set_system_default(self, defkey, defvalue):
    set_default(defkey, defvalue)

    if defkey == 'fiscal_year':
      ysd = sql("select year_start_date from `tabFiscal Year` where name=%s", defvalue)
      ysd = ysd and ysd[0][0] or ''
      if ysd:
        set_default('year_start_date', ysd.strftime('%Y-%m-%d'))
        set_default('year_end_date', get_last_day(get_first_day(ysd,0,11)).strftime('%Y-%m-%d'))


  # Update
  # --------
  def update_cp(self):
    def_list = [['fiscal_year',self.doc.current_fiscal_year],
                ['company',self.doc.default_company],
                ['currency',self.doc.default_currency],
                ['price_list_name',self.doc.default_price_list],
                ['item_group',self.doc.default_item_group],
                ['customer_group',self.doc.default_customer_group],
                ['cust_master_name',self.doc.cust_master_name], 
                ['supplier_type',self.doc.default_supplier_type],
                ['supp_master_name',self.doc.supp_master_name], 
                ['territory',self.doc.default_territory],
                ['stock_uom',self.doc.default_stock_uom],
                ['fraction_currency',self.doc.default_currency_fraction],
                ['valuation_method',self.doc.default_valuation_method]]

    for d in def_list:
      self.set_system_default(d[0],d[1])
    # Update Currency Format
	
    sql("update `tabSingles` set value = '%s' where field = 'currency_format' and doctype = 'Control Panel'" % self.doc.default_currency_format)
    sql("update `tabSingles` set value = '%s' where field = 'date_format' and doctype = 'Control Panel'" %self.doc.date_format)


    return get_defaults()

