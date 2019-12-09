<template>
	<div class="hub-item-sort">
		<button
			@click="change_sort"
			:class="['sort-grp',
				'material-icons',
				{'icon-flipped': this.asc}]"
		>
			<i class="material-icons">sort</i>
		</button>
		<li @click="toggle_menu()" class="sort-dropdown-toggle" v-if="selected_option.name !== undefined">
			{{ selected_option.name }}
			<span class="caret"></span>
		</li>

		<li @click="toggle_menu()" class="sort-dropdown-toggle" v-if="selected_option.name === undefined">
			{{placeholderText}}
			<span class="caret"></span>
		</li>
		<ul class="sort-dropdown-menu" v-if="showMenu">
			<li v-for="(option, idx) in options" :key="idx">
				<a href="javascript:void(0)" @click="update_option(option)">{{ option.name }}</a>
			</li>
		</ul>
	</div>
</template>

<script>
export default {
	data() {
		return {
			selected_option: {
				name: ''
			},
			asc: false,
			showMenu: false,
			placeholderText: 'Please select an item'
		};
	},
	props: {
		options: {
			type: [Array, Object]
		},
		selected: {},
		placeholder: [String],
		close_on_outside_click: {
			type: [Boolean],
			default: true
		}
	},

	mounted() {
		this.selected_option = this.selected;
		if (this.placeholder) {
			this.placeholderText = this.placeholder;
		}

		if (this.close_on_outside_click) {
			document.addEventListener('click', this.clickHandler);
		}
	},

	beforeDestroy() {
		document.removeEventListener('click', this.clickHandler);
	},

	methods: {
		update_option(option) {
			this.selected_option = option;
			this.selected_option['asc'] = this.asc;
			this.showMenu = false;
			this.$emit('update_option', this.selected_option);
		},

		toggle_menu() {
			this.showMenu = !this.showMenu;
		},

		change_sort() {
			this.asc = !this.asc;
			if (this.selected !== 'Sort By') {
				this.update_option(this.selected);
			}
		},

		clickHandler(event) {
			const { target } = event;
			const { $el } = this;

			if (!$el.contains(target)) {
				this.showMenu = false;
			}
		}
	}
};
</script>

<style scoped>
@font-face {
	font-family: 'Material Icons';
	font-style: normal;
	font-weight: 400;
	src: url(https://fonts.gstatic.com/s/materialicons/v29/2fcrYFNaTjcS6g4U3t-Y5ZjZjT5FdEJ140U2DJYC3mY.woff2)
		format('woff2');
}

.material-icons {
	font-family: 'Material Icons';
	font-weight: normal;
	font-style: normal;
	font-size: 24px;
	line-height: 1;
	letter-spacing: normal;
	text-transform: none;
	display: inline-block;
	white-space: nowrap;
	word-wrap: normal;
	direction: ltr;
	-webkit-font-feature-settings: 'liga';
	-webkit-font-smoothing: antialiased;
}

li {
	list-style: none;
}
</style>