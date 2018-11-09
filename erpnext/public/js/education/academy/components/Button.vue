<template>
	<button :class="classList" v-on="$listeners" v-bind="$attrs" @click="goToRoute">
		<slot></slot>
	</button>
</template>
<script>
export default {
	name: 'AButton',
	props: ['type', 'size', 'route'],
	computed: {
		classList() {
			return [
				'btn',
				'btn-' + this.type,
				'btn-' + this.size
			]
		}
	},
	methods: {
		goToRoute() {
			this.$router.push(this.route);
		}
	}
}
</script>
