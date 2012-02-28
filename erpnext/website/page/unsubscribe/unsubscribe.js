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

pscript.onload_unsubscribe = function(wrapper) {
	var email = window.location.hash.split('/').splice(-1);
	$(wrapper).find('input[name="unsubscribe"]').val(email)
	
	$('#btn-unsubscribe').click(function() {
		var email = $(wrapper).find('input[name="unsubscribe"]').val();
		if(email) {
			var btn = this;
			wn.call({
				module:'website',
				page:'unsubscribe',
				method:'unsubscribe',
				args:email,
				btn: this,
				callback: function() {
					$(wrapper).find('input[name="unsubscribe"]').val('');
				}
			});
		}
	});
}