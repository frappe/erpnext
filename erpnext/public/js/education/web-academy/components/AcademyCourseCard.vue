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
                <button class='btn btn-primary btn-sm btn-block' @click="$router.push($route.path + '/' + course.name + '/' + nextContentType + '/' + nextContent)">Start Course</button>
                <button class='btn btn-primary btn-sm btn-block'>Continue</button>
                <button class='btn btn-success btn-sm btn-block'>Completed</button>
            </div>
        </div>
    </div>
</div>
</template>

<script>
export default {
    props: ['course'],
    name: "AcademyCourseCard",
    data() {
        return {
            nextContent: '',
            nextContentType: ''
        }
    },
    mounted() {
        frappe.call({
            method: "erpnext.www.academy.get_starting_content",
            args: {
                course_name: this.course.name
            }
        }).then(r => {
            this.nextContent = r.message.content,
            this.nextContentType = r.message.content_type
        });
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