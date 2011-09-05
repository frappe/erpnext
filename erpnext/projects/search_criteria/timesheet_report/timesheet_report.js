report.customize_filters = function() {
  this.filter_fields_dict['Timesheet Detail'+FILTER_SEP +'Project Name'].df.in_first_page = 1;
  this.filter_fields_dict['Timesheet Detail'+FILTER_SEP +'Task Id'].df.in_first_page = 1;
this.filter_fields_dict['Timesheet'+FILTER_SEP +'Timesheet by'].df.filter_hide = 1;
}

//this.mytabs.items['Select Columns'].hide()