import * as THREE from "three";
import { TransformControls } from "three/examples/jsm/controls/TransformControls.js";
import { get_meshes, load_model_file } from "./model_loaders";

const OUTLINE_COLOR = 0xf59e0b;
const outlines = new WeakMap();

export class PlacementLayer {
	constructor(viewer) {
		this.viewer = viewer;
		this.templates = new Map();
		this.objects = [];
		this.group = new THREE.Group();
		viewer.scene.add(this.group);

		this.controls = new TransformControls(viewer.camera, viewer.renderer.domElement);
		this.controls.addEventListener(
			"dragging-changed",
			(event) => (viewer.controls.enabled = !event.value)
		);
		this.controls.addEventListener("change", () => viewer.draw());
		this.controls.addEventListener("mouseUp", () => this.on_change?.(this.controls.object));
		viewer.scene.add(this.controls.getHelper());
	}

	get is_using_handles() {
		return Boolean(this.controls.object && this.controls.axis);
	}

	get_template(file_url) {
		if (!this.templates.has(file_url)) this.templates.set(file_url, load_model_file(file_url));
		return this.templates.get(file_url);
	}

	get_key(parts) {
		return JSON.stringify(parts);
	}

	async sync(parts) {
		const key = this.get_key(parts);
		if (key === this.key) return;
		this.key = key;

		const objects = [];
		for (const part of parts) {
			const template = await this.get_template(part.model_file);
			part.placements.forEach((placement, index) =>
				objects.push(this.make_object(template, part.node_id, index, placement))
			);
		}
		if (key !== this.key) return;

		this.clear();
		objects.forEach((object) => this.group.add(object));
		this.objects = objects;
		this.viewer.draw();
	}

	make_object(template, node_id, index, placement) {
		const object = template.clone(true);
		for (const mesh of get_meshes(object)) {
			if (!outlines.has(mesh.geometry))
				outlines.set(mesh.geometry, new THREE.EdgesGeometry(mesh.geometry, 30));
			mesh.add(
				new THREE.LineSegments(
					outlines.get(mesh.geometry),
					new THREE.LineBasicMaterial({ color: OUTLINE_COLOR })
				)
			);
		}
		object.position.fromArray(placement.position);
		object.quaternion.fromArray(placement.quaternion || [0, 0, 0, 1]);
		object.userData = { node_id, index };
		return object;
	}

	async get_drop_placement(file_url, hit) {
		const box = new THREE.Box3().setFromObject(await this.get_template(file_url));
		const size = box.getSize(new THREE.Vector3());
		const normal = hit.face
			? hit.face.normal.clone().transformDirection(hit.object.matrixWorld)
			: new THREE.Vector3(0, 1, 0);
		const depth = Math.abs(size.x * normal.x) + Math.abs(size.y * normal.y) + Math.abs(size.z * normal.z);
		const position = hit.point
			.clone()
			.sub(box.getCenter(new THREE.Vector3()))
			.add(normal.multiplyScalar(depth / 2));
		return { position: position.toArray(), quaternion: [0, 0, 0, 1] };
	}

	get_placement(object) {
		return { position: object.position.toArray(), quaternion: object.quaternion.toArray() };
	}

	find(node_id, index) {
		return this.objects.find(
			(object) => object.userData.node_id === node_id && object.userData.index === index
		);
	}

	pick(raycaster) {
		const [hit] = raycaster.intersectObjects(this.objects, true);
		let object = hit?.object;
		while (object && object.userData.node_id === undefined) object = object.parent;
		return object || null;
	}

	select(object) {
		object ? this.controls.attach(object) : this.controls.detach();
		this.viewer.draw();
	}

	set_mode(mode) {
		this.controls.setMode(mode);
	}

	async get_template_meshes(file_url) {
		return get_meshes(await this.get_template(file_url));
	}

	clear() {
		this.controls.detach();
		this.objects.forEach((object) => this.group.remove(object));
		this.objects = [];
	}

	dispose() {
		this.clear();
		this.controls.dispose();
	}
}
