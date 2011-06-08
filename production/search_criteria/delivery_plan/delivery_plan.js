report.customize_filters = function() {

  //to hide all filters
  //this.hide_all_filters();

  // to disable a filter from query set 
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Status'].df.ignore = 1;

  // to unhide required filters
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Customer'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Customer Name'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order Detail'+FILTER_SEP +'From Confirmed Delivery Date'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order Detail'+FILTER_SEP +'To Confirmed Delivery Date'].df.filter_hide = 0;


  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}