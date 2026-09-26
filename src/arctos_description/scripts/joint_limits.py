#!/usr/bin/env python3
"""Compute joint limits: nearest CAD collision angle divided by a factor of safety."""

# Parse the URDF and mesh directory arguments.
import argparse
# Combine downstream joint samples for the worst-case search.
import itertools
# Convert between degrees and radians.
import math
# Resolve local mesh files by name.
from pathlib import Path
# Read joint and link definitions from the URDF.
import xml.etree.ElementTree as ET

# Use arrays for mesh sampling and transforms.
import numpy as np
# Find nearby surface points between link meshes.
from scipy.spatial import cKDTree

# Limit rule: divide each nearest collision angle by this factor of safety.
FACTOR_OF_SAFETY = 1.5
# Limit rule: treat the base_link bottom plane (z = 0 mm) as the table.
TABLE_Z_MM = 0.0
# Limit rule: allow a half turn each way when nothing collides within a full turn.
FREE_LIMIT_RAD = math.pi

# Sweep: step each joint outward from zero by this many degrees.
SWEEP_STEP_DEG = 1.0
# Sweep: search each direction at most this far.
SWEEP_MAX_DEG = 360.0
# Sweep: refine each collision angle to this resolution.
REFINE_DEG = 0.1
# Sweep: sample downstream joints at most this many degrees apart.
GRID_STEP_DEG = 45.0

# Contact: sample about this many surface points per square millimetre.
DENSITY_PER_MM2 = 1.0
# Contact: a point collides when it sits this far inside another link.
PENETRATION_MM = 1.0
# Contact: search this far for surface samples when judging penetration.
SEARCH_MM = 3.0
# Contact: judge each point against this many samples so sharp edges do not flip the sign.
NEIGHBOURS = 4
# Contact: require this many penetrating points; CAD interference fits reach about 7.
MIN_POINTS = 20
# Contact: ignore points within this distance of another link at the zero pose (joint interfaces).
CLEARANCE_MM = 0.5
# Contact: search this deep when finding zero-pose overlaps.
OVERLAP_SEARCH_MM = 20.0

# Describe each 50-byte binary STL triangle record.
STL_DTYPE = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])


# Apply 4x4 transforms to points; either may carry leading batch dimensions.
def transform(t, points):
    # Rotate then translate.
    return points @ np.swapaxes(t[..., :3, :3], -1, -2) + t[..., :3, 3]


# Build a 4x4 rotation about a unit axis by an angle in radians (Rodrigues' formula).
def rotation(axis, angle):
    # Unpack the axis.
    x, y, z = axis
    # Form the axis cross-product matrix.
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    # Start from the identity.
    t = np.eye(4)
    # Fill the rotation block.
    t[:3, :3] = np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * k @ k
    # Return the transform.
    return t


# Build a 4x4 translation.
def translation(xyz):
    # Start from the identity.
    t = np.eye(4)
    # Fill the translation column.
    t[:3, 3] = xyz
    # Return the transform.
    return t


# Read one URDF joint, converting metres to millimetres.
def read_joint(element):
    # Read the optional origin attributes.
    origin = {} if element.find('origin') is None else element.find('origin').attrib
    # Read the translation in millimetres.
    xyz = [1000 * float(v) for v in origin.get('xyz', '0 0 0').split()]
    # Read fixed-axis roll, pitch, and yaw in radians.
    roll, pitch, yaw = (float(v) for v in origin.get('rpy', '0 0 0').split())
    # Compose the fixed-axis rotation: roll about X, then pitch about Y, then yaw about Z.
    rpy = rotation((0, 0, 1), yaw) @ rotation((0, 1, 0), pitch) @ rotation((1, 0, 0), roll)
    # Read the optional axis, which URDF defaults to X.
    axis = '1 0 0' if element.find('axis') is None else element.find('axis').get('xyz')
    # Return the joint fields.
    return {
        # Name the joint for lookups and reporting.
        'name': element.get('name'),
        # Sweep only revolute and continuous joints.
        'movable': element.get('type') in ('revolute', 'continuous'),
        # Name the parent link.
        'parent': element.find('parent').get('link'),
        # Name the child link.
        'child': element.find('child').get('link'),
        # Translate, then rotate.
        'origin': translation(xyz) @ rpy,
        # Keep the rotation axis.
        'axis': [float(v) for v in axis.split()],
    }


# One link's sampled surface, in its own frame and in millimetres.
class Link:
    # Sample the link's binary STL surface.
    def __init__(self, path, rng):
        # Read triangle vertices after the 84-byte STL header.
        triangles = np.frombuffer(path.read_bytes(), dtype=STL_DTYPE, offset=84)['vertices'].astype(float)
        # Compute winding normals, which point outward for these meshes.
        cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        # Compute triangle areas in square millimetres.
        area = np.linalg.norm(cross, axis=1) / 2
        # Drop degenerate triangles.
        triangles, cross, area = triangles[area > 0], cross[area > 0], area[area > 0]
        # Give each triangle at least one sample and large ones proportionally more.
        counts = np.maximum(1, np.round(area * DENSITY_PER_MM2).astype(int))
        # Repeat each triangle once per sample.
        corners = np.repeat(triangles, counts, axis=0)
        # Draw barycentric coordinates for every sample.
        u, v = rng.random((2, len(corners), 1))
        # Fold samples outside the triangle back inside it.
        u, v = np.where(u + v > 1, 1 - u, u), np.where(u + v > 1, 1 - v, v)
        # Place the samples on their triangles.
        self.points = corners[:, 0] + u * (corners[:, 1] - corners[:, 0]) + v * (corners[:, 2] - corners[:, 0])
        # Give each sample its triangle's unit outward normal.
        self.normals = np.repeat(cross / (2 * area[:, None]), counts, axis=0)
        # Index the samples for nearest-point queries.
        self.tree = cKDTree(self.points)
        # Pad the sample bounds by the search distance.
        self.low, self.high = self.points.min(0) - SEARCH_MM, self.points.max(0) + SEARCH_MM
        # Centre a bounding sphere on the bounds.
        self.centre = (self.low + self.high) / 2
        # Size the sphere to enclose every sample.
        self.radius = np.linalg.norm(self.points - self.centre, axis=1).max()

    # Return each point's distance outside this surface: negative inside, infinite beyond the search.
    def depth(self, points, search):
        # Find each point's nearest samples.
        distance, index = self.tree.query(points, k=NEIGHBOURS, distance_upper_bound=search)
        # Mark neighbours found within the search distance.
        found = distance < np.inf
        # Point missing neighbours at sample 0 to keep indexing valid.
        index = np.where(found, index, 0)
        # Measure each point along each neighbour's outward normal.
        signed = np.einsum('ijk,ijk->ij', points[:, None] - self.points[index], self.normals[index])
        # Count a point inside only when every found neighbour agrees.
        deepest = np.where(found, signed, -np.inf).max(1)
        # Treat points with no neighbours as far outside.
        return np.where(found.any(1), deepest, np.inf)

    # Report whether points penetrate this surface in a colliding amount.
    def penetrated_by(self, points):
        # Keep only points inside the padded bounds.
        points = points[np.all((points > self.low) & (points < self.high), axis=1)]
        # Count points deeper than the penetration threshold.
        return np.sum(self.depth(points, SEARCH_MM) < -PENETRATION_MM) >= MIN_POINTS


# The URDF chain with sampled link meshes; joints must be listed base to tip.
class Robot:
    # Read the URDF chain and sample every link mesh.
    def __init__(self, urdf, mesh_dir):
        # Parse the URDF document.
        root = ET.parse(urdf).getroot()
        # Read every joint in file order.
        self.joints = [read_joint(element) for element in root.findall('joint')]
        # Index joints by name.
        self.joint = {j['name']: j for j in self.joints}
        # Index each link's parent joint.
        self.above = {j['child']: j for j in self.joints}
        # Name the root link.
        self.root = self.joints[0]['parent']
        # Seed sampling so repeated runs give the same limits.
        rng = np.random.default_rng(0)
        # Collect sampled links.
        self.links = {}
        # Visit each link element.
        for element in root.findall('link'):
            # Find the link's visual mesh.
            mesh = element.find('visual/geometry/mesh')
            # Sample links that have one, mapping package URIs to the local directory.
            if mesh is not None:
                # Load the mesh by file name.
                self.links[element.get('name')] = Link(Path(mesh_dir) / Path(mesh.get('filename')).name, rng)
        # Cache masks of each link's points that start clear of another link.
        self.clear = {}

    # List the joints from the root down to a link.
    def path(self, link):
        # Collect joints while walking up.
        joints = []
        # Walk parents until the root.
        while link != self.root:
            # Prepend the joint above this link.
            joints.insert(0, self.above[link])
            # Step to the parent link.
            link = self.above[link]['parent']
        # Return the base-to-link path.
        return joints

    # Report whether a joint moves a link.
    def carries(self, swept, link):
        # Look for the joint on the link's path.
        return any(j['name'] == swept for j in self.path(link))

    # List the movable joints between a swept joint and a link it carries.
    def joints_below(self, swept, link):
        # List movable joints on the link's path.
        names = [j['name'] for j in self.path(link) if j['movable']]
        # Keep those after the swept joint.
        return names[names.index(swept) + 1:]

    # Compute every link pose in the base frame for a map of joint angles; missing joints are zero.
    def poses(self, angles):
        # Place the root at the base frame.
        pose = {self.root: np.eye(4)}
        # Chain joints base to tip so parents are placed first.
        for j in self.joints:
            # Rotate movable joints by their angle.
            turn = rotation(j['axis'], angles.get(j['name'], 0.0)) if j['movable'] else np.eye(4)
            # Compose parent pose, joint origin, and joint rotation.
            pose[j['child']] = pose[j['parent']] @ j['origin'] @ turn
        # Return the pose map.
        return pose

    # Report whether link b's points, clear at the zero pose, now penetrate link a.
    def penetrates(self, a, b, pose_a, pose_b):
        # Build the zero-pose mask once per ordered pair.
        if (a, b) not in self.clear:
            # Place all joints at zero.
            zero = self.poses({})
            # Express link b's points in link a's frame.
            points = transform(np.linalg.inv(zero[a]) @ zero[b], self.links[b].points)
            # Drop joint interfaces and CAD overlaps.
            self.clear[(a, b)] = self.links[a].depth(points, OVERLAP_SEARCH_MM) >= CLEARANCE_MM
        # Select link b's clear points.
        clear = self.links[b].points[self.clear[(a, b)]]
        # Express them in link a's frame and test them.
        return self.links[a].penetrated_by(transform(np.linalg.inv(pose_a) @ pose_b, clear))

    # List moving links and their poses relative to the swept joint's child, per downstream combination.
    def layout(self, swept, grids):
        # Find the swept joint's child link.
        child = self.joint[swept]['child']
        # Collect one entry per moving link.
        entries = []
        # Visit each link the joint carries.
        for link in (link for link in self.links if self.carries(swept, link)):
            # List the downstream joints that move this link.
            names = self.joints_below(swept, link)
            # Sample each joint's range, using zero for joints without limits yet.
            samples = [grids.get(name, [0.0]) for name in names]
            # Combine the samples.
            combos = [dict(zip(names, values)) for values in itertools.product(*samples)]
            # Pose each combination relative to the child frame.
            relative = np.array([np.linalg.inv(p[child]) @ p[link] for p in map(self.poses, combos)])
            # Store the entry.
            entries.append((link, combos, relative))
        # Return the layout.
        return entries

    # Return the first collision at a swept angle as (description, downstream angles), or None.
    def collision(self, swept, angle, layout):
        # Pose the robot with only the swept joint moved.
        pose = self.poses({swept: angle})
        # List links that stay still.
        still = [link for link in self.links if not self.carries(swept, link)]
        # Check each moving link over its downstream combinations.
        for link, combos, relative in layout:
            # Pose every combination at once.
            poses = pose[self.joint[swept]['child']] @ relative
            # Check combinations whose bounding sphere reaches the table or a still link.
            for i in self.candidates(link, poses, still, pose):
                # Report table contact when any point drops below the table plane.
                if np.any(transform(poses[i], self.links[link].points)[:, 2] < TABLE_Z_MM):
                    # Name the table contact.
                    return f'{link} × table', combos[i]
                # Check each still link.
                for other in still:
                    # Report a self-collision, testing both directions for coverage.
                    if (self.penetrates(other, link, pose[other], poses[i])
                            or self.penetrates(link, other, poses[i], pose[other])):
                        # Name the colliding pair.
                        return f'{link} × {other}', combos[i]
        # Report no collision.
        return None

    # Return indices of poses whose bounding sphere reaches the table or a still link's sphere.
    def candidates(self, link, poses, still, pose):
        # Look up the moving link.
        body = self.links[link]
        # Place its sphere centre for every pose.
        centres = transform(poses, body.centre)
        # Flag poses whose sphere reaches the table.
        reach = centres[:, 2] - body.radius < TABLE_Z_MM
        # Visit each still link.
        for other in still:
            # Place the still link's sphere centre.
            centre = transform(pose[other], self.links[other].centre)
            # Flag poses whose spheres overlap within the search distance.
            reach |= np.linalg.norm(centres - centre, axis=1) < body.radius + self.links[other].radius + SEARCH_MM
        # Return the flagged indices.
        return np.flatnonzero(reach)


# Sweep one direction of a joint; return the signed collision angle in degrees and its cause, or None.
def sweep(robot, swept, sign, grids):
    # Precompute downstream poses for this joint.
    layout = robot.layout(swept, grids)

    # Return the collision at an unsigned angle in degrees, or None.
    def hit(deg):
        # Test the signed angle.
        return robot.collision(swept, sign * math.radians(deg), layout)

    # Step outward from zero.
    for step in np.arange(1, round(SWEEP_MAX_DEG / SWEEP_STEP_DEG) + 1) * SWEEP_STEP_DEG:
        # Refine once a step collides.
        if cause := hit(step):
            # Bracket the contact with the last clear step.
            clear = step - SWEEP_STEP_DEG
            # Bisect to the refinement resolution.
            while step - clear > REFINE_DEG:
                # Test the midpoint.
                middle = (clear + step) / 2
                # Tighten the colliding bound when the midpoint collides.
                if found := hit(middle):
                    # Keep the tighter bound and its cause.
                    step, cause = middle, found
                # Otherwise tighten the clear bound.
                else:
                    # Keep the tighter clear bound.
                    clear = middle
            # Return the refined angle and cause.
            return sign * step, cause
    # Report no collision within the sweep.
    return None, None


# Sample a joint range at most GRID_STEP_DEG apart, including zero and both limits.
def grid(lower, upper):
    # Choose enough intervals to respect the grid step.
    count = max(1, math.ceil(math.degrees(upper - lower) / GRID_STEP_DEG))
    # Space samples evenly and add zero.
    values = set(np.linspace(lower, upper, count + 1).tolist()) | {0.0}
    # Drop the upper end of a full turn, which repeats the lower end.
    if upper - lower >= 2 * math.pi - 1e-6:
        # Remove the duplicate pose.
        values.discard(upper)
    # Return the sorted samples.
    return sorted(values)


# Round a map of joint angles for printing.
def rounded(angles):
    # Keep three decimals of radians.
    return {name: round(value, 3) for name, value in angles.items()}


# Compute and print limits for every movable joint, tip to base.
def main():
    # Use the module description as help text.
    parser = argparse.ArgumentParser(description=__doc__)
    # Require the URDF whose origins and axes define the chain.
    parser.add_argument('--urdf', type=Path, required=True, help='Path to arctos.urdf')
    # Require the local directory of prepared link STLs.
    parser.add_argument('--mesh-dir', type=Path, required=True, help='Directory with the prepared link STLs')
    # Parse the arguments.
    args = parser.parse_args()
    # Load the chain and sample the meshes.
    robot = Robot(args.urdf, args.mesh_dir)
    # Store each computed range as a grid for upstream sweeps.
    grids = {}
    # Collect result rows.
    rows = []
    # Sweep from the tip so downstream limits exist before upstream sweeps.
    for name in reversed([j['name'] for j in robot.joints if j['movable']]):
        # Collect the lower and upper limits.
        limits = []
        # Sweep negative, then positive.
        for sign in (-1, 1):
            # Find the nearest collision angle in this direction.
            angle, cause = sweep(robot, name, sign, grids)
            # Apply the factor of safety, or the free limit when nothing collides.
            limits.append(sign * FREE_LIMIT_RAD if angle is None else math.radians(angle) / FACTOR_OF_SAFETY)
            # Record the result.
            rows.append((name, angle, limits[-1], cause))
            # Show progress.
            print(f'{name} {"+" if sign > 0 else "-"} done', flush=True)
        # Expose this joint's range to upstream sweeps.
        grids[name] = grid(*limits)
    # Print the header.
    print(f'\n{"joint":8} {"collision°":>10} {"limit rad":>10} {"limit°":>7}  cause (downstream rad)')
    # Print rows base to tip, lower limit first.
    for name, angle, limit, cause in sorted(rows, key=lambda row: (row[0], row[2])):
        # Describe the cause and the downstream angles that produced it.
        text = f'none within {SWEEP_MAX_DEG:.0f}°' if cause is None else f'{cause[0]} {rounded(cause[1])}'
        # Show the collision angle, or a dash when none.
        shown = '—' if angle is None else f'{angle:.1f}'
        # Print one joint direction.
        print(f'{name:8} {shown:>10} {limit:10.6f} {math.degrees(limit):7.1f}  {text}')


# Run only when executed directly.
if __name__ == '__main__':
    # Start the sweep.
    main()
