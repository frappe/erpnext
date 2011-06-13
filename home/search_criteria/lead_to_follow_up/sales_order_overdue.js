report.customize_filters = function() {
  this.hide_all_filters();
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Customer'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'ID'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Quotation No'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Partner'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'From Sales Order Date'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'To Sales Order Date'].df.filter_hide = 0;
}