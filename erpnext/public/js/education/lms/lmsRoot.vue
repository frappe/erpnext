<template>
	<div id="lms-root">
	<router-view :key="$route.fullPath"></router-view>
	</div>
</template>
<script>
import Navbar from "./components/Navbar.vue"
export default {
	name: "lmsRoot",
	components: {
		Navbar
	}
};
</script>
