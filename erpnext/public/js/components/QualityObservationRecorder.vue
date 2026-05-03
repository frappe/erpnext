<template>
    <div class="row">
        <div class="col-12" v-if="slabSize">
            <div class="visualizer-container position-relative mb-3"
                ref="visualizerRef"
                :style="{
                    width: '100%',
                    maxWidth: '800px',
                    aspectRatio: `${slabSize.length} / ${slabSize.breadth}`,
                    outline: '2px solid var(--text-color)',
                    background: 'var(--fg-color)',
                    cursor: 'crosshair',
                    margin: '0 auto'
                }"
                @mousemove="handleMouseMove"
                @mouseleave="handleMouseLeave"
                @click="handleSlabClick">

                <!-- Crosshairs & Labels -->
                <template v-if="hoverCoordinates.visible && !newObservation">
                    <!-- Horizontal Line -->
                    <div class="crosshair-h"
                        :style="{ top: (hoverCoordinates.y * slabScale) + 'px' }">
                    </div>

                    <!-- Vertical Line -->
                    <div class="crosshair-v"
                        :style="{ left: (hoverCoordinates.x * slabScale) + 'px' }">
                    </div>

                    <!-- X Label (Left Distance) -->
                    <div class="crosshair-label label-x"
                        :style="{
                            top: (hoverCoordinates.y * slabScale) + 'px',
                            left: (hoverCoordinates.x * slabScale) + 'px'
                        }">
                        {{ hoverCoordinates.x }} mm
                    </div>

                    <!-- Y Label (Top Distance) -->
                    <div class="crosshair-label label-y"
                        :style="{
                            top: (hoverCoordinates.y * slabScale) + 'px',
                            left: (hoverCoordinates.x * slabScale) + 'px'
                        }">
                        {{ hoverCoordinates.y }} mm
                    </div>
                </template>

                <!-- Existing Observations -->
                <div v-for="(obs, index) in observations" :key="index"
                    class="obs-marker"
                    :style="{
                        left: (obs.x * slabScale) + 'px',
                        top: (obs.y * slabScale) + 'px'
                    }"
                    :title="`${obs.text} (${obs.x}, ${obs.y})`"
                    @click.stop="editObservation(index)">
                    <div class="marker-dot" :style="{ backgroundColor: obs.colour || observationColour }"></div>
                </div>

                <!-- New Observation Input -->
                <div v-if="newObservation"
                    class="obs-input-popup p-2 shadow rounded border"
                    :style="{
                        left: (newObservation.x * slabScale) + 'px',
                        top: (newObservation.y * slabScale) + 'px',
                        position: 'absolute',
                        zIndex: 100,
                        minWidth: '200px',
                        background: 'var(--card-bg)',
                        color: 'var(--text-color)',
                        transform: 'translate(-10px, 10px)'
                    }"
                    @click.stop>
                    <div class="small text-muted mb-1">
                        {{ newObservation.x }}, {{ newObservation.y }}
                    </div>
                    <input id="obs-input" type="text" v-model="newObservation.text"
                        class="form-control form-control-sm mb-2" :disabled="editingObservationIndex !== null && observations[editingObservationIndex]?.name"
                        :placeholder="__('Enter observation')"
                        @keydown.enter="saveObservation"
                        @keydown.esc="cancelObservation">
                    <div class="d-flex justify-content-end">
                        <button v-if="editingObservationIndex !== null && !observations[editingObservationIndex]?.name"
                            class="btn btn-xs btn-danger mr-auto"
                            @click="deleteObservation">
                            {{ __('Delete') }}
                        </button>
                        <button class="btn btn-xs btn-light mr-1" @click="cancelObservation">{{ __('Cancel') }}</button>
                        <button class="btn btn-xs btn-primary" v-if="editingObservationIndex !== null && !observations[editingObservationIndex]?.name" @click="saveObservation">{{ __('Save') }}</button>
                    </div>
                </div>

            </div>
            <div class="text-center text-muted small mt-2">
                {{ __('Click anywhere on the slab to add an observation point.') }}
            </div>
        </div>
        <div class="col-12 text-center py-5 text-muted" v-else>
            {{ __('Slab dimensions not available for visualization.') }}
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';

const props = defineProps({
    observations: {
        type: Array,
        required: true
    },
    slabSize: {
        type: Object,
        default: null
    },
    observationColour: {
        type: String,
        default: 'red'
    }
});

const emit = defineEmits(['update:observations']);

const newObservation = ref(null);
const hoverCoordinates = ref({ x: 0, y: 0, visible: false });
const slabScale = ref(1); // pixels per mm
const visualizerRef = ref(null);
const editingObservationIndex = ref(null);

watch(() => props.slabSize, () => {
    newObservation.value = null;
    editingObservationIndex.value = null;
});

const getScale = () => {
    if (!visualizerRef.value || !props.slabSize) return 1;
    // Use getBoundingClientRect for precise sub-pixel rendering and zoom handling
    const rect = visualizerRef.value.getBoundingClientRect();
    return rect.width / props.slabSize.length;
};

const updateScale = () => {
    if (visualizerRef.value) {
        slabScale.value = getScale();
    }
};

// Mouse tracking
const handleMouseMove = (event) => {
    if (!visualizerRef.value) return;
    updateScale(); // Ensure scale is always current (handles zoom/resize)
    const rect = visualizerRef.value.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Convert to mm
    const mmX = Math.round(x / slabScale.value);
    const mmY = Math.round(y / slabScale.value);

    // Clamp to slab dimensions
    if (mmX >= 0 && mmX <= props.slabSize.length && mmY >= 0 && mmY <= props.slabSize.breadth) {
        hoverCoordinates.value = { x: mmX, y: mmY, visible: true, clientX: event.clientX, clientY: event.clientY };
    } else {
        hoverCoordinates.value.visible = false;
    }
};

const handleMouseLeave = () => {
    hoverCoordinates.value.visible = false;
};

const handleSlabClick = (event) => {
    if (!visualizerRef.value || newObservation.value) return; // Don't start new if one is open

    // Clear editing state if clicking elsewhere
    editingObservationIndex.value = null;

    const rect = visualizerRef.value.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const mmX = Math.round(x / slabScale.value);
    const mmY = Math.round(y / slabScale.value);

    newObservation.value = {
        x: mmX,
        y: mmY,
        text: ''
    };

    // Auto-focus input next tick
    setTimeout(() => {
        const input = document.getElementById('obs-input');
        if (input) input.focus();
    }, 100);
};

const editObservation = (index) => {
    editingObservationIndex.value = index;
    newObservation.value = { ...props.observations[index] };

    // Auto-focus input next tick
    setTimeout(() => {
        const input = document.getElementById('obs-input');
        if (input) input.focus();
    }, 100);
};

const deleteObservation = () => {
    if (editingObservationIndex.value !== null) {
        if (props.observations[editingObservationIndex.value]?.name) {
            return;
        }

        const newObs = [...props.observations];
        newObs.splice(editingObservationIndex.value, 1);
        emit('update:observations', newObs);
    }

    newObservation.value = null;
    editingObservationIndex.value = null;
};

const saveObservation = () => {
    if (editingObservationIndex.value !== null && props.observations[editingObservationIndex.value]?.name) {
        return;
    }

    if (newObservation.value && newObservation.value.text.trim()) {
        const newObs = [...props.observations];
        if (editingObservationIndex.value !== null) {
            newObs[editingObservationIndex.value] = { ...newObservation.value };
        } else {
            newObs.push({ ...newObservation.value });
        }
        emit('update:observations', newObs);
    }
    newObservation.value = null;
    editingObservationIndex.value = null;
};

const cancelObservation = () => {
    newObservation.value = null;
    editingObservationIndex.value = null;
};

onMounted(() => {
    window.addEventListener('resize', updateScale);
});

onUnmounted(() => {
    window.removeEventListener('resize', updateScale);
});
</script>

<style scoped>
.obs-marker {
    position: absolute;
    width: 0;
    height: 0;
}

.marker-dot {
    width: 12px;
    height: 12px;
    border: 2px solid white;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}


.marker-dot:hover {
    transform: translate(-50%, -50%) scale(1.2);
}

.crosshair-h {
    position: absolute;
    width: 100%;
    height: 1px;
    left: 0;
    border-top: 1px dashed var(--text-color);
    pointer-events: none;
    z-index: 10;
}

.crosshair-v {
    position: absolute;
    height: 100%;
    width: 1px;
    top: 0;
    border-left: 1px dashed var(--text-color);
    pointer-events: none;
    z-index: 10;
}

.crosshair-label {
    position: absolute;
    background: var(--text-color);
    color: var(--card-bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    pointer-events: none;
    z-index: 11;
    white-space: nowrap;
}

.label-x {
    transform: translate(-100%, -50%);
    margin-left: -30px;
}

.label-y {
    transform: translate(-50%, -100%);
    margin-top: -30px;
}
</style>
