<template>
	<div id="academy-root">
	<router-view :key="$route.fullPath"></router-view>
	</div>
</template>
<script>
export default {
    name: "AcademyRoot",
};
</script>