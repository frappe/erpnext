<template>
<div class="card mt-3" data-list="getting-started">
    <div class='card-body'>
        <div class="row">
            <div class="course-details col-xs-8 col-sm-9 col-md-10">
                <h5 class="card-title">{{ course.course_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    Course Content
                    <ul class="mb-0 mt-1">
                            <li v-for="content in course.course_content" :key="content.name">{{ content.content }}</li>
                    </ul>
                </span>
            </div>
            <div class='course-buttons text-center col-xs-4 col-sm-3 col-md-2'>
                <a-button
                    :type="buttonType"
                    size="sm btn-block"
                    :route="firstContentRoute"
                >
                    {{ courseMeta.flag }}
                </a-button>
            </div>
        </div>
    </div>
</div>
</template>

<script>
import AButton from './Button.vue';
import AcademyCourseCardButton from './AcademyCourseCardButton.vue'

export default {
    props: ['course', 'courseMeta', 'program_name'],
    name: "AcademyCourseCard",
    components: {
        AcademyCourseCardButton,
        AButton
    },
    computed: {
        showStart() {
            return lms.loggedIn && !this.courseMeta.flag == "Completed";
        },
        showCompleted() {
            return lms.loggedIn && this.courseMeta.flag == "Completed";
        },
        firstContentRoute() {
            return `${this.program_name}/${this.course.name}/${this.courseMeta.content_type}/${this.courseMeta.content}`
        },
        buttonType() {
            if (this.courseMeta.flag == "Start" ){
                return "primary"
            }
            else if (this.courseMeta.flag == "Complete" ) {
                return "success"
            }
            else if (this.courseMeta.flag == "Continue" ) {
                return "info"
            }
            else {
                return " hidden"
            }
        }
    }
};
</script>

<style scoped>
    @media only screen and (max-width: 576px) {
    .course-buttons {
        margin-top: 1em;
    }
}
</style>