// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.POS = Class.extend({
	init: function(wrapper, frm) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.wrapper.html('<div class="container">\
			<div class="row" style="margin: -9px 0px 10px -30px; border-bottom: 1px solid #c7c7c7;">\
				<div class="party-area col-sm-3 col-xs-6"></div>\
				<div class="barcode-area col-sm-3 col-xs-6"></div>\
				<div class="search-area col-sm-3 col-xs-6"></div>\
				<div class="item-group-area col-sm-3 col-xs-6"></div>\
			</div>\
			<div class="row">\
				<div class="col-sm-6">\
					<div class="pos-bill">\
						<div class="item-cart">\
							<table class="table table-condensed table-hover" id="cart" style="table-layout: fixed;">\
								<thead>\
									<tr>\
										<th style="width: 40%">Item</th>\
										<th style="width: 9%"></th>\
										<th style="width: 17%; text-align: right;">Qty</th>\
										<th style="width: 9%"></th>\
										<th style="width: 25%; text-align: right;">Rate</th>\
									</tr>\
								</thead>\
								<tbody>\
								</tbody>\
							</table>\
						</div>\
						<br>\
						<div class="totals-area" style="margin-left: 40%;">\
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
							<div class="grand-total-area">\
								<table class="table table-condensed">\
									<tr>\
										<td style="vertical-align: middle;"><b>Grand Total</b></td>\
										<td style="text-align: right; font-size: 200%; \
											font-size: bold;" class="grand-total"></td>\
									</tr>\
								</table>\
							</div>\
						</div>\
					</div>\
					<br><br>\
					<div class="row">\
						<div class="col-sm-9">\
							<button class="btn btn-success btn-lg make-payment">\
								<i class="icon-money"></i> Make Payment</button>\
						</div>\
						<div class="col-sm-3">\
							<button class="btn btn-default btn-lg remove-items" style="display: none;">\
								<i class="icon-trash"></i> Del</button>\
						</div>\
					</div>\
					<br><br>\
				</div>\
				<div class="col-sm-6">\
					<div class="item-list-area">\
						<div class="col-sm-12">\
							<div class="row item-list"></div></div>\
					</div>\
				</div>\
			</div></div>');
		
		this.check_transaction_type();
		this.make();

		var me = this;
		$(this.frm.wrapper).on("refresh-fields", function() {
			me.refresh();
		});

		this.call_function("remove-items", function() {me.remove_selected_items();});
		this.call_function("make-payment", function() {me.make_payment();});
	},
	check_transaction_type: function() {
		var me = this;

		// Check whether the transaction is "Sales" or "Purchase"
		if (wn.meta.has_field(cur_frm.doc.doctype, "customer")) {
			this.set_transaction_defaults("Customer", "export");
		}
		else if (wn.meta.has_field(cur_frm.doc.doctype, "supplier")) {
			this.set_transaction_defaults("Supplier", "import");
		}
	},
	set_transaction_defaults: function(party, export_or_import) {
		var me = this;
		this.party = party;
		this.price_list = (party == "Customer" ? 
			this.frm.doc.selling_price_list : this.frm.doc.buying_price_list);
		this.price_list_field = (party == "Customer" ? "selling_price_list" : "buying_price_list");
		this.sales_or_purchase = (party == "Customer" ? "Sales" : "Purchase");
		this.net_total = "net_total_" + export_or_import;
		this.grand_total = "grand_total_" + export_or_import;
		this.amount = export_or_import + "_amount";
		this.rate = export_or_import + "_rate";
	},
	call_function: function(class_name, fn, event_name) {
		this.wrapper.find("." + class_name).on(event_name || "click", fn);
	},
	make: function() {
		this.make_party();
		this.make_item_group();
		this.make_search();
		this.make_barcode();
		this.make_item_list();
	},
	make_party: function() {
		var me = this;
		this.party_field = wn.ui.form.make_control({
			df: {
				"fieldtype": "Link",
				"options": this.party,
				"label": this.party,
				"fieldname": "pos_party",
				"placeholder": this.party
			},
			parent: this.wrapper.find(".party-area"),
			only_input: true,
		});
		this.party_field.make_input();
		this.party_field.$input.on("change", function() {
			if(!me.party_field.autocomplete_open)
				wn.model.set_value(me.frm.doctype, me.frm.docname, 
					me.party.toLowerCase(), this.value);
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
				"placeholder": "Item Group"
			},
			parent: this.wrapper.find(".item-group-area"),
			only_input: true,
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
				"fieldtype": "Data",
				"label": "Item",
				"fieldname": "pos_item",
				"placeholder": "Search Item"
			},
			parent: this.wrapper.find(".search-area"),
			only_input: true,
		});
		this.search.make_input();
		this.search.$input.on("keypress", function() {
			if(!me.search.autocomplete_open)
				if(me.item_timeout)
					clearTimeout(me.item_timeout);
				me.item_timeout = setTimeout(function() { me.make_item_list(); }, 1000);
		});
	},
	make_barcode: function() {
		var me = this;
		this.barcode = wn.ui.form.make_control({
			df: {
				"fieldtype": "Data",
				"label": "Barcode",
				"fieldname": "pos_barcode",
				"placeholder": "Barcode / Serial No"
			},
			parent: this.wrapper.find(".barcode-area"),
			only_input: true,
		});
		this.barcode.make_input();
		this.barcode.$input.on("keypress", function() {
			if(me.barcode_timeout)
				clearTimeout(me.barcode_timeout);
			me.barcode_timeout = setTimeout(function() { me.add_item_thru_barcode(); }, 1000);
		});
	},
	make_item_list: function() {
		var me = this;
		me.item_timeout = null;
		wn.call({
			method: 'accounts.doctype.sales_invoice.pos.get_items',
			args: {
				sales_or_purchase: this.sales_or_purchase,
				price_list: this.price_list,
				item_group: this.item_group.$input.val(),
				item: this.search.$input.val()
			},
			callback: function(r) {
				var $wrap = me.wrapper.find(".item-list");
				me.wrapper.find(".item-list").empty();
				if (r.message) {
					$.each(r.message, function(index, obj) {
						if (obj.image)
							image = '<img src="' + obj.image + '" class="img-responsive" \
									style="border:1px solid #eee; max-height: 140px;">';
						else
							image = '<div class="missing-image"><i class="icon-camera"></i></div>';

						$(repl('<div class="col-xs-3 pos-item" data-item_code="%(item_code)s">\
									<div style="height: 140px; overflow: hidden;">%(item_image)s</div>\
									<div class="small">%(item_code)s</div>\
									<div class="small">%(item_name)s</div>\
									<div class="small">%(item_price)s</div>\
								</div>', 
							{
								item_code: obj.name,
								item_price: format_currency(obj.ref_rate, obj.currency),
								item_name: obj.name===obj.item_name ? "" : obj.item_name,
								item_image: image
							})).appendTo($wrap);
					});
				}

				// if form is local then allow this function
				$(me.wrapper).find("div.pos-item").on("click", function() {
					if(me.frm.doc.docstatus==0) {
						if(!me.frm.doc[me.party.toLowerCase()] && ((me.frm.doctype == "Quotation" && 
								me.frm.doc.quotation_to == "Customer") 
								|| me.frm.doctype != "Quotation")) {
							msgprint("Please select " + me.party + " first.");
							return;
						}
						else
							me.add_to_cart($(this).attr("data-item_code"));
					}
				});
			}
		});
	},
	add_to_cart: function(item_code, serial_no) {
		var me = this;
		var caught = false;

		// get no_of_items
		var no_of_items = me.wrapper.find("#cart tbody tr").length;
		
		// check whether the item is already added
		if (no_of_items != 0) {
			$.each(wn.model.get_children(this.frm.doctype + " Item", this.frm.doc.name, 
				this.frm.cscript.fname,	this.frm.doctype), function(i, d) {
				if (d.item_code == item_code) {
					caught = true;
					if (serial_no)
						wn.model.set_value(d.doctype, d.name, "serial_no", d.serial_no + '\n' + serial_no);
					else
						wn.model.set_value(d.doctype, d.name, "qty", d.qty + 1);
				}
			});
		}
		
		// if item not found then add new item
		if (!caught)
			this.add_new_item_to_grid(item_code, serial_no);

		this.refresh();
		this.refresh_search_box();
	},
	add_new_item_to_grid: function(item_code, serial_no) {
		var me = this;

		var child = wn.model.add_child(me.frm.doc, this.frm.doctype + " Item", 
			this.frm.cscript.fname);
		child.item_code = item_code;

		if (serial_no)
			child.serial_no = serial_no;

		this.frm.script_manager.trigger("item_code", child.doctype, child.name);
	},
	refresh_search_box: function() {
		var me = this;

		// Clear Item Box and remake item list
		if (this.search.$input.val()) {
			this.search.set_input("");
			this.make_item_list();
		}
	},
	update_qty: function(item_code, qty) {
		var me = this;
		$.each(wn.model.get_children(this.frm.doctype + " Item", this.frm.doc.name, 
			this.frm.cscript.fname, this.frm.doctype), function(i, d) {
			if (d.item_code == item_code) {
				if (qty == 0) {
					wn.model.clear_doc(d.doctype, d.name);
					me.refresh_grid();
				} else {
					wn.model.set_value(d.doctype, d.name, "qty", qty);
				}
			}
		});
		this.refresh();
	},
	refresh: function() {
		var me = this;

		this.refresh_item_list();
		this.party_field.set_input(this.frm.doc[this.party.toLowerCase()]);
		this.barcode.set_input("");

		this.show_items_in_item_cart();
		this.show_taxes();
		this.set_totals();

		// if form is local then only run all these functions
		if (this.frm.doc.docstatus===0) {
			this.call_when_local();
		}

		this.disable_text_box_and_button();
		this.hide_payment_button();

		// If quotation to is not Customer then remove party
		if (this.frm.doctype == "Quotation") {
			this.party_field.$wrapper.remove();
			if (this.frm.doc.quotation_to == "Customer")
				this.make_party();
		}
	},
	refresh_item_list: function() {
		var me = this;
		// refresh item list on change of price list
		if (this.frm.doc[this.price_list_field] != this.price_list) {
			this.price_list = this.frm.doc[this.price_list_field];
			this.make_item_list();
		}
	},
	show_items_in_item_cart: function() {
		var me = this;
		var $items = this.wrapper.find("#cart tbody").empty();

		$.each(wn.model.get_children(this.frm.doctype + " Item", this.frm.doc.name, 
			this.frm.cscript.fname, this.frm.doctype), function(i, d) {

			$(repl('<tr id="%(item_code)s" data-selected="false">\
					<td>%(item_code)s%(item_name)s</td>\
					<td style="vertical-align:middle;" align="right">\
						<div class="decrease-qty" style="cursor:pointer;">\
							<i class="icon-minus-sign icon-large text-danger"></i>\
						</div>\
					</td>\
					<td style="vertical-align:middle;"><input type="text" value="%(qty)s" \
						class="form-control qty" style="text-align: right;"></td>\
					<td style="vertical-align:middle;cursor:pointer;">\
						<div class="increase-qty" style="cursor:pointer;">\
							<i class="icon-plus-sign icon-large text-success"></i>\
						</div>\
					</td>\
					<td style="text-align: right;"><b>%(amount)s</b><br>%(rate)s</td>\
				</tr>',
				{
					item_code: d.item_code,
					item_name: d.item_name===d.item_code ? "" : ("<br>" + d.item_name),
					qty: d.qty,
					rate: format_currency(d[me.rate], me.frm.doc.currency),
					amount: format_currency(d[me.amount], me.frm.doc.currency)
				}
			)).appendTo($items);
		});

		this.wrapper.find("input.qty").on("focus", function() {
			$(this).select();
		});
	},
	show_taxes: function() {
		var me = this;
		var taxes = wn.model.get_children(this.sales_or_purchase + " Taxes and Charges", 
			this.frm.doc.name, this.frm.cscript.other_fname, this.frm.doctype);
		$(this.wrapper).find(".tax-table")
			.toggle((taxes && taxes.length) ? true : false)
			.find("tbody").empty();
		
		$.each(taxes, function(i, d) {
			if (d.tax_amount) {
				$(repl('<tr>\
					<td>%(description)s %(rate)s</td>\
					<td style="text-align: right;">%(tax_amount)s</td>\
				<tr>', {
					description: d.description,
					rate: ((d.charge_type == "Actual") ? '' : ("(" + d.rate + "%)")),
					tax_amount: format_currency(flt(d.tax_amount)/flt(me.frm.doc.conversion_rate), 
						me.frm.doc.currency)
				})).appendTo(".tax-table tbody");
			}
		});
	},
	set_totals: function() {
		var me = this;
		this.wrapper.find(".net-total").text(format_currency(this.frm.doc[this.net_total], 
			me.frm.doc.currency));
		this.wrapper.find(".grand-total").text(format_currency(this.frm.doc[this.grand_total], 
			me.frm.doc.currency));
	},
	call_when_local: function() {
		var me = this;

		// append quantity to the respective item after change from input box
		$(this.wrapper).find("input.qty").on("change", function() {
			var item_code = $(this).closest("tr").attr("id");
			me.update_qty(item_code, $(this).val());
		});

		// increase/decrease qty on plus/minus button
		$(this.wrapper).find(".increase-qty, .decrease-qty").on("click", function() {
			var tr = $(this).closest("tr");
			me.increase_decrease_qty(tr, $(this).attr("class"));
		});

		// on td click toggle the highlighting of row
		$(this.wrapper).find("#cart tbody tr td").on("click", function() {
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
		this.barcode.$input.focus();
	},
	increase_decrease_qty: function(tr, operation) {
		var item_code = tr.attr("id");
		var item_qty = cint(tr.find("input.qty").val());

		if (operation == "increase-qty")
			this.update_qty(item_code, item_qty + 1);
		else if (operation == "decrease-qty" && item_qty != 1)
			this.update_qty(item_code, item_qty - 1);
	},
	disable_text_box_and_button: function() {
		var me = this;
		// if form is submitted & cancelled then disable all input box & buttons
		if (this.frm.doc.docstatus>=1) {
			$(this.wrapper).find('input, button').each(function () {
				$(this).prop('disabled', true);
			});
			$(this.wrapper).find(".remove-items").hide();
			$(this.wrapper).find(".make-payment").hide();
		}
		else {
			$(this.wrapper).find('input, button').each(function () {
				$(this).prop('disabled', false);
			});
			$(this.wrapper).find(".make-payment").show();
		}
	},
	hide_payment_button: function() {
		var me = this;
		// Show Make Payment button only in Sales Invoice
		if (this.frm.doctype != "Sales Invoice")
			$(this.wrapper).find(".make-payment").hide();
	},
	refresh_delete_btn: function() {
		$(this.wrapper).find(".remove-items").toggle($(".item-cart .warning").length ? true : false);
	},
	add_item_thru_barcode: function() {
		var me = this;
		me.barcode_timeout = null;
		wn.call({
			method: 'accounts.doctype.sales_invoice.pos.get_item_code',
			args: {barcode_serial_no: this.barcode.$input.val()},
			callback: function(r) {
				if (r.message) {
					if (r.message[1] == "serial_no")
						me.add_to_cart(r.message[0][0].item_code, r.message[0][0].name);
					else
						me.add_to_cart(r.message[0][0].name);
				}
				else
					msgprint(wn._("Invalid Barcode"));

				me.refresh();
			}
		});
	},
	remove_selected_items: function() {
		var me = this;
		var selected_items = [];
		var no_of_items = $(this.wrapper).find("#cart tbody tr").length;
		for(var x=0; x<=no_of_items - 1; x++) {
			var row = $(this.wrapper).find("#cart tbody tr:eq(" + x + ")");
			if(row.attr("data-selected") == "true") {
				selected_items.push(row.attr("id"));
			}
		}

		var child = wn.model.get_children(this.frm.doctype + " Item", this.frm.doc.name, 
			this.frm.cscript.fname, this.frm.doctype);

		$.each(child, function(i, d) {
			for (var i in selected_items) {
				if (d.item_code == selected_items[i]) {
					wn.model.clear_doc(d.doctype, d.name);
				}
			}
		});

		this.refresh_grid();
	},
	refresh_grid: function() {
		this.frm.dirty();
		this.frm.fields_dict[this.frm.cscript.fname].grid.refresh();
		this.frm.script_manager.trigger("calculate_taxes_and_totals");
		this.refresh();
	},
	make_payment: function() {
		var me = this;
		var no_of_items = $(this.wrapper).find("#cart tbody tr").length;
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
					dialog.get_input("total_amount").prop("disabled", true);
					
					dialog.fields_dict.pay.input.onclick = function() {
						me.frm.set_value("mode_of_payment", dialog.get_values().mode_of_payment);
						me.frm.set_value("paid_amount", dialog.get_values().total_amount);
						me.frm.cscript.mode_of_payment(me.frm.doc);
						me.frm.save();
						dialog.hide();
						me.refresh();
					};
				}
			});
		}
	},
});