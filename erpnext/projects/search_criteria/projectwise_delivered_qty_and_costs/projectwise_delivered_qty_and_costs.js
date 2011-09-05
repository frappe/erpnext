report.customize_filters = function() {
  this.hide_all_filters();

  //this.add_filter({fieldname:'item_code', label:'Item Code', fieldtype:'Link', options:'Item',ignore : 1,parent:'Delivery Note Detail'});

  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Project Name'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;  
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Customer'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Customer Name'].df.filter_hide = 0;

  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Project Name'].df.in_first_page = 1;

  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}
