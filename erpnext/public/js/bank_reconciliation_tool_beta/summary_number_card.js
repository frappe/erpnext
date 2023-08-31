frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.SummaryCard = class SummaryCard {
	/**
	 * {
	 * 	$wrapper: $wrapper,
	 * 	values: {
	 * 		"Amount": [120, "text-blue"],
	 * 		"Unallocated Amount": [200]
	 * 	},
	 * 	wrapper_class: "custom-style",
	 * 	currency: "USD"
	 * }
	*/
	constructor(opts) {
		Object.assign(this, opts);
		this.make();
	}

	make() {
		this.$wrapper.empty();
		let $container = null;

		if (this.$wrapper.find(".report-summary").length > 0) {
			$container = this.$wrapper.find(".report-summary");
			$container.empty();
		} else {
			$container = this.$wrapper.append(
				`<div class="report-summary ${this.wrapper_class || ""}"></div>`
			).find(".report-summary");
		}

		Object.keys(this.values).map((key) => {
			let values = this.values[key];
			let data = {
				value: values[0],
				label: __(key),
				datatype: "Currency",
				currency: this.currency,
			}

			let number_card = frappe.utils.build_summary_item(data);
			$container.append(number_card);

			if (values.length > 1) {
				let $text = number_card.find(".summary-value");
				$text.addClass(values[1]);
			}
		});
	}
}