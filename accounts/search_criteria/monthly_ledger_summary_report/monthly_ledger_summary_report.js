report.customize_filters = function() {
  flds = ['ID','Owner','Cost Center','From Posting Date', 'To Posting Date', 'Against Voucher','Voucher Type','Voucher No','Is Cancelled','Is Opening','Remarks', 'From Aging Date', 'To Aging Date', 'Company']
  for(i=0;i<flds.length;i++){
    this.filter_fields_dict['GL Entry'+FILTER_SEP +flds[i]].df.filter_hide = 1;
  }
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Fiscal Year'].df['report_default']=sys_defaults.fiscal_year;
  this.filter_fields_dict['GL Entry'+FILTER_SEP +'Fiscal Year'].df.in_first_page = 1;
}

this.mytabs.items['Select Columns'].hide();
this.mytabs.items['More Filters'].hide();