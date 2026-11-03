import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { get_meshes, load_model_file, make_material } from "./model_loaders";
import { PlacementLayer } from "./placement_layer";

export class ModelViewer {
	constructor(container, on_pick) {
		this.container = container;
		this.on_pick = on_pick;
		this.meshes = [];

		this.scene = new THREE.Scene();
		this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100000);
		this.camera.add(new THREE.DirectionalLight(0xffffff, 1.5));
		this.scene.add(this.camera, new THREE.HemisphereLight(0xffffff, 0x808080, 2));
		this.model = new THREE.Group();
		this.scene.add(this.model);

		this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
		this.renderer.setPixelRatio(window.devicePixelRatio);
		container.appendChild(this.renderer.domElement);

		this.controls = new OrbitControls(this.camera, this.renderer.domElement);
		this.controls.addEventListener("change", () => this.draw());
		this.placement = new PlacementLayer(this);
		this.bind_pick();

		this.resize_observer = new ResizeObserver(() => this.resize());
		this.resize_observer.observe(container);
	}

	async load(file_url) {
		const group = await load_model_file(file_url);
		for (const mesh of get_meshes(group)) {
			this.model.add(mesh);
			this.meshes.push(mesh);
		}
		this.fit();
	}

	highlight(is_selected) {
		const highlight_color = new THREE.Color(get_css_color("--blue-500"));
		const has_selection = this.meshes.some((mesh) => is_selected(mesh.userData.path));
		for (const mesh of this.meshes) {
			const selected = is_selected(mesh.userData.path);
			mesh.material.color.copy(selected ? highlight_color : mesh.userData.color);
			mesh.material.transparent = has_selection && !selected;
			mesh.material.opacity = has_selection && !selected ? 0.25 : 1;
		}
		this.draw();
	}

	fit() {
		const box = new THREE.Box3().setFromObject(this.model);
		if (box.isEmpty()) return;

		this.controls.target.copy(place_camera(this.camera, box));
		this.controls.update();
	}

	capture(is_selected, { single = false } = {}) {
		const matching = this.meshes.filter((mesh) => is_selected(mesh.userData.path));
		return this.capture_meshes(single ? matching.slice(0, 1) : matching);
	}

	capture_meshes(meshes, size = 512) {
		if (!meshes.length) return null;

		const box = new THREE.Box3();
		meshes.forEach((mesh) => box.expandByObject(mesh));
		const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100000);
		camera.add(new THREE.DirectionalLight(0xffffff, 1.5));
		camera.lookAt(place_camera(camera, box));

		const scene = new THREE.Scene();
		scene.add(camera, new THREE.HemisphereLight(0xffffff, 0x808080, 2));
		const materials = meshes.map((mesh) => make_material(mesh.userData.color));
		meshes.forEach((mesh, index) => scene.add(new THREE.Mesh(mesh.geometry, materials[index])));

		const renderer = this.get_capture_renderer(size);
		renderer.render(scene, camera);
		materials.forEach((material) => material.dispose());
		return get_centered_image(renderer.domElement, size);
	}

	get_capture_renderer(size) {
		this.capture_renderer ??= new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
		this.capture_renderer.setClearColor(0xffffff, 1);
		this.capture_renderer.setSize(size, size);
		return this.capture_renderer;
	}

	bind_pick() {
		const canvas = this.renderer.domElement;
		let start = null;
		canvas.addEventListener("pointerdown", (event) => (start = [event.clientX, event.clientY]));
		canvas.addEventListener("pointerup", (event) => {
			const moved = start && Math.hypot(event.clientX - start[0], event.clientY - start[1]);
			if (moved !== null && moved < 4) this.pick(event);
		});
	}

	pick(event) {
		if (this.placement.is_using_handles) return;

		const bounds = this.renderer.domElement.getBoundingClientRect();
		const pointer = new THREE.Vector2(
			((event.clientX - bounds.left) / bounds.width) * 2 - 1,
			-((event.clientY - bounds.top) / bounds.height) * 2 + 1
		);
		const raycaster = new THREE.Raycaster();
		raycaster.setFromCamera(pointer, this.camera);
		const opaque = this.meshes.filter((mesh) => !mesh.material.transparent);

		if (this.on_place) {
			const [hit] = raycaster.intersectObjects([...opaque, ...this.placement.objects], true);
			if (hit) this.on_place(hit);
			return;
		}

		const added = this.placement.pick(raycaster);
		if (added) {
			this.on_pick_added?.(added);
			return;
		}

		const [hit] = raycaster.intersectObjects(opaque);
		this.on_pick(hit ? hit.object.userData.path : null);
	}

	resize() {
		const { clientWidth, clientHeight } = this.container;
		if (!clientWidth || !clientHeight) return;

		this.renderer.setSize(clientWidth, clientHeight);
		this.camera.aspect = clientWidth / clientHeight;
		this.camera.updateProjectionMatrix();
		this.draw();
	}

	draw() {
		if (this.frame) return;

		this.frame = requestAnimationFrame(() => {
			this.frame = null;
			this.renderer.render(this.scene, this.camera);
		});
	}

	destroy() {
		cancelAnimationFrame(this.frame);
		this.resize_observer.disconnect();
		this.controls.dispose();
		this.placement.dispose();
		for (const mesh of this.meshes) {
			mesh.geometry.dispose();
			mesh.material.dispose();
		}
		this.renderer.dispose();
		this.capture_renderer?.dispose();
		this.renderer.domElement.remove();
	}
}

function place_camera(camera, box) {
	const center = box.getCenter(new THREE.Vector3());
	const radius = box.getSize(new THREE.Vector3()).length() / 2 || 1;
	const half_fov = THREE.MathUtils.degToRad(camera.fov / 2);
	const half_view = Math.min(half_fov, Math.atan(Math.tan(half_fov) * camera.aspect));
	const distance = radius / Math.sin(half_view);
	camera.position.copy(center).add(new THREE.Vector3(1, 0.8, 1).normalize().multiplyScalar(distance));
	camera.near = distance / 100;
	camera.far = distance * 100;
	camera.updateProjectionMatrix();
	return center;
}

function get_centered_image(source, size, margin = 0.1) {
	const canvas = document.createElement("canvas");
	canvas.width = canvas.height = size;
	const context = canvas.getContext("2d", { willReadFrequently: true });
	context.drawImage(source, 0, 0, size, size);
	const bounds = get_drawn_bounds(context.getImageData(0, 0, size, size));
	if (!bounds) return canvas.toDataURL("image/png");

	const scale = (size * (1 - 2 * margin)) / Math.max(bounds.width, bounds.height);
	const [width, height] = [bounds.width * scale, bounds.height * scale];
	context.fillStyle = "#fff";
	context.fillRect(0, 0, size, size);
	context.drawImage(
		source,
		bounds.x,
		bounds.y,
		bounds.width,
		bounds.height,
		(size - width) / 2,
		(size - height) / 2,
		width,
		height
	);
	return canvas.toDataURL("image/png");
}

function get_drawn_bounds({ data, width, height }) {
	let [left, top, right, bottom] = [width, height, -1, -1];
	for (let y = 0; y < height; y++) {
		for (let x = 0; x < width; x++) {
			const index = (y * width + x) * 4;
			if (Math.min(data[index], data[index + 1], data[index + 2]) > 245) continue;
			[left, top, right, bottom] = [
				Math.min(left, x),
				Math.min(top, y),
				Math.max(right, x),
				Math.max(bottom, y),
			];
		}
	}
	return right < 0 ? null : { x: left, y: top, width: right - left + 1, height: bottom - top + 1 };
}

function get_css_color(variable) {
	return getComputedStyle(document.body).getPropertyValue(variable).trim() || "#2490ef";
}
