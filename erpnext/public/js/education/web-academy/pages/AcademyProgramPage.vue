<template>
<div>
	Program Page {{ code }}
</div>
</template>
<script>
export default {
	props: ['code'],
    name: "AcademyProgramPage",
    data() {
   		return this.code
    }
};
</script>