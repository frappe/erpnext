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
		
		if (wn.meta.has_field(cur_frm.doc.doctype, "customer")) {
			this.party = "Customer";
			this.price_list = this.frm.doc.selling_price_list;
			this.sales_or_purchase = "Sales";
		}
		else if (wn.meta.has_field(cur_frm.doc.doctype, "supplier")) {
			this.party = "Supplier";
			this.price_list = this.frm.doc.buying_price_list;
			this.sales_or_purchase = "Purchase";
		}
		
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
				"fieldtype": "Link",
				"options": "Item",
				"label": "Item",
				"fieldname": "pos_item",
				"placeholder": "Item"
			},
			parent: this.wrapper.find(".search-area"),
			only_input: true,
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
					if (serial_no) {
						d.serial_no += '\n' + serial_no;
						me.frm.script_manager.trigger("serial_no", d.doctype, d.name);
					}
					else {
						d.qty += 1;
						me.frm.script_manager.trigger("qty", d.doctype, d.name);
					}
				}
			});
		}
		
		// if item not found then add new item
		if (!caught) {
			var child = wn.model.add_child(me.frm.doc, this.frm.doctype + " Item", 
				this.frm.cscript.fname);
			child.item_code = item_code;

			if (serial_no)
				child.serial_no = serial_no;

			me.frm.script_manager.trigger("item_code", child.doctype, child.name);
		}
		me.refresh();
	},
	update_qty: function(item_code, qty) {
		var me = this;
		$.each(wn.model.get_children(this.frm.doctype + " Item", this.frm.doc.name, 
			this.frm.cscript.fname, this.frm.doctype), function(i, d) {
			if (d.item_code == item_code) {
				if (qty == 0)
					wn.model.clear_doc(d.doctype, d.name);
				else {
					d.qty = qty;
					me.frm.script_manager.trigger("qty", d.doctype, d.name);
				}
			}
		});
		me.refresh();
	},
	refresh: function() {
		var me = this;
		this.party_field.set_input(this.frm.doc[this.party.toLowerCase()]);
		this.barcode.set_input("");

		// add items
		var $items = me.wrapper.find("#cart tbody").empty();

		$.each(wn.model.get_children(this.frm.doctype + " Item", this.frm.doc.name, 
			this.frm.cscript.fname, this.frm.doctype), function(i, d) {

			if (me.sales_or_purchase == "Sales") {
				item_amount = d.export_amount;
				rate = d.export_rate;
			}
			else {
				item_amount = d.import_amount;
				rate = d.import_rate;
			}

			$(repl('<tr id="%(item_code)s" data-selected="false">\
					<td>%(item_code)s%(item_name)s</td>\
					<td><input type="text" value="%(qty)s" \
						class="form-control qty" style="text-align: right;"></td>\
					<td style="text-align: right;"><b>%(amount)s</b><br>%(rate)s</td>\
				</tr>',
				{
					item_code: d.item_code,
					item_name: d.item_name===d.item_code ? "" : ("<br>" + d.item_name),
					qty: d.qty,
					rate: format_currency(rate, me.frm.doc.currency),
					amount: format_currency(item_amount, me.frm.doc.currency)
				}
			)).appendTo($items);
		});

		// taxes
		var taxes = wn.model.get_children(this.sales_or_purchase + " Taxes and Charges", 
			this.frm.doc.name, this.frm.cscript.other_fname, this.frm.doctype);
		$(this.wrapper).find(".tax-table")
			.toggle((taxes && taxes.length) ? true : false)
			.find("tbody").empty();
		
		$.each(taxes, function(i, d) {
			$(repl('<tr>\
				<td>%(description)s (%(rate)s%)</td>\
				<td style="text-align: right;">%(tax_amount)s</td>\
			<tr>', {
				description: d.description,
				rate: d.rate,
				tax_amount: format_currency(flt(d.tax_amount)/flt(me.frm.doc.conversion_rate), 
					me.frm.doc.currency)
			})).appendTo(".tax-table tbody");
		});

		// set totals
		if (this.sales_or_purchase == "Sales") {
			this.wrapper.find(".net-total").text(format_currency(this.frm.doc.net_total_export, 
				me.frm.doc.currency));
			this.wrapper.find(".grand-total").text(format_currency(this.frm.doc.grand_total_export, 
				me.frm.doc.currency));
		}
		else {
			this.wrapper.find(".net-total").text(format_currency(this.frm.doc.net_total_import, 
				me.frm.doc.currency));
			this.wrapper.find(".grand-total").text(format_currency(this.frm.doc.grand_total_import, 
				me.frm.doc.currency));
		}

		// if form is local then only run all these functions
		if (this.frm.doc.docstatus===0) {
			$(this.wrapper).find("input.qty").on("focus", function() {
				$(this).select();
			});

			// append quantity to the respective item after change from input box
			$(this.wrapper).find("input.qty").on("change", function() {
				var item_code = $(this).closest("tr")[0].id;
				me.update_qty(item_code, $(this).val());
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
		}

		// if form is submitted & cancelled then disable all input box & buttons
		if (this.frm.doc.docstatus>=1) {
			$(this.wrapper).find('input, button').each(function () {
				$(this).prop('disabled', true);
			});
			$(this.wrapper).find(".delete-items").hide();
			$(this.wrapper).find(".make-payment").hide();
		}
		else {
			$(this.wrapper).find('input, button').each(function () {
				$(this).prop('disabled', false);
			});
			$(this.wrapper).find(".make-payment").show();
		}

		// Show Make Payment button only in Sales Invoice
		if (this.frm.doctype != "Sales Invoice")
			$(this.wrapper).find(".make-payment").hide();

		// If quotation to is not Customer then remove party
		if (this.frm.doctype == "Quotation") {
			this.party_field.$wrapper.remove();
			if (this.frm.doc.quotation_to == "Customer")
				this.make_party();
		}
	},
	refresh_delete_btn: function() {
		$(this.wrapper).find(".delete-items").toggle($(".item-cart .warning").length ? true : false);		
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
	remove_selected_item: function() {
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
		this.frm.fields_dict[this.frm.cscript.fname].grid.refresh();
		this.frm.script_manager.trigger("calculate_taxes_and_totals");
		me.refresh();
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
					me.barcode.$input.focus();
					
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