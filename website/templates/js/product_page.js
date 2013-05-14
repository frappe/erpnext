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

$(document).ready(function() {
	$.ajax({
		method: "GET",
		url:"server.py",
		dataType: "json",
		data: {
			cmd: "website.helpers.product.get_product_info",
			item_code: "{{ name }}"
		},
		success: function(data) {
			if(data.message) {
				if(data.message.price) {
					$("<h4>").html(data.message.price.ref_currency + " " 
						+ data.message.price.ref_rate).appendTo(".item-price");
					$(".item-price").toggle(true);
				}
				if(data.message.stock==0) {
					$(".item-stock").html("<div class='help'>Not in stock</div>")
				}
				else if(data.message.stock==1) {
					$(".item-stock").html("<div style='color: green'>\
						<i class='icon-check'></i> Available (in stock)</div>")
				}
			}
		}
	})
})