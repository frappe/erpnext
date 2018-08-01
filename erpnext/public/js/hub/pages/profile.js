import SubPage from './base_page';

erpnext.hub.Profile = class Profile extends SubPage {
	make_wrapper() {
		super.make_wrapper();
	}

	refresh() {
		this.get_hub_seller_profile(this.keyword)
			.then(profile => this.render(profile));
	}

	get_hub_seller_profile() {
		return hub.call('get_hub_seller_profile', { hub_seller: hub.settings.company_email });
	}

	render(profile) {
		const p = profile;
		const content_by_log_type = this.get_content_by_log_type();

		let activity_logs = (p.hub_seller_activity || []).sort((a, b) => {
			return new Date(b.creation) - new Date(a.creation);
		});

		const timeline_items_html = activity_logs
			.map(log => {
				const stats = JSON.parse(log.stats);
				const no_of_items = stats && stats.push_update || '';

				const content = content_by_log_type[log.type];
				const message = content.get_message(no_of_items);
				const icon = content.icon;
				return this.get_timeline_log_item(log.pretty_date, message, icon);
			})
			.join('');

		const profile_html = `<div class="hub-item-container">
			<div class="row visible-xs">
				<div class="col-xs-12 margin-bottom">
					<button class="btn btn-xs btn-default" data-route="marketplace/home">Back to home</button>
				</div>
			</div>
			<div class="row">
				<div class="col-md-3">
					<div class="hub-item-image">
						<img src="${p.logo}">
					</div>
				</div>
				<div class="col-md-6">
					<h2>${p.company}</h2>
					<div class="text-muted">
						<p>${p.country}</p>
						<p>${p.site_name}</p>
					</div>
					<hr>
					<div class="hub-item-description">
					${'description'
						? `<p>${p.company_description}</p>`
						: `<p>__('No description')</p`
					}
					</div>
				</div>
			</div>

			<div class="timeline">
				<div class="timeline-items">
					${timeline_items_html}
				</div>
			</div>

		</div>`;

		this.$wrapper.html(profile_html);
	}

	get_timeline_log_item(pretty_date, message, icon) {
		return `<div class="media timeline-item  notification-content">
			<div class="small">
				<i class="octicon ${icon} fa-fw"></i>
				<span title="Administrator"><b>${pretty_date}</b> ${message}</span>
			</div>
		</div>`;
	}

	get_content_by_log_type() {
		return {
			"Created": {
				icon: 'octicon-heart',
				get_message: () => 'Joined Marketplace'
			},
			"Items Publish": {
				icon: 'octicon-bookmark',
				get_message: (no_of_items) =>
					`Published ${no_of_items} product${no_of_items > 1 ? 's' : ''} to Marketplace`
			}
		}
	}
}