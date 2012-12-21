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

pscript.onload_Setup = function(wrapper) {
	wrapper.appframe = new wn.ui.AppFrame($(wrapper).find('.appframe-area'), 'Setup');
	wrapper.appframe.add_home_breadcrumb();
	wrapper.appframe.add_breadcrumb(wn.modules["Setup"].icon);
	
	erpnext.module_page.hide_links(wrapper);
	if(wn.boot.expires_on) {
		$(wrapper).find(".layout-main")
			.prepend("<div class='alert'>Your ERPNext account will expire on "
				+ wn.datetime.global_date_format(wn.boot.expires_on) + "</div>");
	}
}