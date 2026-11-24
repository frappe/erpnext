import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

const TEMPLATE = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../manufacturing/doctype/bom/bom_item_preview.html"
);

const ESCAPE_MAP = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
  "`": "&#x60;",
  "=": "&#x3D;",
};
const escape_html = (text) =>
  text == null
    ? ""
    : String(text).replace(/[&<>"'`=]/g, (char) => ESCAPE_MAP[char]);
const unescape_html = (text) =>
  Object.entries(ESCAPE_MAP).reduce(
    (value, [char, entity]) => value.split(entity).join(char),
    text
  );

const frappe = {
  utils: {
    escape_html,
    bold: (text) => `<strong>${escape_html(text ?? "")}</strong>`,
  },
};
const __ = (message, args = []) =>
  message.replace(/{(\d+)}/g, (_, index) => args[index]);

function render(data) {
  const body = fs
    .readFileSync(TEMPLATE, "utf8")
    .split(/({{[\s\S]*?}}|{%[\s\S]*?%})/)
    .map((part) => {
      if (part.startsWith("{{")) return `out.push(${part.slice(2, -2)});`;
      if (!part.startsWith("{%")) return `out.push(${JSON.stringify(part)});`;
      const tag = part.slice(2, -2).trim();
      return tag === "endif" ? "}" : `if (${tag.replace(/^if\s+/, "")}) {`;
    })
    .join("\n");
  return new Function(
    "data",
    "__",
    "frappe",
    `const out = [];\n${body}\nreturn out.join("");`
  )(data, __, frappe);
}

function attributes(tag) {
  return [...tag.matchAll(/\s([\w-]+)(?:=("[^"]*"|'[^']*'|[^\s>]+))?/g)].map(
    ([, name, value = ""]) => [
      name,
      unescape_html(value.replace(/^["']|["']$/g, "")),
    ]
  );
}

describe("BOM tree preview", () => {
  const image = '/files/frame" data-marker="1.png';
  const html = render({
    image,
    description: "Frame",
    value: "BOM-<i>Frame</i>-001",
    item_code: "Frame <i>Steel</i>",
  });

  it("keeps the image path inside the src attribute", () => {
    const tag = html.match(/<img[^>]*>/)[0];
    assert.deepEqual(
      attributes(tag).map(([name]) => name),
      ["class", "style", "src"]
    );
    assert.equal(Object.fromEntries(attributes(tag)).src, image);
  });

  it("shows the BOM and Item names in the buttons as text", () => {
    assert.ok(!html.includes("<i>"));
    assert.ok(
      html.includes(
        "Open BOM <strong>BOM-&lt;i&gt;Frame&lt;/i&gt;-001</strong>"
      )
    );
    assert.ok(
      html.includes("Open Item <strong>Frame &lt;i&gt;Steel&lt;/i&gt;</strong>")
    );
  });

  it("shows no image when the item has none", () => {
    assert.ok(
      !render({ image: null, value: "BOM-001", item_code: "Frame" }).includes(
        "<img"
      )
    );
  });
});
