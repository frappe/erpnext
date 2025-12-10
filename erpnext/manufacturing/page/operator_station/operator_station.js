frappe.pages['operator-station'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Operator Station',
		single_column: true
	});

	new erpnext.mfg.OperatorStation(page);
};
erpnext.mfg = erpnext.mfg || {};

erpnext.mfg.OperatorStation = class OperatorStation {
    constructor(page) {
		this.page = page;
		this.$wrapper = $(page.body);
		this.timer = null;
		this.elapsed_seconds = 0;
		this.alarms = [];
		this.make_layout();
	}

    make_layout() {
        this.$wrapper.html(`
            <div class="operator-station page-card d-flex flex-column align-items-center">
				<div class="current-job-card mb-4 border border-dark w-50 rounded p-4">
					<div class="status text-center mb-2" style="font-size:1rem">
						<span class="badge badge-info badge-pill" style="padding:.5rem">
							${__('Pending')}
						</span>
					</div>
					
					<div class="text-center text-muted small">${__('SERIAL NUMBER')}</div>
					<h2 class="job-serial text-center font-weight-bold mb-2 p-3">
						SLB-2025-00427
					</h2>
					
					<div class="text-center text-muted small mb-1">${__('Colour')}</div>
					<div class="d-flex justify-content-center align-items-center mb-3">
						<span class="job-color mr-2">Carrara White</span>
						<span class="color-swatch" style="width:24px;height:24px;border-radius:4px;background:#f5f5f5;border:1px solid #ddd;"></span>
					</div>
					
					<div class="text-center mb-2">
						<button class="btn btn-success py-3 px-4 start-button-row" data-action="start-job">
							<span class="fa fa-play mr-1 pr-2"></span>${__('Start Job')}
						</button>
					</div>
					
					<div class="text-center mb-3 timer-row" style="display:none;">
						<div class="text-success" style="font-size:1.5rem">
							<span class="fa fa-clock-o mr-1"></span>
							<span class="job-timer">00:00:00</span>
						</div>
					</div>

					<div class="text-center mb-2 action-buttons-row" style="display:none;">
						<button class="btn btn-info mr-2" data-action="finish-job">
							<span class="fa fa-check-square-o mr-1"></span>${__('Finish Job')}
						</button>
						<button class="btn btn-warning mr-2" data-action="halt-job">
							<span class="fa fa-pause-circle-o mr-1"></span>${__('Halt Job')}
						</button>
						<button class="btn btn-danger" data-action="discard-job">
							<span class="fa fa-trash-o mr-1"></span>${__('Discard')}
						</button>
					</div>
				</div>

            <div class="raise-alarm-box mb-4 w-50 border border-dark rounded p-4">
                <div class="d-flex flex-column justify-content-between mb-1 py-3">
                    <div class="d-flex align-items-center">
						<span class="fa fa-exclamation-triangle mr-2"
							style="color:#ffc107; border:1px solid #ffc107; border-radius:50%; padding:4px;"></span>
							<h5 class="mb-1">${__('Raise Alarm')}</h5>
					</div>
					<div class="text-muted small">
						${__('Report issues to the mixer operator')}
					</div>
                </div>
				<button class="btn btn-outline-warning btn-block border border-warning" data-action="raise-alarm">
					<span class="fa fa-exclamation-triangle mr-1"></span>
					${__('Report Issue to Mixer')}
				</button>
            </div>

            <div class="downstream-alarms-box w-50 border border-dark rounded p-4">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                        <span class="fa fa-bell mr-1"></span>
                        <span class="font-weight-bold">${__('Downstream Alarms')}</span>
                        <span class="badge badge-danger ml-2 alarms-count">2</span>
                    </div>
                    <a href="javascript:void(0)" class="text-muted small" data-action="toggle-alarms">
                        <span class="fa fa-chevron-down"></span>
                    </a>
                </div>
                <div class="alarms-list pt-4">
                    <!-- cards injected here -->
                </div>
            </div>
        </div>
    `);

    this.render_dummy_alarms();

    this.$wrapper.on('click', '[data-action="start-job"]', () => this.start_job());
    this.$wrapper.on('click', '[data-action="raise-alarm"]', () => this.raise_alarm());
    this.$wrapper.on('click', '[data-action="toggle-alarms"]', () => this.toggle_alarms());

	this.$wrapper.on('click', '[data-action="finish-job"]', () => this.finish_job());
	this.$wrapper.on('click', '[data-action="halt-job"]', () => this.halt_job());
	this.$wrapper.on('click', '[data-action="discard-job"]', () => this.discard_job());
    }

    start_job() {
		this.$wrapper.find('.status .badge')
			.text(__('In Progress'))
			.css({
				background: '#d4f8d4',
				color: '#137a13'
			});

		this.$wrapper.find('.start-button-row').hide();

        this.$wrapper.find('.timer-row').show();
		this.$wrapper.find('.action-buttons-row').show();

		this.elapsed_seconds = 0;
		this.update_timer_display();
		if (this.timer) clearInterval(this.timer);

		this.timer = setInterval(() => {
			this.elapsed_seconds += 1;
			this.update_timer_display();
		}, 1000);
    }

	update_timer_display() {
		const h = String(Math.floor(this.elapsed_seconds / 3600)).padStart(2, '0');
		const m = String(Math.floor((this.elapsed_seconds % 3600) / 60)).padStart(2, '0');
		const s = String(this.elapsed_seconds % 60).padStart(2, '0');
		this.$wrapper.find('.job-timer').text(`${h}:${m}:${s}`);
	}

	toggle_alarms() {
		const $list = this.$wrapper.find('.alarms-list');
		$list.toggle();
	}

    raise_alarm() {
		const d = new frappe.ui.Dialog({
			title: __('Raise Alarm'),
			fields: [
				{ 
					fieldname: 'issue_type', label: __('Issue Type'), fieldtype: 'Select',
					options: ['Quality Issue','Machine Problem','Material Issue','Other'], reqd: 1 
				},
				{ 
					fieldname: 'description', label: __('Description'), fieldtype: 'Small Text', reqd: 1 
				},
				{ 
					fieldname: 'serial_no', label: __('Serial Number'), fieldtype: 'Data',
					default: this.current_serial || 'SLB-2025-00427' 
				},
			],
			primary_action_label: __('Submit'),
			primary_action: (values) => {
				const now = frappe.datetime.now_time(); 	
				this.alarms.unshift({
					station: __('Mixer'),
					type: values.issue_type.toUpperCase(),
					description: values.description,
					time: now,
					tone: 'warning'
				});

				this.render_alarms();  
				frappe.msgprint(__('Alarm submitted'));
				d.hide();
			}
		});
		d.show();
	}

	finish_job() {
		this.$wrapper.find('.status .badge')
			.text(__('Finished'))
			.css({
				background: '#d1ecf1',
				color: '#0c5460'
			});

		if (this.timer) {
			clearInterval(this.timer);
			this.timer = null;
		}
		this.elapsed_seconds = 0;
		this.update_timer_display();
		this.$wrapper.find('.timer-row').hide();
		this.$wrapper.find('.action-buttons-row').hide();
		this.$wrapper.find('.start-button-row').show();

		frappe.msgprint(__('Job is Finished'));
	}

	discard_job() {
		frappe.confirm(
			__('Are you sure you want to discard this job?'),
			() => {
				this.$wrapper.find('.status .badge')
					.text(__('Discarded'))
					.css({
						background: '#f8d7da',
						color: '#721c24'
					});
				if (this.timer) {
					clearInterval(this.timer);
					this.timer = null;
				}
				this.elapsed_seconds = 0;
				this.update_timer_display();
				this.$wrapper.find('.timer-row').hide();
				this.$wrapper.find('.action-buttons-row').hide();
				this.$wrapper.find('.start-button-row').show();

				frappe.msgprint(__('Job is discarded'));
			},
			() => {
			}
		);
	}

	halt_job() {
		this.$wrapper.find('.status .badge')
			.text(__('Halted'))
			.css({
				background: '#ffeeba',  
				color: '#856404'
			});
		if (this.timer) {
			clearInterval(this.timer);
			this.timer = null;
		}
		frappe.msgprint(__('Job is halted'));
	}


	render_dummy_alarms() {
		this.alarms = [
			{
				station: 'Polishing 1',
				type: __('QUALITY ISSUE'),
				description: __('Surface defect detected on SLB-2025-00425'),
				time: '14:23:15',
				tone: 'danger'
			},
			{
				station: 'Trimmer',
				type: __('MACHINE PROBLEM'),
				description: __('Blade alignment issue'),
				time: '14:15:42',
				tone: 'warning'
			}
		];
		this.render_alarms();
	}

	render_alarms() {
		const $list = this.$wrapper.find('.alarms-list').empty();
		this.alarms.forEach(a => {
			const bg = a.tone === 'danger' ? '#ffecec' : '#fff9e6';
			$list.append(`
				<div class="alarm-card mb-2" style="background:${bg};border-radius:8px;padding:12px 16px;">
					<div class="d-flex justify-content-between mb-1">
						<div class="font-weight-bold">${a.station}</div>
						<div class="text-muted small">${a.time}</div>
					</div>
					<div class="text-uppercase text-muted small mb-1">${a.type}</div>
					<div class="small">${a.description}</div>
				</div>
			`);
		});
		this.$wrapper.find('.alarms-count').text(this.alarms.length);
	}
};

