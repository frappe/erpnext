frappe.provide("erpnext.stock");

erpnext.stock.PackingSlipController = class PackingSlipController extends erpnext.stock.StockController {
	setup() {
		this.setup_posting_date_time_check();
	}

	refresh() {
		erpnext.hide_company();
	}
};

extend_cscript(cur_frm.cscript, new erpnext.stock.PackingSlipController({frm: cur_frm}));
