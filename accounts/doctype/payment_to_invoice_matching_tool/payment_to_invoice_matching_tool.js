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

// Booking Entry Id
// --------------------

cur_frm.cscript.onload_post_render = function(doc) {
	$(cur_frm.get_field("reconcile").input).addClass("btn-info");
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.set_intro("");
	if(!doc.voucher_no) {
		cur_frm.set_intro("Select the Invoice against which you want to allocate payments.");
	} else {
		cur_frm.set_intro("Set allocated amount against each Payment Entry and click 'Allocate'.");
	}
}

cur_frm.fields_dict.voucher_no.get_query = function(doc) {
	if (!doc.account) msgprint("Please select Account first");
	else {
		return repl("select voucher_no, posting_date \
			from `tabGL Entry` where ifnull(is_cancelled, 'No') = 'No'\
			and account = '%(acc)s' \
			and voucher_type = '%(dt)s' \
			and voucher_no LIKE '%s' \
			ORDER BY posting_date DESC, voucher_no DESC LIMIT 50 \
		", {dt:doc.voucher_type, acc:doc.account});
	}
}

cur_frm.cscript.voucher_no  =function(doc, cdt, cdn) {
	get_server_fields('get_voucher_details', '', '', doc, cdt, cdn, 1)
}

