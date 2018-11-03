<template>
	<button class='btn btn-primary btn-lg' @click="$router.push()">{{ buttonName }}</button>
</template>
<script>
export default {
    name: "AcademyTopSectionButton",
    data() {
        return {
            buttonName: '',
            url: {}
        }
    },
    mounted() {
    	if(this.$route.name == 'home'){
    		this.buttonName = 'Explore Courses'
            this.url = {}
    	}
        else if(this.$route.name == 'program'){
            this.buttonName = 'Start Course'
            this.url = {
                name: 'content',
                params: {
                    code: this.$route.params.code,
                    course: this.$route.params.course,
                    type: this.nextContentType,

                }
            }
        }
    }
};
</script>