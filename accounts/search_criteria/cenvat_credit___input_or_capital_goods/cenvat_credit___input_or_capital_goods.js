report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'report', label:'Report Type', fieldtype:'Select', options:NEWLINE + 'CENVAT CREDIT ACCOUNT - INPUTS (R.G.23 A - PART II)' + NEWLINE + 'CAPITAL GOODS - INPUTS (R.G. 23 C - PART II)', ignore : 1, parent:'Journal Voucher Detail'})
  this.add_filter({fieldname:'main_acc_head', label:'Main Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
  this.add_filter({fieldname:'add_acc_head', label:'Additional Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
  this.add_filter({fieldname:'cvd_acc_head', label:'CVD Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
  this.add_filter({fieldname:'edu_cess_acc_head', label:'Edu Cess Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
  this.add_filter({fieldname:'sh_edu_cess_acc_head', label:'S.H.Edu Cess Account Head', fieldtype:'Link', options:'Account', ignore : 1, parent:'Journal Voucher Detail'});
    

  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;
  
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df['report_default']=sys_defaults.company;

  //this.large_report = 1;
}