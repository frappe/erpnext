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

cur_frm.cscript.refresh = function(doc) {
	if(!doc.__islocal && doc.published && !doc.email_sent) {
		cur_frm.add_custom_button('Email Subscribers', function() {
			$c_obj(make_doclist(doc.doctype, doc.name), 'send_emails', '', function(r) {
				cur_frm.refresh();
			});
		})
	}
}