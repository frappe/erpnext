// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

window.doc={{ doc.as_json() }};

$(document).ready(function() {
	new rfq();
	doc.supplier = "{{ doc.supplier }}"
	doc.currency = "{{ doc.currency }}"
	doc.number_format = "{{ doc.number_format }}"
	doc.buying_price_list = "{{ doc.buying_price_list }}"
});

rfq = class rfq {
	constructor(){
		this.onfocus_select_all();
		this.change_qty();
		this.change_rate();
		this.terms();
		this.submit_rfq();
		this.navigate_quotations();
	}

	onfocus_select_all(){
		$("input").click(function(){
			$(this).select();
		})
	}

	change_qty(){
		var me = this;
		$('.rfq-items').on("change", ".rfq-qty", function(){
			me.idx = parseFloat($(this).attr('data-idx'));
			me.qty = parseFloat(flt($(this).val())) || 0;
			me.rate = parseFloat(flt($(repl('.rfq-rate[data-idx=%(idx)s]',{'idx': me.idx})).val()));
			me.update_qty_rate();
			$(this).val(format_number(me.qty, doc.number_format, 2));
		})
	}

	change_rate(){
		var me = this;
		$(".rfq-items").on("change", ".rfq-rate", function(){
			me.idx = parseFloat($(this).attr('data-idx'));
			me.rate = parseFloat(flt($(this).val())) || 0;
			me.qty = parseFloat(flt($(repl('.rfq-qty[data-idx=%(idx)s]',{'idx': me.idx})).val()));
			me.update_qty_rate();
			$(this).val(format_number(me.rate, doc.number_format, 2));
		})
	}

	terms(){
		$(".terms").on("change", ".terms-feedback", function(){
			doc.terms = $(this).val();
		})
	}

	update_qty_rate(){
		var me = this;
		doc.grand_total = 0.0;
		$.each(doc.items, function(idx, data){
			if(data.idx == me.idx){
				data.qty = me.qty;
				data.rate = me.rate;
				data.amount = (me.rate * me.qty) || 0.0;
				$(repl('.rfq-amount[data-idx=%(idx)s]',{'idx': me.idx})).text(format_number(data.amount, doc.number_format, 2));
			}

			doc.grand_total += flt(data.amount);
			$('.tax-grand-total').text(format_number(doc.grand_total, doc.number_format, 2));
		})
	}

	submit_rfq(){
		$('.btn-sm').click(function(){
			frappe.freeze();
			frappe.call({
				type: "POST",
				method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.create_supplier_quotation",
				args: {
					doc: doc
				},
				btn: this,
				callback: function(r){
					frappe.unfreeze();
					if(r.message){
						$('.btn-sm').hide()
						window.location.href = "/supplier-quotations/" + encodeURIComponent(r.message);
					}
				}
			})
		})
	}

	navigate_quotations() {
		$('.quotations').click(function(){
			name = $(this).attr('idx')
			window.location.href = "/quotations/" + encodeURIComponent(name);
		})
	}
}
