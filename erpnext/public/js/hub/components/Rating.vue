<template>
    <span>
        <i v-for="index in max_rating"
            :key="index"
            class="fa fa-fw star-icon"
            :class="{'fa-star': index <= rating, 'fa-star-o': index > rating}"
        >
        </i>
    </span>
</template>

<script>
export default {
    props: ['rating', 'max_rating']
}
</script>
