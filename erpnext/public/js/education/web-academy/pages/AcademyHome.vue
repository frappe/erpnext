<template>
<div>
	<AcademyTopSection/>
	<AcademyCardList/>
</div>
</template>
<script>
import AcademyTopSection from "../components/AcademyTopSection.vue"
import AcademyCardList from "../components/AcademyCardList.vue"

export default {
    name: "AcademyHome",
    components: {
		AcademyTopSection, AcademyCardList
	}
};
</script>