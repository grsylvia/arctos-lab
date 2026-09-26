#!/usr/bin/env python3
"""Compute joint limits: nearest CAD collision angle divided by a factor of safety."""
import argparse
import itertools
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial import cKDTree

# Limit rule. Mesh units are millimetres.
FACTOR_OF_SAFETY = 1.5
TABLE_Z_MM = 0.0  # base_link bottom plane
FREE_LIMIT_RAD = math.pi  # used when nothing collides within a full turn

# Sweep resolution.
SWEEP_STEP_DEG = 1.0
SWEEP_MAX_DEG = 360.0
REFINE_DEG = 0.1
GRID_STEP_DEG = 45.0  # maximum spacing of downstream joint samples

# Contact detection.
DENSITY_PER_MM2 = 1.0  # surface samples per mm²
PENETRATION_MM = 1.0  # depth inside another link that counts as contact
SEARCH_MM = 3.0
NEIGHBOURS = 4  # all must agree a point is inside, so sharp edges do not flip the sign
MIN_POINTS = 20  # CAD interference fits reach about 7 penetrating points
CLEARANCE_MM = 0.5  # points this close at the zero pose are joint interfaces, ignored
OVERLAP_SEARCH_MM = 20.0

STL_DTYPE = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])


def transform(t, points):
    """Apply 4x4 transforms to points; either may carry leading batch dimensions."""
    return points @ np.swapaxes(t[..., :3, :3], -1, -2) + t[..., :3, 3]


def rotation(axis, angle):
    """4x4 rotation about a unit axis (Rodrigues' formula)."""
    x, y, z = axis
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    t = np.eye(4)
    t[:3, :3] = np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * k @ k
    return t


def translation(xyz):
    t = np.eye(4)
    t[:3, 3] = xyz
    return t


def read_joint(element):
    """Read one URDF joint, converting metres to millimetres."""
    origin = {} if element.find('origin') is None else element.find('origin').attrib
    xyz = [1000 * float(v) for v in origin.get('xyz', '0 0 0').split()]
    roll, pitch, yaw = (float(v) for v in origin.get('rpy', '0 0 0').split())
    # URDF fixed-axis order: roll about X, then pitch about Y, then yaw about Z.
    rpy = rotation((0, 0, 1), yaw) @ rotation((0, 1, 0), pitch) @ rotation((1, 0, 0), roll)
    axis = '1 0 0' if element.find('axis') is None else element.find('axis').get('xyz')
    return {
        'name': element.get('name'),
        'movable': element.get('type') in ('revolute', 'continuous'),
        'parent': element.find('parent').get('link'),
        'child': element.find('child').get('link'),
        'origin': translation(xyz) @ rpy,
        'axis': [float(v) for v in axis.split()],
    }


class Link:
    """One link's sampled surface, in its own frame."""

    def __init__(self, path, rng):
        triangles = np.frombuffer(path.read_bytes(), dtype=STL_DTYPE, offset=84)['vertices'].astype(float)
        # Winding normals point outward for these meshes.
        cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        area = np.linalg.norm(cross, axis=1) / 2
        triangles, cross, area = triangles[area > 0], cross[area > 0], area[area > 0]
        counts = np.maximum(1, np.round(area * DENSITY_PER_MM2).astype(int))
        corners = np.repeat(triangles, counts, axis=0)
        u, v = rng.random((2, len(corners), 1))
        # Fold barycentric samples outside the triangle back inside it.
        u, v = np.where(u + v > 1, 1 - u, u), np.where(u + v > 1, 1 - v, v)
        self.points = corners[:, 0] + u * (corners[:, 1] - corners[:, 0]) + v * (corners[:, 2] - corners[:, 0])
        self.normals = np.repeat(cross / (2 * area[:, None]), counts, axis=0)
        self.tree = cKDTree(self.points)
        self.low, self.high = self.points.min(0) - SEARCH_MM, self.points.max(0) + SEARCH_MM
        self.centre = (self.low + self.high) / 2
        self.radius = np.linalg.norm(self.points - self.centre, axis=1).max()

    def depth(self, points, search):
        """Distance outside this surface: negative inside, infinite beyond the search."""
        distance, index = self.tree.query(points, k=NEIGHBOURS, distance_upper_bound=search)
        found = distance < np.inf
        index = np.where(found, index, 0)
        signed = np.einsum('ijk,ijk->ij', points[:, None] - self.points[index], self.normals[index])
        deepest = np.where(found, signed, -np.inf).max(1)
        return np.where(found.any(1), deepest, np.inf)

    def penetrated_by(self, points):
        points = points[np.all((points > self.low) & (points < self.high), axis=1)]
        return np.sum(self.depth(points, SEARCH_MM) < -PENETRATION_MM) >= MIN_POINTS


class Robot:
    """The URDF chain with sampled link meshes; joints must be listed base to tip."""

    def __init__(self, urdf, mesh_dir):
        root = ET.parse(urdf).getroot()
        self.joints = [read_joint(element) for element in root.findall('joint')]
        self.joint = {j['name']: j for j in self.joints}
        self.above = {j['child']: j for j in self.joints}
        self.root = self.joints[0]['parent']
        # Seeded so repeated runs give the same limits.
        rng = np.random.default_rng(0)
        self.links = {}
        for element in root.findall('link'):
            mesh = element.find('visual/geometry/mesh')
            if mesh is not None:
                # Map the package:// URI to the local mesh directory by file name.
                self.links[element.get('name')] = Link(Path(mesh_dir) / Path(mesh.get('filename')).name, rng)
        # Per ordered link pair: mask of points that start clear of the other link.
        self.clear = {}

    def path(self, link):
        """Joints from the root down to a link."""
        joints = []
        while link != self.root:
            joints.insert(0, self.above[link])
            link = self.above[link]['parent']
        return joints

    def carries(self, swept, link):
        return any(j['name'] == swept for j in self.path(link))

    def joints_below(self, swept, link):
        """Movable joints between a swept joint and a link it carries."""
        names = [j['name'] for j in self.path(link) if j['movable']]
        return names[names.index(swept) + 1:]

    def poses(self, angles):
        """Link poses in the base frame for a map of joint angles; missing joints are zero."""
        pose = {self.root: np.eye(4)}
        for j in self.joints:
            turn = rotation(j['axis'], angles.get(j['name'], 0.0)) if j['movable'] else np.eye(4)
            pose[j['child']] = pose[j['parent']] @ j['origin'] @ turn
        return pose

    def penetrates(self, a, b, pose_a, pose_b):
        """Whether link b's points, clear at the zero pose, now penetrate link a."""
        if (a, b) not in self.clear:
            zero = self.poses({})
            points = transform(np.linalg.inv(zero[a]) @ zero[b], self.links[b].points)
            # Excludes joint interfaces and CAD overlaps present at the zero pose.
            self.clear[(a, b)] = self.links[a].depth(points, OVERLAP_SEARCH_MM) >= CLEARANCE_MM
        clear = self.links[b].points[self.clear[(a, b)]]
        return self.links[a].penetrated_by(transform(np.linalg.inv(pose_a) @ pose_b, clear))

    def layout(self, swept, grids):
        """Per moving link: downstream joint combinations and poses relative to the swept joint's child."""
        child = self.joint[swept]['child']
        entries = []
        for link in (link for link in self.links if self.carries(swept, link)):
            names = self.joints_below(swept, link)
            # Joints without computed limits yet stay at zero.
            samples = [grids.get(name, [0.0]) for name in names]
            combos = [dict(zip(names, values)) for values in itertools.product(*samples)]
            relative = np.array([np.linalg.inv(p[child]) @ p[link] for p in map(self.poses, combos)])
            entries.append((link, combos, relative))
        return entries

    def collision(self, swept, angle, layout):
        """First collision at a swept angle as (description, downstream angles), or None."""
        pose = self.poses({swept: angle})
        still = [link for link in self.links if not self.carries(swept, link)]
        for link, combos, relative in layout:
            poses = pose[self.joint[swept]['child']] @ relative
            for i in self.candidates(link, poses, still, pose):
                if np.any(transform(poses[i], self.links[link].points)[:, 2] < TABLE_Z_MM):
                    return f'{link} × table', combos[i]
                for other in still:
                    # Test both directions for coverage.
                    if (self.penetrates(other, link, pose[other], poses[i])
                            or self.penetrates(link, other, poses[i], pose[other])):
                        return f'{link} × {other}', combos[i]
        return None

    def candidates(self, link, poses, still, pose):
        """Indices of poses whose bounding sphere reaches the table or a still link's sphere."""
        body = self.links[link]
        centres = transform(poses, body.centre)
        reach = centres[:, 2] - body.radius < TABLE_Z_MM
        for other in still:
            centre = transform(pose[other], self.links[other].centre)
            reach |= np.linalg.norm(centres - centre, axis=1) < body.radius + self.links[other].radius + SEARCH_MM
        return np.flatnonzero(reach)


def sweep(robot, swept, sign, grids):
    """Sweep one direction; return the signed collision angle in degrees and its cause, or None."""
    layout = robot.layout(swept, grids)

    def hit(deg):
        return robot.collision(swept, sign * math.radians(deg), layout)

    for step in np.arange(1, round(SWEEP_MAX_DEG / SWEEP_STEP_DEG) + 1) * SWEEP_STEP_DEG:
        if cause := hit(step):
            # Bisect between the last clear step and this one.
            clear = step - SWEEP_STEP_DEG
            while step - clear > REFINE_DEG:
                middle = (clear + step) / 2
                if found := hit(middle):
                    step, cause = middle, found
                else:
                    clear = middle
            return sign * step, cause
    return None, None


def grid(lower, upper):
    """Sample a joint range at most GRID_STEP_DEG apart, including zero and both limits."""
    count = max(1, math.ceil(math.degrees(upper - lower) / GRID_STEP_DEG))
    values = set(np.linspace(lower, upper, count + 1).tolist()) | {0.0}
    # A full turn's upper end repeats the lower end.
    if upper - lower >= 2 * math.pi - 1e-6:
        values.discard(upper)
    return sorted(values)


def rounded(angles):
    return {name: round(value, 3) for name, value in angles.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--urdf', type=Path, required=True, help='Path to arctos.urdf')
    parser.add_argument('--mesh-dir', type=Path, required=True, help='Directory with the prepared link STLs')
    args = parser.parse_args()
    robot = Robot(args.urdf, args.mesh_dir)
    grids = {}
    rows = []
    # Sweep tip to base so downstream limits exist before upstream sweeps.
    for name in reversed([j['name'] for j in robot.joints if j['movable']]):
        limits = []
        for sign in (-1, 1):
            angle, cause = sweep(robot, name, sign, grids)
            limits.append(sign * FREE_LIMIT_RAD if angle is None else math.radians(angle) / FACTOR_OF_SAFETY)
            rows.append((name, angle, limits[-1], cause))
            print(f'{name} {"+" if sign > 0 else "-"} done', flush=True)
        grids[name] = grid(*limits)
    print(f'\n{"joint":8} {"collision°":>10} {"limit rad":>10} {"limit°":>7}  cause (downstream rad)')
    for name, angle, limit, cause in sorted(rows, key=lambda row: (row[0], row[2])):
        text = f'none within {SWEEP_MAX_DEG:.0f}°' if cause is None else f'{cause[0]} {rounded(cause[1])}'
        shown = '—' if angle is None else f'{angle:.1f}'
        print(f'{name:8} {shown:>10} {limit:10.6f} {math.degrees(limit):7.1f}  {text}')


if __name__ == '__main__':
    main()
