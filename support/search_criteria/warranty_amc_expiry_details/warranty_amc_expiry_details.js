//this.mytabs.items['Select Columns'].hide();

report.customize_filters = function() {
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Status'].df.in_first_page = 0;
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Customer'].df.in_first_page = 1;
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Customer Name'].df.in_first_page = 1;
  this.filter_fields_dict['Serial No'+FILTER_SEP +'Maintenance Status'].df.in_first_page = 1;

}