report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'show_group_balance', label:'Show Group Balance', fieldtype:'Select', options:NEWLINE+'Yes'+NEWLINE+'No',ignore : 1, parent:'Account'});
  this.add_filter({fieldname:'level', label:'Level', fieldtype:'Data', default:3,ignore : 1, parent:'Account'});
  
  this.add_filter({fieldname:'from_date', label:'Date', fieldtype:'Date', parent:'Account'});

  
  this.filter_fields_dict['Account'+FILTER_SEP +'Company'].df.filter_hide = 0;
  //this.filter_fields_dict['Account'+FILTER_SEP +'From Date'].df.filter_hide = 0;
  //this.filter_fields_dict['Account'+FILTER_SEP +'To Date'].df.filter_hide = 0;

  //this.large_report = 1;
}

report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}