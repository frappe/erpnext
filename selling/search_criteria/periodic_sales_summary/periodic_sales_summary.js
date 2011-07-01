report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'transaction_date', label:'Sales Order Date', fieldtype:'Date', parent:'Sales Order', in_first_page : 1,default:''});
  
  //this.filter_fields_dict['Sales Order'+FILTER_SEP +'Territory'].df.filter_hide = 0;
  //this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Order Date'].df.filter_hide = 0;
  //this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Order Date'].df.in_first_page = 1;
  
  this.filter_fields_dict['Sales Order Detail'+FILTER_SEP +'Item Code'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order Detail'+FILTER_SEP +'Item Code'].df.in_first_page = 1;

  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df.in_first_page = 1;

  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;

  //this.mytabs.items['Select Columns'].hide();
  //this.mytabs.items['More Filters'].hide();
}