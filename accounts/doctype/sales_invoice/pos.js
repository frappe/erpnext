// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

erpnext.POS = Class.extend({
	init: function(wrapper, frm) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.wrapper.html('<div class="container">\
			<div class="row">\
				<div class="col-lg-4">\
					<div class="customer-area"></div>\
					<div class="button-area">\
						<div class="col-lg-6">\
							<a class="btn btn-danger col-lg-12 delete-items">\
							<i class="icon-trash icon-large"></i></a></div>\
						<div class="col-lg-6">\
							<a class="btn btn-success col-lg-12 make-payment">\
							<i class="icon-money icon-large"></i></a></div>\
					</div>\
					<div>&nbsp;</div>\
					<div class="item-cart">\
						<table class="table table-condensed">\
							<tr>\
								<th>Item</th>\
								<th>#</th>\
								<th>Rate</th>\
								<th>Amount</th>\
							</tr>\
						</table>\
						<div>\
							<table id="cart" class="table table-condensed table-hover">\
							</table>\
						</div>\
					</div>\
					<div>&nbsp;</div>\
					<div class="net-total-area" style="font-weight:bold;">\
						<div class="col-lg-6">Net Total</div>\
						<div class="col-lg-6 net-total">&nbsp;</div>\
					</div>\
					<div class="tax-area" style="font-weight:bold;">\
						<div class="col-lg-6">Tax</div>\
						<div class="col-lg-6 tax">&nbsp;</div>\
					</div>\
					<div class="grand-total-area" style="font-weight:bold;">\
						<div class="col-lg-6">Grand Total</div>\
						<div class="col-lg-6 grand-total">&nbsp;</div>\
					</div>\
				</div>\
				<div class="col-lg-8">\
					<div class="search-fields-area">\
						<div class="col-lg-4">\
							<div class="barcode-area"></div></div>\
						<div class="col-lg-4">\
							<div class="search-area"></div></div>\
						<div class="col-lg-4">\
							<div class="item-group-area"></div></div>\
					</div>\
					<div class="item-list-area">\
						<div class="col-lg-12">\
							<div class="row item-list"></div></div>\
					</div>\
				</div>\
			</div></div>');

		this.make();

		var me = this;
		$(this.frm.wrapper).on("refresh-fields", function() {
			me.refresh();
		});

		this.wrapper.find(".delete-items").on("click", function() {
			me.remove_selected_item();
		});

		this.wrapper.find(".make-payment").on("click", function() {
			me.make_payment();
		});
	},
	make: function() {
		this.make_customer();
		this.make_item_group();
		this.make_search();
		this.make_barcode();
		this.make_item_list();
	},
	make_customer: function() {
		var me = this;
		this.customer = wn.ui.form.make_control({
			df: {
				"fieldtype": "Link",
				"options": "Customer",
				"label": "Customer",
				"fieldname": "pos_customer"
			},
			parent: this.wrapper.find(".customer-area")
		});
		this.customer.make_input();
		this.customer.$input.on("change", function() {
			if(!me.customer.autocomplete_open)
				wn.model.set_value("Sales Invoice", me.frm.docname, "customer", this.value);
		});
	},
	make_item_group: function() {
		var me = this;
		this.item_group = wn.ui.form.make_control({
			df: {
				"fieldtype": "Link",
				"options": "Item Group",
				"label": "Item Group",
				"fieldname": "pos_item_group"
			},
			parent: this.wrapper.find(".item-group-area")
		});
		this.item_group.make_input();
		this.item_group.$input.on("change", function() {
			if(!me.item_group.autocomplete_open)
				me.make_item_list();
		});
	},
	make_search: function() {
		var me = this;
		this.search = wn.ui.form.make_control({
			df: {
				"fieldtype": "Link",
				"options": "Item",
				"label": "Item",
				"fieldname": "pos_item"
			},
			parent: this.wrapper.find(".search-area")
		});
		this.search.make_input();
		this.search.$input.on("change", function() {
			if(!me.search.autocomplete_open)
				me.make_item_list();
		});
	},
	make_barcode: function() {
		var me = this;
		this.barcode = wn.ui.form.make_control({
			df: {
				"fieldtype": "Data",
				"label": "Barcode",
				"fieldname": "pos_barcode"
			},
			parent: this.wrapper.find(".barcode-area")
		});
		this.barcode.make_input();
		this.barcode.$input.on("change", function() {
			me.add_item_thru_barcode();
		});
	},
	make_item_list: function() {
		var me = this;
		wn.call({
			method: 'accounts.doctype.sales_invoice.pos.get_items',
			args: {
				price_list: cur_frm.doc.selling_price_list,
				item_group: this.item_group.$input.val(),
				item: this.search.$input.val()
			},
			callback: function(r) {
				var $wrap = me.wrapper.find(".item-list");
				me.wrapper.find(".item-list").empty();
				$.each(r.message, function(index, obj) {
					if (obj.image)
						image = "<img src='" + obj.image + "' width='112px' height='125px'>";
					else
						image = "<div class='missing-image'><i class='icon-camera'></i></div>";

					$(repl('<div class="col-lg-3 item">\
							<a data-item_code="%(item_code)s">\
							<table>\
							<tr><td colspan="2">%(item_image)s</td></tr>\
							<tr><td>%(item_code)s</td>\
							<td rowspan="2">%(item_price)s</td></tr>\
							<tr><td>%(item_name)s</td>\
							</tr></table></a></div>', 
						{
							item_code: obj.name,
							item_price: format_currency(obj.ref_rate, obj.ref_currency),
							item_name: obj.item_name,
							item_image: image
						})).appendTo($wrap);
				});

				$("div.item").on("click", function() {
					me.add_to_cart($(this).find("a").attr("data-item_code"));
				});
			}
		});
	},
	add_to_cart: function(item_code) {
		var me = this;
		var caught = false;

		// get no_of_items
		no_of_items = me.wrapper.find("#cart tr").length;

		// check whether the item is already added
		if (no_of_items != 0) {
			$.each(wn.model.get_children("Sales Invoice Item", this.frm.doc.name, "entries", 
			"Sales Invoice"), function(i, d) {
				if (d.item_code == item_code)
					caught = true;
			});
		}
		
		// if duplicate row then append the qty
		if (caught) {
			me.update_qty(item_code, 1);
		}
		else {
			var child = wn.model.add_child(me.frm.doc, "Sales Invoice Item", "entries");
			child.item_code = item_code;
			me.frm.cscript.item_code(me.frm.doc, child.doctype, child.name);
			me.refresh();
		}
	},
	update_qty: function(item_code, qty) {
		var me = this;
		$.each(wn.model.get_children("Sales Invoice Item", this.frm.doc.name, "entries", 
		"Sales Invoice"), function(i, d) {
			if (d.item_code == item_code) {
				if (qty == 1)
					d.qty += 1;
				else
					d.qty = qty;

				me.frm.cscript.qty(me.frm.doc, d.doctype, d.name);
			}
		});
		me.refresh();
	},
	refresh: function() {
		var me = this;
		this.customer.set_input(this.frm.doc.customer);
		this.barcode.set_input("");

		// add items
		var $items = me.wrapper.find("#cart").empty();

		$.each(wn.model.get_children("Sales Invoice Item", this.frm.doc.name, "entries", 
		"Sales Invoice"), function(i, d) {
			$(repl('<tr id="%(item_code)s" data-selected="false">\
				<td>%(item_code)s <br> %(item_name)s</td>\
				<td><input type="text" value="%(qty)s" class="form-control qty"></td>\
				<td>%(rate)s</td>\
				<td>%(amount)s</td></tr>',
				{
					item_code: d.item_code,
					item_name: d.item_name,
					qty: d.qty,
					rate: format_currency(d.ref_rate, cur_frm.doc.price_list_currency),
					amount: format_currency(d.export_amount, cur_frm.doc.price_list_currency)
				}
			)).appendTo($items);
		});

		// set totals
		this.wrapper.find(".net-total").text(format_currency(this.frm.doc.net_total_export, 
			cur_frm.doc.price_list_currency));
		this.wrapper.find(".tax").text(format_currency(this.frm.doc.other_charges_total_export, 
			cur_frm.doc.price_list_currency));
		this.wrapper.find(".grand-total").text(format_currency(this.frm.doc.grand_total_export, 
			cur_frm.doc.price_list_currency));

		// append quantity to the respective item after change from input box
		$("input.qty").on("change", function() {
			var item_code = $(this).closest("tr")[0].id;
			me.update_qty(item_code, $(this).val());
		});

		// on td click highlight the respective row
		$("td").on("click", function() {
			var row = $(this).closest("tr");
			if (row.attr("data-selected") == "false") {
				row.attr("class", "warning");
				row.attr("data-selected", "true");
			}
			else {
				row.prop("class", null);
				row.attr("data-selected", "false");
			}
		});
	},
	add_item_thru_barcode: function() {
		var me = this;
		wn.call({
			method: 'accounts.doctype.sales_invoice.pos.get_item_from_barcode',
			args: {barcode: this.barcode.$input.val()},
			callback: function(r) {
				if (r.message) {
					me.add_to_cart(r.message[0].name);
					me.refresh();
				}
				else
					msgprint(wn._("Invalid Barcode"));
			}
		});
	},
	remove_selected_item: function() {
		var me = this;
		var selected_items = [];
		var no_of_items = $("#cart tr").length;
		for(var x=0; x<=no_of_items - 1; x++) {
			var row = $("#cart tr:eq(" + x + ")");
			if(row.attr("data-selected") == "true") {
				selected_items.push(row.attr("id"));
			}
		}

		if (!selected_items[0])
			msgprint(wn._("Please select any item to remove it"));
		
		var child = wn.model.get_children("Sales Invoice Item", this.frm.doc.name, "entries", 
		"Sales Invoice");
		$.each(child, function(i, d) {
			for (var i in selected_items) {
				if (d.item_code == selected_items[i]) {
					wn.model.clear_doc(d.doctype, d.name);
				}
			}
		});
		cur_frm.fields_dict["entries"].grid.refresh();
		me.refresh();
	},
	make_payment: function() {
		var me = this;
		var no_of_items = $("#cart tr").length;
		var mode_of_payment = [];
		
		if (no_of_items == 0)
			msgprint(wn._("Payment cannot be made for empty cart"));
		else {
			wn.call({
				method: 'accounts.doctype.sales_invoice.pos.get_mode_of_payment',
				callback: function(r) {
					for (x=0; x<=r.message.length - 1; x++) {
						mode_of_payment.push(r.message[x].name);
					}

					// show payment wizard
					var dialog = new wn.ui.Dialog({
						width: 400,
						title: 'Payment', 
						fields: [
							{fieldtype:'Data', fieldname:'total_amount', label:'Total Amount', read_only:1},
							{fieldtype:'Select', fieldname:'mode_of_payment', label:'Mode of Payment', 
								options:mode_of_payment.join('\n'), reqd: 1},
							{fieldtype:'Button', fieldname:'pay', label:'Pay'}
						]
					});
					dialog.set_values({
						"total_amount": $(".grand-total").text()
					});
					dialog.show();
					
					dialog.fields_dict.pay.input.onclick = function() {
						cur_frm.set_value("mode_of_payment", dialog.get_values().mode_of_payment);
						cur_frm.set_value("paid_amount", dialog.get_values().total_amount);
						cur_frm.save();
						dialog.hide();
						me.refresh();
					};
				}
			});
		}
	},
});