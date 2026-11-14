<script setup>
import { Button, Tooltip } from "frappe-ui";
import { __ } from "../../lib/api";

defineProps({ panBy: Function });

const STEP = 100;
const MOVES = [
	{ label: __("Move left"), icon: "lucide-arrow-left", dx: STEP, dy: 0 },
	{ label: __("Move up"), icon: "lucide-arrow-up", dx: 0, dy: STEP },
	{ label: __("Move down"), icon: "lucide-arrow-down", dx: 0, dy: -STEP },
	{ label: __("Move right"), icon: "lucide-arrow-right", dx: -STEP, dy: 0 },
];
</script>

<template>
	<div class="flex items-center gap-0.5 rounded-4 border border-outline-gray-2 bg-surface-base p-0.5">
		<Tooltip v-for="move in MOVES" :key="move.icon" :text="move.label">
			<Button
				variant="ghost"
				:aria-label="move.label"
				:icon="move.icon"
				@click="panBy(move.dx, move.dy)"
			/>
		</Tooltip>
	</div>
</template>
