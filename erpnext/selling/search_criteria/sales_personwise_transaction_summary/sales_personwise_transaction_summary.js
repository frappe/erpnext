report.customize_filters = function() {
  this.hide_all_filters();

  //Add filter
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Sales Order'+NEWLINE+'Delivery Note'+NEWLINE+'Sales Invoice', report_default:'Sales Order', ignore : 1,parent:'Sales Person', single_select :1, in_first_page:1});
  this.add_filter({fieldname:'transaction_date', label:'Date', fieldtype:'Date', options:'', ignore : 1,parent:'Sales Person', in_first_page:1});
  this.add_filter({fieldname:'voucher_id', label:'Voucher Id', fieldtype:'Data', options:'', ignore : 1,parent:'Sales Person', in_first_page:1});
  this.add_filter({fieldname:'territory', label:'Territory', fieldtype:'Link', options:'Territory', ignore : 1,parent:'Sales Person', in_first_page:1});
  this.add_filter({fieldname:'sales_person', label:'Sales Person', fieldtype:'Link', options:'Sales Person', ignore : 1,parent:'Sales Person', in_first_page:1});
}

// hide sections
this.mytabs.items['More Filters'].hide();
this.mytabs.items['Select Columns'].hide();

// Get query
report.get_query = function() {
  based_on = this.get_filter('Sales Person', 'Based On').get_value();
  from_date = this.get_filter('Sales Person', 'From Date').get_value();
  to_date = this.get_filter('Sales Person', 'To Date').get_value();
  vid = this.get_filter('Sales Person', 'Voucher Id').get_value();
  terr = this.get_filter('Sales Person', 'Territory').get_value();
  sp = this.get_filter('Sales Person', 'Sales Person').get_value();

  date_fld = 'transaction_date';
  if(based_on == 'Sales Invoice') {
    based_on = 'Receivable Voucher';
    date_fld = 'voucher_date';
  }

  sp_cond = '';
  if (from_date) sp_cond += ' AND t1.' + date_fld + '>= "' + from_date + '"';
  if (to_date) sp_cond += ' AND t1.' + date_fld + '<= "' + to_date + '"';
  if (vid) sp_cond += ' AND t1.name LIKE "%' + vid + '%"';
  if (terr) sp_cond += ' AND t1.territory = "' + terr + '"';
  if (sp) sp_cond += ' AND t2.sales_person = "' + sp + '"';

  return 'SELECT t1.`name`, t1.`customer_name`, t1.`territory`, t1.`' + date_fld + '`, t1.`net_total`, t1.`grand_total`, t2.`sales_person`, t2.`allocated_percentage`, t2.`allocated_amount` FROM `tab' + based_on + '` t1, `tabSales Team` t2 WHERE t1.docstatus=1 AND t2.`parenttype` = "' + based_on + '" AND t2.`parent` = t1.`name`' + sp_cond + ' ORDER BY t1.`name` DESC';
}

