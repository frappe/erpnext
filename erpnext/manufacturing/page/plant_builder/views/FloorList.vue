<script setup>
import { onMounted, ref } from "vue";
import { Button } from "frappe-ui";
import { __, call, setRoute } from "../lib/api";
import { machineOf } from "../lib/machines";
import { MACHINE_STATUS } from "../lib/floor";

const emit = defineEmits(["title", "actions"]);
const floors = ref([]);
const loading = ref(true);

onMounted(async () => {
	emit("title", __("Plant Builder"));
	emit("actions", [
		{
			label: __("New Process Design"),
			onClick: () => window.frappe.new_doc("BOM Creator", { track_semi_finished_goods: 1 }),
		},
	]);
	floors.value = await call("get_floors");
	loading.value = false;
});

const open = (floor) => setRoute(floor.name);
const addFloor = () => setRoute("new");

function meta(floor) {
	const running = floor.machines.filter((machine) => machine.job).length;
	const count = floor.machines.length;
	const parts = [count === 1 ? __("1 machine") : __("{0} machines", [count])];
	if (running) parts.push(__("{0} running", [running]));
	return parts.join(" · ");
}
</script>

<template>
	<div class="min-h-0 flex-1 overflow-auto">
		<div class="mx-auto max-w-5xl px-5 pb-10 pt-6">
			<div class="flex items-start gap-4">
				<p class="max-w-[680px] flex-1 text-p-base text-ink-gray-7">
					{{
						__(
							"A plant floor is where your machines stand. Add machines to a floor to see them in 3D and what each one is running. Design the process in BOM Creator with Process Manufacturing, then run its Work Orders here."
						)
					}}
				</p>
				<Button
					variant="solid"
					icon-left="lucide-plus"
					:label="__('New Plant Floor')"
					@click="addFloor"
				/>
			</div>
			<div class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
				<div
					v-for="floor in floors"
					:key="floor.name"
					role="link"
					tabindex="0"
					class="flex cursor-pointer flex-col gap-3 rounded-5 border border-outline-gray-2 bg-surface-base p-4 hover:bg-surface-gray-1"
					@click="open(floor)"
					@keydown.enter="open(floor)"
				>
					<div class="flex h-8 items-center gap-1.5">
						<span
							v-for="machine in floor.machines"
							:key="machine.name"
							class="relative flex size-8 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-6"
							:title="`${machine.name} · ${__(machine.status || 'Off')}`"
						>
							<span
								class="size-4"
								:class="machineOf(machine.machine_model).icon"
								aria-hidden="true"
							/>
							<span
								class="absolute right-0.5 top-0.5 size-1.5 rounded-full"
								:class="MACHINE_STATUS[machine.status]?.dot || 'bg-surface-gray-5'"
								aria-hidden="true"
							/>
						</span>
						<span v-if="!floor.machines.length" class="text-sm text-ink-gray-5">{{
							__("No machines yet")
						}}</span>
					</div>
					<div class="min-w-0">
						<p class="truncate text-lg-semibold text-ink-gray-8">
							{{ floor.floor_name || floor.name }}
						</p>
						<p class="truncate text-sm text-ink-gray-6">
							{{ floor.warehouse || __("No store set yet") }}
						</p>
						<p class="mt-1 truncate text-xs text-ink-gray-5">{{ meta(floor) }}</p>
					</div>
				</div>
				<div
					role="button"
					tabindex="0"
					class="flex min-h-[11rem] cursor-pointer flex-col items-center justify-center gap-2 rounded-5 border border-dashed border-outline-gray-3 text-center hover:bg-surface-gray-1"
					@click="addFloor"
					@keydown.enter="addFloor"
				>
					<span class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
						<span class="lucide-factory block size-5" aria-hidden="true" />
					</span>
					<p class="text-base text-ink-gray-7">{{ __("Add a plant floor") }}</p>
					<p class="text-sm text-ink-gray-5">{{ __("Then place your machines on it") }}</p>
				</div>
			</div>
			<p v-if="loading" class="mt-6 text-sm text-ink-gray-5">{{ __("Loading...") }}</p>
		</div>
	</div>
</template>
