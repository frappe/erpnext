report.customize_filters = function() {
  this.filter_fields_dict['Employee'+FILTER_SEP +'From Date of Birth'].df.in_first_page = 1;
  this.filter_fields_dict['Employee'+FILTER_SEP +'To Date of Birth'].df.in_first_page = 1;
  this.filter_fields_dict['Employee'+FILTER_SEP +'Month of Birth'].df.in_first_page = 1;
  this.filter_fields_dict['Employee'+FILTER_SEP +'Department'].df.in_first_page = 1;
}