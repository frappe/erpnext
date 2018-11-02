<template>
    <section class='article-top-section video-section-bg'>
        <div class='container'>
            <div class="row">
                <div class="col-md-8">
                    <h2>{{ title }}</h2>
                    <span v-if="typeof author !== 'undefined' || variable !== null" class="text-muted">
                        Published on {{ publishDate }}, by {{ author }}
                    </span>
                </div>
                <div class="col-md-4 text-right">
                    <slot></slot>
                </div>
            </div>
            <hr>
        </div>
    </section>
</template>

<script>
export default {
    props: ['title', 'publishDate', 'author'],
    name: 'ContentTitle',
    data() {
        return {

        };
    },
};
</script>

<style lang="css" scoped>
</style>
