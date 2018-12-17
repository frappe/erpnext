<template>
<div class="card mt-3" data-list="getting-started">
    <div class='card-body'>
        <div class="row">
            <div class="course-details col-xs-8 col-sm-9 col-md-10">
                <h5 class="card-title">{{ course.course_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    Topics
                    <ul class="mb-0 mt-1">
                        <li v-for="topic in course.course_topic" :key="topic.name">
                            <div><span style="padding-right: 0.4em"></span>{{ topic.topic_name }}</div>
                        </li>
                    </ul>
                </span>
            </div>
            <div class='course-buttons text-center col-xs-4 col-sm-3 col-md-2'>
                <a-button
                    :type="'primary'"
                    size="sm btn-block"
                    :route="courseRoute"
                >
                    View Course
                </a-button>
            </div>
        </div>
    </div>
</div>
</template>

<script>
import AButton from './Button.vue';

export default {
    props: ['course', 'program_name'],
    name: "CourseCard",
    components: {
        AButton
    },
    computed: {
        courseRoute() {
            return `${this.program_name}/${this.course.name}`
        },
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