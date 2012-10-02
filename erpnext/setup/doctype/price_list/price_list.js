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

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.__islocal) {
		cur_frm.set_intro("Save this list to begin.");
		return;
	}
	if (wn.boot.profile.can_create.indexOf(cdt) !== -1) {
		if(!doc.file_list) {
			cur_frm.set_intro('<p>1. Click on "Download Template" \
				to download the template of all Items.</p>'
			+'<p>2. Update prices and Currency.</p>'
			+'<p>3. Save it as a CSV (.csv) file.</p>'
			+'<p>4. Upload the file.</p>');
		
			cur_frm.add_custom_button('Download Template', function() {
				$c_obj_csv(cur_frm.get_doclist(), 'download_template');
			}, 'icon-download')
		
			cur_frm.add_custom_button('Upload Price List', function() {
				cur_frm.attachments.add_attachment();
			}, 'icon-upload');
		} else {
			cur_frm.set_intro('To update prices from the attachment, click on "Update Prices". \
				To reset prices, delete the attachment (in the sidebar) and upload again.');
		
			// Update Prices
			cur_frm.add_custom_button('Update Prices', function() {
				cur_frm.call_server('update_prices');
			}, 'icon-refresh');
		}
	}
}
