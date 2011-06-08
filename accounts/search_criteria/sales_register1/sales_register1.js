report.customize_filters = function() {
 
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'ID'].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Owner'].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Saved'].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Submitted'].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Cancelled'].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Grand Total >='].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Grand Total <='].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Sales Partner'].df.filter_hide = 1;
  this.filter_fields_dict['Receivable Voucher'+FILTER_SEP +'Is Opening'].df.filter_hide = 1;
}
