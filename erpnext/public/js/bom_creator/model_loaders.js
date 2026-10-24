import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

const STEP_READER_PATH = "/assets/erpnext/dist/occt-import-js/";
const DEFAULT_COLOR = 0xb4bcc4;
let step_reader;

export async function load_model_file(file_url) {
	const extension = file_url.split("?")[0].split(".").pop().toLowerCase();
	const buffer = await fetch_file(file_url);
	if (extension === "stl") return make_group([make_mesh(read_stl(buffer), null, [""])]);
	if (extension === "glb") return read_gltf(buffer);
	return read_step(buffer);
}

export function make_material(color) {
	return new THREE.MeshStandardMaterial({ color, metalness: 0.1, roughness: 0.6, side: THREE.DoubleSide });
}

export function get_meshes(object) {
	const meshes = [];
	object.traverse((child) => child.isMesh && meshes.push(child));
	return meshes;
}

function make_mesh(geometry, rgb, path) {
	const color = rgb ? new THREE.Color(...rgb) : new THREE.Color(DEFAULT_COLOR);
	const mesh = new THREE.Mesh(geometry, make_material(color));
	mesh.userData = { path, color };
	return mesh;
}

function make_group(meshes) {
	const group = new THREE.Group();
	meshes.forEach((mesh) => group.add(mesh));
	return group;
}

async function read_step(buffer) {
	const reader = await get_step_reader();
	const result = reader.ReadStepFile(new Uint8Array(buffer), null);
	if (!result.success) {
		throw new Error(__("The STEP file could not be read."));
	}

	const meshes = [];
	add_step_node(result.root, result.meshes, [], meshes);
	return make_group(meshes);
}

function add_step_node(node, step_meshes, parent_path, meshes) {
	const path = [...parent_path, (node.name || "").trim()];
	for (const index of node.meshes) {
		const data = step_meshes[index];
		meshes.push(make_mesh(make_step_geometry(data), data.color, [...path, (data.name || "").trim()]));
	}
	node.children.forEach((child) => add_step_node(child, step_meshes, path, meshes));
}

function make_step_geometry(data) {
	const geometry = new THREE.BufferGeometry();
	geometry.setAttribute("position", new THREE.Float32BufferAttribute(data.attributes.position.array, 3));
	geometry.setIndex(data.index.array);
	if (data.attributes.normal) {
		geometry.setAttribute("normal", new THREE.Float32BufferAttribute(data.attributes.normal.array, 3));
	} else {
		geometry.computeVertexNormals();
	}
	return geometry;
}

function read_stl(buffer) {
	const geometry = new STLLoader().parse(buffer);
	if (!geometry.getAttribute("normal")) geometry.computeVertexNormals();
	return geometry;
}

async function read_gltf(buffer) {
	const gltf = await new GLTFLoader().parseAsync(buffer, "");
	gltf.scene.updateMatrixWorld(true);
	const meshes = get_meshes(gltf.scene).map((object) => {
		const color = object.material?.color;
		const geometry = object.geometry.clone().applyMatrix4(object.matrixWorld);
		return make_mesh(geometry, color ? [color.r, color.g, color.b] : null, [object.name || ""]);
	});
	return make_group(meshes);
}

function get_step_reader() {
	step_reader ??= new Promise((resolve, reject) => {
		const script = document.createElement("script");
		script.src = `${STEP_READER_PATH}occt-import-js.js`;
		script.onload = () =>
			window.occtimportjs({ locateFile: (name) => STEP_READER_PATH + name }).then(resolve, reject);
		script.onerror = () => {
			step_reader = null;
			reject(new Error(__("The 3D viewer files are missing. Run yarn install for ERPNext.")));
		};
		document.head.appendChild(script);
	});
	return step_reader;
}

async function fetch_file(file_url) {
	const response = await fetch(file_url);
	if (!response.ok) {
		throw new Error(__("The 3D file could not be loaded."));
	}
	return response.arrayBuffer();
}
