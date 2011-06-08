report.customize_filters = function() {
  this.hide_all_filters();
  
  this.add_filter({fieldname:'main_acc_head', label:'Main Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
  this.add_filter({fieldname:'edu_cess_acc_head', label:'Edu Cess Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
  this.add_filter({fieldname:'sh_edu_cess_acc_head', label:'S.H.Edu Cess Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
  
  // un-hide fields 
  //this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company', ignore : 1, parent:'Journal Voucher Detail'});
  //this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', ignore : 1, parent:'Journal Voucher Detail'});
  //this.add_filter({fieldname:'posting_date', label:'Posting Date', fieldtype:'Date', ignore : 1, parent:'Journal Voucher Detail'});
  
  

  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;
  
  // set defaults
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;

  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());

  //this.large_report = 1;
}