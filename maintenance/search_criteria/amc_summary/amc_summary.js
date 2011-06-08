report.customize_filters = function() {
  this.hide_all_filters();
  this.mytabs.items['Select Columns'].hide();
  this.mytabs.items['More Filters'].hide()
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Territory'].df.filter_hide = 0;
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Item Group'].df.filter_hide = 0;
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Territory'].df.in_first_page = 1;
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Item Group'].df.in_first_page = 1; 
}