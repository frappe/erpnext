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


//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.__islocal) {
		set_field_options('price_help', ''); return;
	}
	if(!doc.file_list) {
		set_field_options('price_help', '<div class="help_box">To upload a price list, please attach a (.csv) file with 3 columns - <b>Item Code, Price and Currency</b> (no headings necessary). See attachments box in the right column</div>')
	} else {
		set_field_options('price_help', '<div class="help_box">To update prices from the attachment, please click on "Update Prices"</div>')
	}
}

cur_frm.cscript.clear_prices = function(doc, cdt, cdn) {
	if(confirm("This action will clear all rates for '"+ doc.name +"' from the Item Master and cannot be un-done. Are you sure you want to continue?")) {
		$c_obj(make_doclist(doc.doctype, doc.name), 'clear_prices', '', function(r, rt) { });
	}
}
