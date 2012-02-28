// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

report.customize_filters = function() {
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Posting Date'].df['report_default'] = sys_defaults.year_start_date;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Posting Date'].df['report_default'] = dateutil.obj_to_str(new Date());
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
  
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Voucher Type'].df.in_first_page = 0;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Clearance Date'].df.in_first_page = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Clearance Date'].df.in_first_page = 1;
  this.filter_fields_dict['Journal Voucher Detail'+FILTER_SEP +'Account'].df.in_first_page = 1;  		
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Company'].df.in_first_page = 1;  		
	
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'ID'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Owner'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Saved'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Submitted'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Cancelled'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher Detail'+FILTER_SEP +'Against Receivable'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'TDS Category'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher Detail'+FILTER_SEP +'Cost Center'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher Detail'+FILTER_SEP +'Against Payable'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Owner'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'TDS Applicable'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Is Opening'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Total Debit >='].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Total Debit <='].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Total Credit >='].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Total Credit <='].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'User Remark'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'From Voucher Date'].df.filter_hide = 1;
  this.filter_fields_dict['Journal Voucher'+FILTER_SEP +'To Voucher Date'].df.filter_hide = 1;
}

this.mytabs.items['More Filters'].hide()