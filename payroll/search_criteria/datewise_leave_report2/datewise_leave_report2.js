report.customize_filters = function() {
  this.add_filter({fieldname:'from_date', label:'From date', fieldtype:'date', options:'',ignore : 1, parent:'Leave Transaction'});
  this.add_filter({fieldname:'to_date', label:'To date', fieldtype:'date', options:'',ignore : 1, parent:'Leave Transaction'});
  this.filter_fields_dict['Leave Transaction'+FILTER_SEP +'From date'].df.in_first_page = 1;
  this.filter_fields_dict['Leave Transaction'+FILTER_SEP +'To date'].df.in_first_page = 1;
  this.filter_fields_dict['Leave Transaction'+FILTER_SEP +'From date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Leave Transaction'+FILTER_SEP +'To date'].df['report_default'] = dateutil.obj_to_str(new Date());
}