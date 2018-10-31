frappe.provide('erpnext.bankreconciliation');

frappe.views.bankreconciliationFactory = class bankreconciliationFactory extends frappe.views.Factory {
	show() {
		if (frappe.pages.bankreconciliation) {
			frappe.container.change_to('bankreconciliation');
		} else {
			this.make('bankreconciliation');
		}
	}
 	make(page_name) {
		const assets = [
			'/assets/js/bankreconciliation.min.js'
		];
 		frappe.require(assets, () => {
			erpnext.bankreconciliation.home = new erpnext.bankreconciliation.Home({
				parent: this.make_page(true, page_name)
			});
		});
	}
};

$(document).on('toolbar_setup', () => {
	$('#toolbar-user .navbar-reload').after(`
	<li>
		<a class="bankreconciliation-link" href="#bankreconciliation/home">${__("Bank Reconciliation")}</a>
	</li>
	`);
});