<template>
	<div id="lms-root">
	<router-view :key="$route.fullPath"></router-view>
	</div>
</template>
<script>
export default {
	name: "lmsRoot",
};
</script>