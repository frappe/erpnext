<script setup>
import { computed } from "vue";
import { Avatar, HoverCard, Tooltip } from "frappe-ui";

import { avatarTheme } from "../colors.js";
import { person } from "../host.js";

const MAX = 3;

const props = defineProps({
	users: { type: Array, required: true },
});

const people = computed(() => props.users.map(person));
// show one extra person instead of "+1"
const shown = computed(() => (people.value.length <= MAX + 1 ? people.value : people.value.slice(0, MAX)));
const hidden = computed(() => people.value.slice(shown.value.length));
</script>

<template>
	<div v-if="people.length" class="flex items-center -space-x-1">
		<Tooltip v-for="item in shown" :key="item.user" :text="item.fullname">
			<span class="rounded-full ring-2 ring-[var(--surface-base)]">
				<Avatar
					size="sm"
					:label="item.fullname"
					:image="item.image"
					:theme="avatarTheme(item.fullname)"
				/>
			</span>
		</Tooltip>
		<HoverCard v-if="hidden.length" align="start">
			<template #trigger>
				<span
					class="flex size-5 items-center justify-center rounded-full bg-surface-gray-2 text-[10px] font-medium text-ink-gray-8 ring-2 ring-[var(--surface-base)]"
					tabindex="0"
					role="img"
					:aria-label="hidden.map((item) => item.fullname).join(', ')"
				>
					+{{ hidden.length }}
				</span>
			</template>
			<div class="flex flex-col gap-2 p-1">
				<div v-for="item in hidden" :key="item.user" class="flex items-center gap-2">
					<Avatar
						size="sm"
						:label="item.fullname"
						:image="item.image"
						:theme="avatarTheme(item.fullname)"
					/>
					<span class="text-sm text-ink-gray-8">{{ item.fullname }}</span>
				</div>
			</div>
		</HoverCard>
	</div>
</template>
