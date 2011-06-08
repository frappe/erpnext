report.customize_filters = function() {
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'ID'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'From Sales Order Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'To Sales Order Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Sales Order Detail'+FILTER_SEP +'Item Code'].df.in_first_page = 1;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Status'].df.filter_hide = 1;
}

//this.mytabs.items['Select Columns'].hide();
this.mytabs.items['More Filters'].hide();