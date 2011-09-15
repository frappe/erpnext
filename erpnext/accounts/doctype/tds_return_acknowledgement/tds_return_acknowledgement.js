cur_frm.fields_dict['quarter'].get_query = function(doc, cdt, cdn) {
  if(doc.fiscal_year)
    return 'SELECT `tabPeriod`.name FROM `tabPeriod` WHERE `tabPeriod`.fiscal_year = "'+doc.fiscal_year+'" AND `tabPeriod`.period_type = "Quarter" AND `tabPeriod`.docstatus != 2 AND `tabPeriod`.name LIKE "%s" ORDER BY `tabPeriod`.start_date ASC LIMIT 50';
}
