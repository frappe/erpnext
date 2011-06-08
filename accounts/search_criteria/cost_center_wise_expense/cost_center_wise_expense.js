report.customize_filters = function() {
  this.hide_all_filters();

  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Cost Center'].df.filter_hide = 0;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Account'].df.filter_hide = 0;

  this.filter_fields_dict['GL Entry'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Account'].df.in_first_page = 1;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Cost Center'].df.in_first_page = 1;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Company'].df.in_first_page = 1;

  
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;

}
this.mytabs.items['Select Columns'].hide();
this.mytabs.items['More Filters'].hide();