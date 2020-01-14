<template>
	<div class="hub-image">
		<img :src="src" :alt="alt" v-show="!is_loading && !is_broken"/>
		<div class="hub-image-loading" v-if="is_loading">
			<span class="octicon octicon-cloud-download"></span>
		</div>
		<div class="hub-image-broken" v-if="is_broken">
			<span class="octicon octicon-file-media"></span>
		</div>
	</div>
</template>
<script>
export default {
	name: 'Image',
	props: ['src', 'alt'],
	data() {
		return {
			is_loading: true,
			is_broken: false
		}
	},
	created() {
		this.handle_image();
	},
	methods: {
		handle_image() {
			let img = new Image();
			img.src = this.src;

			img.onload = () => {
				this.is_loading = false;
			};
			img.onerror = () => {
				this.is_loading = false;
				this.is_broken = true;
			};
		}
	}
};
</script>
