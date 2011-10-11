report.customize_filters = function() {
  this.hide_all_filters();
  filter_list = ['From Voucher Date', 'To Voucher Date', 'Debit To', 'From Posting Date', 'To Posting Date']
  for(var i=0;i<filter_list.length;i++)
    this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +filter_list[i]].df.filter_hide = 0;

  this.filter_fields_dict['RV Detail'+FILTER_SEP +'Item'].df.filter_hide = 0;
  this.filter_fields_dict['RV Detail'+FILTER_SEP +'Item Group'].df.filter_hide = 0;
  this.filter_fields_dict['RV Detail'+FILTER_SEP +'Brand Name'].df.filter_hide = 0;
  this.filter_fields_dict['RV Detail'+FILTER_SEP +'Cost Center'].df.filter_hide = 0;

  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['RV Detail'+FILTER_SEP +'Item'].df.in_first_page = 1;

  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Company'].df['report_default']=sys_defaults.company
}
