<template>
<div>
	<AcademyTopSection :title="portal.title" :description="portal.description">
        <AcademyTopSectionButton/>
    </AcademyTopSection>
	<AcademyList :title="'Featured Programs'" :description="'Master ERPNext'">
        <AcademyProgramCard v-for="item in featuredPrograms" :key="item.program.name" :program="item.program" :enrolled="item.is_enrolled"/>
    </AcademyList>
</div>
</template>
<script>
import AcademyTopSection from "../components/AcademyTopSection.vue"
import AcademyList from "../components/AcademyList.vue"
import AcademyProgramCard from "../components/AcademyProgramCard.vue"
import AcademyTopSectionButton from "../components/AcademyTopSectionButton.vue"

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
		AcademyTopSection,
        AcademyList,
        AcademyProgramCard,
        AcademyTopSectionButton
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