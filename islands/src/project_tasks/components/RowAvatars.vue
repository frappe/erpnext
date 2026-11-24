<script setup>
import { computed } from "vue";
import { Avatar } from "frappe-ui";

import { avatarTheme } from "../../project_overview/colors.js";
import { person } from "../../project_overview/host.js";

// The avatars in a list row: up to three, then "+N". Lighter than the Overview's stack, which
// has a tooltip per avatar, as a long list has a stack per row; the names are on the row's
// button instead.
const props = defineProps({
	users: { type: Array, required: true },
});

const MAX = 3;
const people = computed(() => props.users.map(person));
// one extra person shows instead of "+1"
const shown = computed(() => (people.value.length <= MAX + 1 ? people.value : people.value.slice(0, MAX)));
const hidden = computed(() => people.value.length - shown.value.length);
</script>

<template>
	<span class="flex items-center -space-x-1" aria-hidden="true">
		<span v-for="item in shown" :key="item.user" class="rounded-full ring-2 ring-[var(--surface-base)]">
			<Avatar
				size="sm"
				:label="item.fullname"
				:image="item.image"
				:theme="avatarTheme(item.fullname)"
			/>
		</span>
		<span
			v-if="hidden"
			class="flex size-5 items-center justify-center rounded-full bg-surface-gray-2 text-[10px] font-medium text-ink-gray-8 ring-2 ring-[var(--surface-base)]"
		>
			+{{ hidden }}
		</span>
	</span>
</template>
