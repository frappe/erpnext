<template>
	<button :class="className" class='btn btn-primary btn-sm btn-block' @click="$router.push($route.path + '/' + course + '/' + nextContentType + '/' + nextContent)">{{ buttonName }}</button>
</template>
<script>
export default {
    props: ['course', 'nextContent', 'nextContentType'],
    name: "AcademyCourseCardButton",
    data() {
        return {
            buttonName: 'Start',
            className: 'btn-primary'
        }
    },
    mounted() {
    	if(this.$root.$data.checkCourseCompletion(this.course)){
    		this.buttonName = 'Completed'
    		this.className = 'btn-success'
    	}
    }
};
</script>