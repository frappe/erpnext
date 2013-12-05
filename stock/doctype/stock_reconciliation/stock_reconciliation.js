// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.require("public/app/js/controllers/stock_controller.js");
wn.provide("erpnext.stock");

erpnext.stock.StockReconciliation = erpnext.stock.StockController.extend({
	onload: function() {
		this.set_default_expense_account();
	}, 
	
	set_default_expense_account: function() {
		var me = this;
		
		if (sys_defaults.auto_accounting_for_stock && !this.frm.doc.expense_account) {
			return this.frm.call({
				method: "accounts.utils.get_company_default",
				args: {
					"fieldname": "stock_adjustment_account", 
					"company": this.frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) me.frm.set_value("expense_account", r.message);
				}
			});
		}
	},
	
	setup: function() {
		var me = this;
		if (sys_defaults.auto_accounting_for_stock) {
			this.frm.add_fetch("company", "stock_adjustment_account", "expense_account");
			this.frm.add_fetch("company", "cost_center", "cost_center");
		
			this.frm.fields_dict["expense_account"].get_query = function() {
				return {
					"filters": {
						'company': me.frm.doc.company,
						'group_or_ledger': 'Ledger'
					}
				}
			}
		}
	},
	
	refresh: function() {
		if(this.frm.doc.docstatus===0) {
			this.show_download_template();
			this.show_upload();
			if(this.frm.doc.reconciliation_json) {
				this.frm.set_intro(wn._("You can submit this Stock Reconciliation."));
			} else {
				this.frm.set_intro(wn._("Download the Template, fill appropriate data and \
					attach the modified file."));
			}
		} else if(this.frm.doc.docstatus == 1) {
			this.frm.set_intro(wn._("Cancelling this Stock Reconciliation will nullify its effect."));
			this.show_stock_ledger();
			this.show_general_ledger();
		} else {
			this.frm.set_intro("");
		}
		this.show_reconciliation_data();
		this.show_download_reconciliation_data();
	},
	
	show_download_template: function() {
		var me = this;
		this.frm.add_custom_button(wn._("Download Template"), function() {
			this.title = wn._("Stock Reconcilation Template");
			wn.tools.downloadify([[wn._("Stock Reconciliation")],
				["----"],
				[wn._("Stock Reconciliation can be used to update the stock on a particular date, ")
					+ wn._("usually as per physical inventory.")],
				[wn._("When submitted, the system creates difference entries ")
					+ wn._("to set the given stock and valuation on this date.")],
				[wn._("It can also be used to create opening stock entries and to fix stock value.")],
				["----"],
				[wn._("Notes:")],
				[wn._("Item Code and Warehouse should already exist.")],
				[wn._("You can update either Quantity or Valuation Rate or both.")],
				[wn._("If no change in either Quantity or Valuation Rate, leave the cell blank.")],
				["----"],
				["Item Code", "Warehouse", "Quantity", "Valuation Rate"]], null, this);
			return false;
		}, "icon-download");
	},
	
	show_upload: function() {
		var me = this;
		var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty();
		
		// upload
		wn.upload.make({
			parent: $wrapper,
			args: {
				method: 'stock.doctype.stock_reconciliation.stock_reconciliation.upload'
			},
			sample_url: "e.g. http://example.com/somefile.csv",
			callback: function(fid, filename, r) {
				me.frm.set_value("reconciliation_json", JSON.stringify(r.message));
				me.show_reconciliation_data();
				me.frm.save();
			}
		});

		// rename button
		$wrapper.find('form input[type="submit"]')
			.attr('value', 'Upload')

	},
	
	show_download_reconciliation_data: function() {
		var me = this;
		if(this.frm.doc.reconciliation_json) {
			this.frm.add_custom_button(wn._("Download Reconcilation Data"), function() {
				this.title = wn._("Stock Reconcilation Data");
				wn.tools.downloadify(JSON.parse(me.frm.doc.reconciliation_json), null, this);
				return false;
			}, "icon-download");
		}
	},
	
	show_reconciliation_data: function() {
		var $wrapper = $(cur_frm.fields_dict.reconciliation_html.wrapper).empty();
		if(this.frm.doc.reconciliation_json) {
			var reconciliation_data = JSON.parse(this.frm.doc.reconciliation_json);

			var _make = function(data, header) {
				var result = "";
				
				var _render = header
					? function(col) { return "<th>" + col + "</th>"; }
					: function(col) { return "<td>" + col + "</td>"; };
				
				$.each(data, function(i, row) {
					result += "<tr>"
						+ $.map(row, _render).join("")
						+ "</tr>";
				});
				return result;
			};
			
			var $reconciliation_table = $("<div style='overflow-x: auto;'>\
					<table class='table table-striped table-bordered'>\
					<thead>" + _make([reconciliation_data[0]], true) + "</thead>\
					<tbody>" + _make(reconciliation_data.splice(1)) + "</tbody>\
					</table>\
				</div>").appendTo($wrapper);
		}
	},
});

cur_frm.cscript = new erpnext.stock.StockReconciliation({frm: cur_frm});