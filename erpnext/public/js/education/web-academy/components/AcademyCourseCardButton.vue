<template>
	<button :class="getClassName" class='btn btn-primary btn-sm btn-block' @click="$router.push($route.path + '/' + course + '/' + nextContentType + '/' + nextContent)">{{ getButtonName }}</button>
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
        this.$root.$data.updateCompletedCourses()
    }
    computed: {
        getButtonName: function() {
            if(this.$root.$data.checkCourseCompletion(this.course)){
                return 'Completed'
            }
            else{
                return 'Start'
            }
        },
        getClassName: function() {
            if(this.$root.$data.checkCourseCompletion(this.course)){
                return 'btn-success'
            }
        }
    }
};
</script>