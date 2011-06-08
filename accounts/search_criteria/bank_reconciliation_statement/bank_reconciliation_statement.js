report.customize_filters = function() {
  this.hide_all_filters();

  this.filter_fields_dict['Journal Voucher Detail'+FILTER_SEP +'Account'].df.filter_hide = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Clearance Date'].df.filter_hide = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df.filter_hide = 0;

  this.filter_fields_dict['Journal Voucher Detail'+FILTER_SEP +'Account'].df.in_first_page = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Clearance Date'].df.in_first_page = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df.in_first_page = 1;

  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df['report_default']=sys_defaults.company;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Clearance Date'].df['report_default'] = dateutil.obj_to_str(new Date());

  this.dt.set_no_limit(1);
}

this.mytabs.items['More Filters'].hide();