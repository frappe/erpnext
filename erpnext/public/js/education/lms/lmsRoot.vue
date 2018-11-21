<template>
	<div id="lms-root">
	<router-view :key="$route.fullPath"></router-view>
	</div>
</template>
<script>
export default {
	name: "lmsRoot",
	mounted() {
		$(document).scrollTop(0)
	}
};
</script>