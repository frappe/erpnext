report.customize_filters = function() {
  this.filter_fields_dict['Customer Issue'+FILTER_SEP +'Status'].df.in_first_page = 1;
  this.filter_fields_dict['Customer Issue'+FILTER_SEP +'Allocated To'].df.in_first_page = 1;
  this.filter_fields_dict['Customer Issue'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
}

this.mytabs.items['Select Columns'].hide()