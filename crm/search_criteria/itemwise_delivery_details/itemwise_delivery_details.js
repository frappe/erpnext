report.customize_filters = function() {
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'From Voucher Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'To Voucher Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Delivery Note'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());

}