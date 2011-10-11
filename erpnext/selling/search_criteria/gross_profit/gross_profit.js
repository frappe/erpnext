report.customize_filters = function() {
  this.mytabs.items['Select Columns'].hide();
  this.mytabs.tabs['More Filters'].hide();
  this.hide_all_filters();
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'ID'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note Detail'+FILTER_SEP +'Item Code'].df.filter_hide = 0;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Project Name'].df.filter_hide = 0;

  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'ID'].df.in_first_page = 1;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Delivery Note Detail'+FILTER_SEP +'Item Code'].df.in_first_page = 1;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'Project Name'].df.in_first_page = 1;
}