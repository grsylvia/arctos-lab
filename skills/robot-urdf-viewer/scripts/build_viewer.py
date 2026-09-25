#!/usr/bin/env python3
"""Build an offline, simplified robot viewer from expanded URDF (stdlib only)."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET


def numbers(text, count):
    values = [float(x) for x in text.split()]
    if len(values) != count or not all(math.isfinite(x) for x in values):
        raise ValueError(f"Expected {count} finite numbers: {text!r}")
    return values


def scalar(text):
    return numbers(text, 1)[0]


def name(text):
    if not text or not re.fullmatch(r"[\w./:\-]+", text):
        raise ValueError(f"Invalid link/joint identifier: {text!r}")
    return text


def origin(element):
    item = element.find("origin")
    return {
        key: numbers(item.get(key, "0 0 0") if item is not None else "0 0 0", 3)
        for key in ("xyz", "rpy")
    }


def resolve_mesh(uri, source, packages):
    if uri.startswith("package://"):
        package, sep, relative = uri[10:].partition("/")
        if not sep:
            raise ValueError(f"Invalid mesh URI: {uri}")
        if package in packages:
            return packages[package] / relative
        for prefix in os.environ.get("AMENT_PREFIX_PATH", "").split(os.pathsep):
            if prefix:
                candidate = Path(prefix) / "share" / package / relative
                if candidate.is_file():
                    return candidate
        for ancestor in source.parents:
            for candidate in (ancestor / relative if ancestor.name == package else None,
                              ancestor / package / relative,
                              ancestor / "src" / package / relative):
                if candidate is not None and candidate.is_file():
                    return candidate
        raise ValueError(f"Cannot resolve {uri}; supply --package {package}=/path/to/{package}")
    if uri.startswith("file://"):
        return Path(uri[7:])
    if "://" in uri:
        raise ValueError(f"Only local mesh files are supported: {uri}")
    path = Path(uri)
    return path if path.is_absolute() else source.parent / path


def mesh_bounds(path, scale):
    """Read vertices locally; only the resulting box enters the viewer."""
    data = path.read_bytes()
    vertices = []
    if path.suffix.lower() == ".stl":
        count = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0
        if len(data) == 84 + count * 50:
            for offset in range(84, len(data), 50):
                vertices.extend(struct.unpack_from("<3f", data, offset + 12 + i * 12) for i in range(3))
        else:
            for line in data.decode("ascii").splitlines():
                fields = line.split()
                if fields and fields[0] == "vertex":
                    vertices.append(numbers(" ".join(fields[1:]), 3))
    elif path.suffix.lower() == ".obj":
        for line in data.decode("utf-8").splitlines():
            fields = line.split()
            if fields and fields[0] == "v":
                vertices.append(numbers(" ".join(fields[1:4]), 3))
    else:
        raise ValueError(f"Unsupported mesh format {path.suffix}; bounding boxes support STL and OBJ")
    if not vertices or not all(math.isfinite(v) for p in vertices for v in p):
        raise ValueError(f"No finite mesh vertices in {path.name}")
    lo = [min(p[i] * scale[i] for p in vertices) for i in range(3)]
    hi = [max(p[i] * scale[i] for p in vertices) for i in range(3)]
    return {"box": [max(b - a, 1e-6) for a, b in zip(lo, hi)],
            "center": [(a + b) / 2 for a, b in zip(lo, hi)]}


def convert(source, packages=None, tip=None, tip_at=None, strict_meshes=False):
    source = Path(source).resolve()
    robot = ET.parse(source).getroot()
    if robot.tag != "robot":
        raise ValueError("Input must have a <robot> root")
    if any("xacro" in e.tag for e in robot.iter()) or "${" in ET.tostring(robot, encoding="unicode"):
        raise ValueError("Expand Xacro first: xacro robot.urdf.xacro -o /tmp/robot.urdf")
    model = {"name": robot.get("name", source.stem), "source": {"kind": "urdf", "file": source.name},
             "links": {}, "joints": [], "warnings": []}
    materials = {}
    for material in robot.findall("material"):
        color = material.find("color")
        if color is not None:
            materials[material.get("name")] = numbers(color.get("rgba", "0.6 0.6 0.6 1"), 4)[:3]
    for link in robot.findall("link"):
        key = name(link.get("name"))
        if key in model["links"]:
            raise ValueError(f"Duplicate link: {key}")
        blocks = []
        for visual in link.findall("visual"):
            geometry = visual.find("geometry")
            if geometry is None or len(geometry) != 1:
                raise ValueError(f"{key}: visual needs one geometry")
            shape = geometry[0]
            pose = origin(visual)
            block = {"at": pose["xyz"], "rpy": pose["rpy"]}
            if shape.tag == "box":
                block["box"] = numbers(shape.get("size", ""), 3)
            elif shape.tag == "cylinder":
                block["cyl"] = [scalar(shape.get("radius", "")), scalar(shape.get("length", ""))]
            elif shape.tag == "sphere":
                block["sphere"] = scalar(shape.get("radius", ""))
            elif shape.tag == "mesh":
                try:
                    mesh = resolve_mesh(shape.get("filename", ""), source, packages or {})
                    block.update(mesh_bounds(mesh, numbers(shape.get("scale", "1 1 1"), 3)))
                except (OSError, ValueError, UnicodeError, struct.error) as exc:
                    if strict_meshes:
                        raise ValueError(f"{key}: {exc}") from exc
                    model["warnings"].append(f"{key}: mesh omitted. {exc}")
                    continue
            else:
                raise ValueError(f"{key}: unsupported geometry {shape.tag}")
            dimensions = block.get("box", block.get("cyl", [block.get("sphere", 1)]))
            if any(d <= 0 for d in dimensions):
                raise ValueError(f"{key}: geometry dimensions must be positive")
            material = visual.find("material")
            if material is not None:
                color = material.find("color")
                rgb = (numbers(color.get("rgba", ""), 4)[:3] if color is not None
                       else materials.get(material.get("name")))
                if rgb is not None:
                    block["color"] = rgb
            blocks.append(block)
        model["links"][key] = {"blocks": blocks}
        if not blocks:
            model["warnings"].append(f"{key}: no usable visual; showing a frame connector.")
    if not model["links"]:
        raise ValueError("Robot has no links")
    by_name, parents, children = {}, {}, {}
    for item in robot.findall("joint"):
        key, kind = name(item.get("name")), item.get("type")
        if key in by_name:
            raise ValueError(f"Duplicate joint: {key}")
        if kind not in {"fixed", "revolute", "continuous", "prismatic"}:
            raise ValueError(f"{key}: unsupported joint type {kind}; use fixed, revolute, continuous or prismatic")
        if item.find("parent") is None or item.find("child") is None:
            raise ValueError(f"{key}: missing parent or child")
        parent, child = name(item.find("parent").get("link")), name(item.find("child").get("link"))
        if parent not in model["links"] or child not in model["links"]:
            raise ValueError(f"{key}: parent or child is not a declared link")
        if child in parents:
            raise ValueError(f"{child}: multiple parent joints")
        parents[child] = parent
        children.setdefault(parent, []).append(child)
        joint = dict(name=key, type=kind, parent=parent, child=child, **origin(item))
        if kind != "fixed":
            axis = item.find("axis")
            joint["axis"] = numbers(axis.get("xyz", "1 0 0") if axis is not None else "1 0 0", 3)
            if math.hypot(*joint["axis"]) == 0:
                raise ValueError(f"{key}: axis must be nonzero")
            limit = item.find("limit")
            if kind == "continuous":
                joint.update(lower=-math.pi, upper=math.pi)
            else:
                if limit is None or any(k not in limit.attrib for k in ("lower", "upper")):
                    raise ValueError(f"{key}: explicit lower and upper limits are required")
                joint.update({k: scalar(limit.get(k)) for k in ("lower", "upper")})
                if joint["lower"] > joint["upper"]:
                    raise ValueError(f"{key}: lower limit exceeds upper limit")
            if limit is not None:
                for field in ("velocity", "effort"):
                    if field in limit.attrib:
                        joint[field] = scalar(limit.get(field))
            mimic = item.find("mimic")
            if mimic is not None:
                joint["mimic"] = {"joint": name(mimic.get("joint")),
                                  "multiplier": scalar(mimic.get("multiplier", "1")),
                                  "offset": scalar(mimic.get("offset", "0"))}
        by_name[key] = joint
        model["joints"].append(joint)
    roots = set(model["links"]) - set(parents)
    if len(roots) != 1:
        raise ValueError("URDF must form one connected tree with one root")
    model["root"] = roots.pop()
    queue, visited, depths = [model["root"]], set(), {model["root"]: 0}
    while queue:
        link = queue.pop()
        if link in visited:
            raise ValueError("Cycle in link tree")
        visited.add(link)
        for child in children.get(link, []):
            depths[child] = depths[link] + 1
            queue.append(child)
    if visited != set(model["links"]):
        raise ValueError("Disconnected links or a cycle in the URDF")
    for joint in model["joints"]:
        current, seen = joint, set()
        while "mimic" in current:
            if current["name"] in seen:
                raise ValueError(f"{joint['name']}: cyclic mimic relationship")
            seen.add(current["name"])
            target = current["mimic"]["joint"]
            if target not in by_name or by_name[target]["type"] == "fixed":
                raise ValueError(f"{joint['name']}: missing or fixed mimic source {target}")
            current = by_name[target]
    if tip is not None and tip not in model["links"]:
        raise ValueError(f"Unknown tip link: {tip}")
    chosen = tip or max(depths, key=depths.get)
    model["tip"] = {"link": chosen, "at": tip_at or [0, 0, 0]}
    if tip is None:
        model["warnings"].append(f"Tip marker uses {chosen}'s origin; set --tip and --tip-at to override.")
    return model


def render(model, output):
    template = Path(__file__).resolve().parents[1] / "assets" / "viewer.html"
    encoded = json.dumps(model, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    # Prevent URDF strings from terminating the JSON script element.
    encoded = encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = template.read_text().replace("__ROBOT_MODEL__", encoded)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urdf", type=Path, help="Expanded URDF file")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--package", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--tip", help="Link for the tip marker and optional trail")
    parser.add_argument("--tip-at", nargs=3, type=float, default=[0, 0, 0], metavar=("X", "Y", "Z"))
    parser.add_argument("--strict-meshes", action="store_true", help="Fail instead of omitting unresolved/unsupported meshes")
    args = parser.parse_args()
    try:
        if args.output.resolve() == args.urdf.resolve():
            raise ValueError("Output must differ from the source URDF")
        packages = {}
        for mapping in args.package:
            key, sep, value = mapping.partition("=")
            if not sep or not key or not value:
                raise ValueError("--package must be NAME=PATH")
            packages[key] = Path(value).expanduser().resolve()
        if not all(math.isfinite(v) for v in args.tip_at):
            raise ValueError("Tip coordinates must be finite")
        model = convert(args.urdf, packages, args.tip, args.tip_at, args.strict_meshes)
        render(model, args.output)
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.exit(2, f"error: {exc}\n")
    for warning in model["warnings"]:
        print(f"note: {warning}", file=sys.stderr)
    print(f"Built {args.output} ({len(model['links'])} links, {len(model['joints'])} joints)")


if __name__ == "__main__":
    main()
