<template>
	<div class="item-sort">
		<button class="sort-grp material-icons">
			<i class="material-icons">
				sort
			</i>
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
				<a href="javascript:void(0)" @click="update_option(option)">
					{{ option.name }}
				</a>
			</li>
		</ul>
	</div>
</template>

<script>
	export default {
		data() {
			return {
				selected_option: {
					name: '',
				},
				showMenu: false,
				placeholderText: 'Please select an item',
			}
		},
		props: {
			options: {
				type: [Array, Object]
			},
			selected: {},
			placeholder: [String],
			close_on_outside_click: {
			  type: [Boolean],
			  default: true,
			},
		},

		mounted() {
			this.selected_option = this.selected;
			if (this.placeholder)
			{
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
				this.showMenu = false;
				this.$emit('update_option', this.selected_option);
			},

			toggle_menu() {
				this.showMenu = !this.showMenu;
			},

			clickHandler(event) {
				const { target } = event;
				const { $el } = this;

				if (!$el.contains(target)) {
					this.showMenu = false;
				}
			},
		}
	}
</script>

<style scoped>

@font-face {
	font-family: 'Material Icons';
	font-style: normal;
	font-weight: 400;
	src: url(https://fonts.gstatic.com/s/materialicons/v29/2fcrYFNaTjcS6g4U3t-Y5ZjZjT5FdEJ140U2DJYC3mY.woff2) format('woff2');
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

.sort-grp{
	border: 0;
	outline: none;
	border-radius: 4px;
}
.icon-flipped {
	transform: scaleY(-1);
	-moz-transform: scaleY(-1);
	-webkit-transform: scaleY(-1);
	-ms-transform: scaleY(-1);
}

.item-sort {
	min-width: 200px;
	height: 32px;
	position: relative;
	margin: 10px 1px;
	border: 1px solid #d1d8dd;
	border-radius: 4px;
	display: inline-block;
	vertical-align: middle;
}
.item-sort a:hover {
	text-decoration: none;
}

.sort-dropdown-toggle {
	color: #636b6f;
	min-width: 140px;
	padding: 8px 20px 10px 10px;
	text-transform: none;
	font-weight: 300;
	margin-bottom: 7px;
	float: right;
	white-space: nowrap;
	text-overflow: ellipsis;
	overflow: hidden;
}
.sort-dropdown-toggle:hover {
	cursor: pointer;
}

.sort-dropdown-menu {
	position: absolute;
	top: 100%;
	left: 0;
	z-index: 1000;
	float: left;
	width: 100%;
	padding: 5px 0;
	margin: 2px 0 0;
	list-style: none;
	font-size: 14px;
	text-align: center;
	background-color: #fff;
	border: 1px solid #ccc;
	border-radius: 4px;
	box-shadow: 0 6px 12px rgba(0, 0, 0, 0.175);
	background-clip: padding-box;
}

.sort-dropdown-menu > li > a {
	padding: 10px 30px;
	display: block;
	clear: both;
	font-weight: normal;
	line-height: 1.6;
	color: #333333;
	white-space: nowrap;
	text-decoration: none;
}
.sort-dropdown-menu > li > a:hover {
	background: #f0f4f7;
}

.sort-dropdown-menu > li {
	overflow: hidden;
	width: 100%;
	position: relative;
	margin: 0;
}

.caret {
	width: 0;
	position: absolute;
	top: 14px;
	height: 0;
	margin-left: -24px;
	vertical-align: middle;
	border-top: 4px dashed;
	border-top: 4px solid \9;
	border-right: 4px solid transparent;
	border-left: 4px solid transparent;
	right: 10px;
}

li {
	list-style: none;
}
</style>