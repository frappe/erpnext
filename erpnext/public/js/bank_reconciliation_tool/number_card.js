frappe.provide("erpnext.accounts.bank_reconciliation");

erpnext.accounts.bank_reconciliation.NumberCardManager = class NumberCardManager {
	constructor(opts) {
		Object.assign(this, opts);
		this.make_cards();
	}

	make_cards() {
		this.$reconciliation_tool_cards.empty();
		this.$cards = [];
		this.$summary = $(`<div class="report-summary"></div>`)
			.hide()
			.appendTo(this.$reconciliation_tool_cards);
		var chart_data = [
			{
				value: this.bank_statement_closing_balance,
				label: "Closing Balance as per Bank Statement",
				datatype: "Currency",
				currency: this.currency,
			},
			{
				value: this.cleared_balance,
				label: "Closing Balance as per ERP",
				datatype: "Currency",
				currency: this.currency,
			},
			{
				value:
					this.bank_statement_closing_balance - this.cleared_balance,
				label: "Difference",
				datatype: "Currency",
				currency: this.currency,
			},
		];

		chart_data.forEach((summary) => {
			let number_card = new erpnext.accounts.NumberCard(summary);
			this.$cards.push(number_card);

			number_card.$card.appendTo(this.$summary);
		});
		this.$cards[2].set_value_color(
			this.bank_statement_closing_balance - this.cleared_balance == 0
				? "text-success"
				: "text-danger"
		);
		this.$summary.css({"border-bottom": "0px", "margin-left": "0px", "margin-right": "0px"});
		this.$summary.show();
	}
};

erpnext.accounts.NumberCard = class NumberCard {
	constructor(options) {
		this.$card = frappe.utils.build_summary_item(options);
	}

	set_value(value) {
		this.$card.find("div").text(value);
	}

	set_value_color(color) {
		this.$card
			.find("div")
			.removeClass("text-danger text-success")
			.addClass(`${color}`);
	}

	set_indicator(color) {
		this.$card
			.find("span")
			.removeClass("indicator red green")
			.addClass(`indicator ${color}`);
	}
};
