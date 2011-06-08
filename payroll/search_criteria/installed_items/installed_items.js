report.customize_filters = function() {
  this.filter_fields_dict['Serial No'+FILTER_SEP +'ID'].df.in_first_page = 1;
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Status'].df.filter_hide = 1;
}
this.mytabs.items['Select Columns'].hide();