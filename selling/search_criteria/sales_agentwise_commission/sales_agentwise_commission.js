report.customize_filters = function() {
  this.hide_all_filters();
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Partner'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Partner'].df.in_first_page = 1;
}


this.mytabs.items['Select Columns'].hide();
this.mytabs.items['More Filters'].hide();