report.customize_filters = function() {

  //to hide all filters
  this.hide_all_filters();
  field_list=['Voucher Type', 'Voucher No', 'From Posting Date','To Posting Date','Account','Company', 'Remarks', 'Is Cancelled', 'Is Opening']
  for(var i=0;i<field_list.length;i++){
    this.filter_fields_dict['GL Entry'+FILTER_SEP +field_list[i]].df.filter_hide = 0;
  }

  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Account'].df.in_first_page = 1;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;

  this.filter_fields_dict['GL Entry'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
}

this.mytabs.tabs['Select Columns'].hide()

report.aftertableprint = function(t) {
  $yt(t,'*',2,{whiteSpace:'pre'});
   $yt(t,'*',3,{whiteSpace:'pre'});
}