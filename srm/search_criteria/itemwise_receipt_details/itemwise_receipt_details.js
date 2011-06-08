report.customize_filters = function() {
  this.filter_fields_dict['Purchase Receipt'+FILTER_SEP +'From Transaction Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Purchase Receipt'+FILTER_SEP +'To Transaction Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Purchase Receipt'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Purchase Receipt'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Purchase Receipt'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Purchase Receipt'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;

}