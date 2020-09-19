frappe.provide('healthcare');

healthcare.InpatientMedicationOrderView = class InpatientMedicationOrderView {
	constructor({
		wrapper,
		data,
		columns,
		datatable_class,
		addCheckboxColumn,
		showBorders
	}) {
		this.wrapper = wrapper;
		this.data = data;
		this.columns = columns;
		this.datatable_class = datatable_class;
		this.addCheckboxColumn = addCheckboxColumn;
		this.showBorders = showBorders;

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
						<div class="${this.datatable_class}"></div>
					</div>
				</div>
			</div>
		`);

		this.$order_view = this.wrapper.find('.' + `${this.datatable_class}`);

		if (this.showBorders) {
			this.$order_view.find('.' + `${this.datatable_class}`).addClass('border');
		}
	}

	render_datatable() {
		if (this.orders_datatable) {
			this.orders_datatable.destroy();
		}

		this.orders_datatable = new frappe.DataTable(this.$order_view.get(0), {
			data: this.data,
			columns: this.columns,
			checkboxColumn: this.addCheckboxColumn,
			addCheckboxColumn: this.addCheckboxColumn,
			cellHeight: 35,
			disableReorderColumn: true,
			inlineFilters: true,
			noDataMessage: __('No Data')
		});

		if (this.data.length === 0) {
			this.orders_datatable.style.setStyle('.dt-scrollable', {
				height: 'auto'
			});
		}

		this.orders_datatable.style.setStyle('.dt-dropdown', {
			display: 'none'
		});
	}
};
