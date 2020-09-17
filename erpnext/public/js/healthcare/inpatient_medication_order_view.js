frappe.provide('healthcare');

healthcare.InpatientMedicationOrderView = class InpatientMedicationOrderView {
	constructor({
		wrapper,
		data,
		columns
	}) {
		this.wrapper = wrapper;
		this.data = data;
		this.columns = columns;

		this.make();
	}

	make() {
		this.make_wrapper();
		this.render_datatable();
	}

	make_wrapper() {
		this.wrapper.html(`
			<div>
				<div class="row">
					<div class="col-sm-12">
						<div class="table-orders border"></div>
					</div>
				</div>
			</div>
		`);

		this.$order_view = this.wrapper.find('.table-orders');
	}

	render_datatable() {
		if (this.orders_datatable) {
			this.orders_datatable.destroy();
		}

		this.orders_datatable = new frappe.DataTable(this.$order_view.get(0), {
			data: this.data,
			columns: this.columns,
			checkboxColumn: true,
			addCheckboxColumn: true,
			cellHeight: 35,
			noDataMessage: __('No Data')
		});
	}
};
