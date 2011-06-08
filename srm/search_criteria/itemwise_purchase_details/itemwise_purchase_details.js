report.customize_filters = function() {
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'From PO Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Purchase Order'+FILTER_SEP +'To PO Date'].df['report_default'] = dateutil.obj_to_str(new Date());

}