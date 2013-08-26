// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

erpnext.POS = Class.extend({
	init: function(wrapper, frm) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.wrapper.html('<div class="container">\
			<div class="row">\
				<div class="customer-area col-sm-3 col-xs-6"></div>\
				<div class="barcode-area col-sm-3 col-xs-6"></div>\
				<div class="search-area col-sm-3 col-xs-6"></div>\
				<div class="item-group-area col-sm-3 col-xs-6"></div>\
			</div>\
			<div class="row">\
				<div class="col-sm-6">\
					<div class="pos-bill">\
						<div class="item-cart">\
							<table class="table table-condensed table-hover" id="cart"  style="table-layout: fixed;">\
								<thead>\
									<tr>\
										<th style="width: 50%">Item</th>\
										<th style="width: 25%; text-align: right;">Qty</th>\
										<th style="width: 25%; text-align: right;">Rate</th>\
									</tr>\
								</thead>\
								<tbody>\
								</tbody>\
							</table>\
						</div>\
						<br>\
						<div class="net-total-area" style="margin-left: 40%;">\
							<table class="table table-condensed">\
								<tr>\
									<td><b>Net Total</b></td>\
									<td style="text-align: right;" class="net-total"></td>\
								</tr>\
							</table>\
							<div class="tax-table" style="display: none;">\
								<table class="table table-condensed">\
									<thead>\
										<tr>\
											<th style="width: 60%">Taxes</th>\
											<th style="width: 40%; text-align: right;"></th>\
										</tr>\
									</thead>\
									<tbody>\
									</tbody>\
								</table>\
							</div>\
							<table class="table table-condensed">\
								<tr>\
									<td style="vertical-align: middle;"><b>Grand Total</b></td>\
									<td style="text-align: right; font-size: 200%; \
										font-size: bold;" class="grand-total"></td>\
								</tr>\
							</table>\
						</div>\
					</div>\
					<br><br>\
					<button class="btn btn-success btn-lg make-payment">\
					<i class="icon-money"></i> Make Payment</button>\
					<button class="btn btn-default btn-lg delete-items pull-right" style="display: none;">\
					<i class="icon-trash"></i> Del</button>\
					<br><br>\
				</div>\
				<div class="col-sm-6">\
					<div class="item-list-area">\
						<div class="col-sm-12">\
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
				"fieldname": "pos_customer",
				"placeholder": "Customer"
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
				"fieldname": "pos_item_group",
				"placeholder": "Filter by Item Group"
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
				"fieldname": "pos_item",
				"placeholder": "Select Item"
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
				"fieldname": "pos_barcode",
				"placeholder": "Select Barcode"
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
						image = "<img src='" + obj.image + "' class='img-responsive'>";
					else
						image = '<div class="missing-image"><i class="icon-camera"></i></div>';

					$(repl('<div class="col-xs-3 pos-item" data-item_code="%(item_code)s">\
								%(item_image)s\
								<div class="small">%(item_code)s</div>\
								<div class="small">%(item_name)s</div>\
								<div class="small">%(item_price)s</div>\
							</div>', 
						{
							item_code: obj.name,
							item_price: format_currency(obj.ref_rate, obj.ref_currency),
							item_name: obj.name===obj.item_name ? "" : obj.item_name,
							item_image: image
						})).appendTo($wrap);
				});

				$("div.pos-item").on("click", function() {
					if(!cur_frm.doc.customer) {
						msgprint("Please select customer first.");
						return;
					}
					me.add_to_cart($(this).attr("data-item_code"));
				});
			}
		});
	},
	add_to_cart: function(item_code) {
		var me = this;
		var caught = false;

		// get no_of_items
		no_of_items = me.wrapper.find("#cart tbody").length;

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
			//me.refresh();
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
		var $items = me.wrapper.find("#cart tbody").empty();

		$.each(wn.model.get_children("Sales Invoice Item", this.frm.doc.name, "entries", 
			"Sales Invoice"), function(i, d) {
			$(repl('<tr id="%(item_code)s" data-selected="false">\
					<td>%(item_code)s%(item_name)s</td>\
					<td><input type="text" value="%(qty)s" \
						class="form-control qty" style="text-align: right;"></td>\
					<td style="text-align: right;">%(rate)s<br><b>%(amount)s</b></td>\
				</tr>',
				{
					item_code: d.item_code,
					item_name: d.item_name===d.item_code ? "" : ("<br>" + d.item_name),
					qty: d.qty,
					rate: format_currency(d.ref_rate, cur_frm.doc.price_list_currency),
					amount: format_currency(d.export_amount, cur_frm.doc.price_list_currency)
				}
			)).appendTo($items);
		});

		// taxes
		var taxes = wn.model.get_children("Sales Taxes and Charges", this.frm.doc.name, "other_charges", 
			"Sales Invoice");
		$(".tax-table")
			.toggle((taxes && taxes.length) ? true : false)
			.find("tbody").empty();
		
		$.each(taxes, function(i, d) {
			$(repl('<tr>\
				<td>%(description)s</td>\
				<td style="text-align: right;">%(tax_amount)s</td>\
			<tr>', {
				description: d.description,
				tax_amount: format_currency(d.tax_amount, me.frm.doc.price_list_currency)
			})).appendTo(".tax-table tbody");
		});

		// set totals
		this.wrapper.find(".net-total").text(format_currency(this.frm.doc.net_total_export, 
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
			me.refresh_delete_btn();
			
		});
		
		me.refresh_delete_btn();
	},
	refresh_delete_btn: function() {
		$(".delete-items").toggle($(".item-cart .warning").length ? true : false);		
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
		var no_of_items = $("#cart tbody tr").length;
		for(var x=0; x<=no_of_items - 1; x++) {
			var row = $("#cart tbody tr:eq(" + x + ")");
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
		var no_of_items = $("#cart tbody tr").length;
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
					
					dialog.get_input("total_amount").attr("disabled", "disabled");
					
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