<template>
<div>
	<TopSection :title="portal.title" :description="portal.description">
        <TopSectionButton/>
    </TopSection>
	<CardList :title="'Featured Programs'" :description="'Master ERPNext'">
        <ProgramCard v-for="item in featuredPrograms" :key="item.program.name" :program="item.program" :enrolled="item.is_enrolled"/>
    </CardList>
</div>
</template>
<script>
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"
import ProgramCard from "../components/ProgramCard.vue"
import TopSectionButton from "../components/TopSectionButton.vue"

export default {
    name: "Home",
    data() {
    	return{
    		portal: {},
            featuredPrograms: [],
            // enrolledPrograms: new Set()
    	}
    },
    components: {
		TopSection,
        CardList,
        ProgramCard,
        TopSectionButton
    },
    beforeMount() {
        // this.updateEnrolledPrograms().then(data => {
        //     data.forEach(element => {
        //         this.enrolledPrograms.add(element)
        //     })
        // });
    },
	mounted() {
        this.getPortalDetails().then(data => this.portal = data);
        this.getFeaturedPrograms().then(data => this.featuredPrograms = data);
    },
    methods: {
        // updateEnrolledPrograms(){
        //     return lms.call("get_program_enrollments")
        // },
        getPortalDetails() {
            return lms.call("get_portal_details")
        },
        getFeaturedPrograms() {
            return lms.call("get_featured_programs")
        }
    }
};
</script>