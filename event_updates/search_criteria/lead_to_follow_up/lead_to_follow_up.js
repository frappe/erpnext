report.customize_filters = function() {
  this.filter_fields_dict['Lead'+FILTER_SEP +'Status'].df.filter_hide = 1;
  this.filter_fields_dict['Lead'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}
  