"""Save a 3D matplotlib view of a tool path among box obstacles."""
import matplotlib
matplotlib.use('Agg')  # Render to file; no display required.
from matplotlib.patches import Patch
import matplotlib.pyplot as plt


def plot_tool_path(path, blocks, output, title='tool0 path'):
    """Plot (x, y, z) points in metres with blocks.yaml boxes; both in base_link."""
    figure = plt.figure(figsize=(8, 7))
    axes = figure.add_subplot(projection='3d')
    axes.plot(*zip(*path), color='tab:blue', label='tool0 path')
    axes.scatter(*path[0], color='tab:green', s=40, label='start')
    axes.scatter(*path[-1], color='tab:red', s=40, label='goal')
    for block in blocks:
        corner = [c - s / 2 for c, s in zip(block['position'], block['size'])]
        axes.bar3d(*corner, *block['size'], color='gray', alpha=0.3)
    axes.set_xlabel('x [m]')
    axes.set_ylabel('y [m]')
    axes.set_zlabel('z [m]')
    axes.set_aspect('equal')
    axes.set_title(title)
    # Proxy handle: matplotlib 3.6 cannot build legend entries from bar3d.
    handles, _ = axes.get_legend_handles_labels()
    axes.legend(handles=handles + [Patch(color='gray', alpha=0.3, label='blocks')])
    figure.savefig(output, dpi=150, bbox_inches='tight')
    plt.close(figure)
