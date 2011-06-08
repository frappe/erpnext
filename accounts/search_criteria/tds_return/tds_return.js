report.customize_filters = function() {
  this.hide_all_filters();

  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'TDS Category'].df.filter_hide = 0;

  this.add_filter({fieldname:'transaction_date', label:'Date', fieldtype:'Date', options:'',ignore : 1, parent:'TDS Payment'});  

  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'From Date'].df['report_default']=sys_defaults.year_start_date;
  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'To Date'].df['report_default']=dateutil.obj_to_str(new Date());
  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'Company'].df['report_default']=sys_defaults.company;

  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'From Date'].df.in_first_page = 1;
  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'To Date'].df.in_first_page = 1;
  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'Company'].df.in_first_page = 1;
  this.filter_fields_dict['TDS Payment'+FILTER_SEP +'TDS Category'].df.in_first_page = 1;

}

this.mytabs.items['Select Columns'].hide();
this.mytabs.items['More Filters'].hide();