report.customize_filters = function() {

  this.filter_fields_dict['Enquiry'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Enquiry'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}