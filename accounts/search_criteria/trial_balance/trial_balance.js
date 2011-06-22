report.customize_filters = function() {
  this.hide_all_filters();

  this.add_filter({fieldname:'show_group_balance', label:'Show Group Balance', fieldtype:'Select', options:'Yes'+NEWLINE+'No',ignore : 1, parent:'Account', 'report_default':'No','in_first_page':1});
  this.add_filter({fieldname:'transaction_date', label:'Date', fieldtype:'Date', options:'',ignore : 1, parent:'Account', 'in_first_page':1});

  this.filter_fields_dict['Account'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Account'+FILTER_SEP +'From Date'].df.filter_hide = 0;
  this.filter_fields_dict['Account'+FILTER_SEP +'To Date'].df.filter_hide = 0;

  this.filter_fields_dict['Account'+FILTER_SEP +'From Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Account'+FILTER_SEP +'To Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Account'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;

  this.filter_fields_dict['Account'+FILTER_SEP +'From Date'].df.in_first_page = 1;
  this.filter_fields_dict['Account'+FILTER_SEP +'To Date'].df.in_first_page = 1;
  this.filter_fields_dict['Account'+FILTER_SEP +'Company'].df.in_first_page = 1;

  this.dt.set_no_limit(1);
}

report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}
if(window.location.href.search('/v170/') != -1) {
  this.mytabs.items['More Filters'].hide();
  this.mytabs.items['Select Columns'].hide();
} else {
  $dh(this.mytabs.tabs['More Filters']);
  $dh(this.mytabs.tabs['Select Columns']);
}
