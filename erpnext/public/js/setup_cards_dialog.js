frappe.setup.CardsDialog = class CardsDialog extends frappe.ui.Dialog {
	constructor(wrapper) {
		super(wrapper);
	}
	async make() {
		super.make();
		this.cards_selector = {
			card_list: [],
			active_parent: {},
		};
		this.cards_refresh();
	}
	wait_for_el(id, func) {
		const elInterval = setInterval(() => {
			if ($(id).length) {
				elInterval && clearInterval(elInterval);
				$(id).on("click", func);
			}
		}, 100);
	}
	card_click_event = (e, card, cards) => {
		e.preventDefault();
		if (card.required_by?.length){
			return frappe.show_alert({message: `${card.name} is required by ${card.required_by.map((r) => `${r[1]}`).join(", ")}`, indicator: "orange"})
		}
		card.enabled = !card.enabled;
		if (card.enabled){
			card.clicked = true;
			card.depends_on?.forEach((dc) => {
			let d = cards.find((c) => c.type == dc[0] && c.name == dc[1])
			d.enabled = true;
			if (d.required_by){
				if (d.required_by.findIndex((r) => r[0] == card.type && r[1] == card.name) == -1){
					d.required_by.push([card.type, card.name])
				}
			} else {
				d.required_by = [[card.type, card.name]]
			}
		})
		} else {
			card.clicked = false;
			card.depends_on?.forEach((dc) => {
				let d = cards.find((c) => c.type == dc[0] && c.name == dc[1])
				d.required_by = d.required_by?.filter((r) => !(r[0] == card.type && r[1] == card.name)) || [];
				if (!d.clicked && !d.required_by?.length){
					d.enabled = false;
				}
			})
		}
		this.cards_refresh();
	}
	setup_btns() {
		if (frappe.setup.data.primary_domain.name != this.cards_selector.active_parent.name) {
			this.custom_actions.empty().append(`<button class="btn btn-danger btn-sm" id="disable-domain">Disable</button>`);
			this.wait_for_el("#disable-domain:visible", () => {
				this.cards_selector.active_parent.on_disable?.(this.cards_selector.active_parent);
			})
		}
	}
	async cards_refresh() {
		const cards = this.cards_selector["card_list"];
		this.setup_btns();	
		this.$body.empty()
		if (!cards?.length) return;
		this.$body.append(`
            <div class="module-cards" id="module-cards">
				${cards.filter((c) => !c.is_hidden).map((card) => {
						const id = frappe.utils.get_random(10);
						card.id = id;
						this.wait_for_el(`#${id}`, (e) => this.card_click_event(e, card, cards));
						let isActive = card.enabled ? " active" : "";
						return `
							<div class="module-card${isActive}" id="${id}">
								<div class="module-header">
									<h5 class="module-title">${card.name}</h5>
									<span class="fa fa-check-circle icon-show"></span>
								</div>
								<div class="module-body">
									<p class="module-desc">${card.description}</p>
								</div>
							</div>
						`;
					})
					.join("")}
            </div>
			`);
	}
};
