#!/usr/bin/env python3
"""Synthetic tests for URDF semantics, mesh bounds, and offline output."""
import json
import math
from pathlib import Path
import re
import struct
import tempfile
import unittest
from build_viewer import convert, mesh_bounds, render

ROBOT = '''<robot name="Test robot">
  <material name="orange"><color rgba="1 0.5 0 1"/></material>
  <link name="base"><visual><geometry><box size="0.4 0.4 0.1"/></geometry></visual></link>
  <link name="arm"><visual><origin xyz="0 0 0.5" rpy="0 0.2 0"/>
    <geometry><cylinder radius="0.04" length="1"/></geometry><material name="orange"/></visual></link>
  <link name="tool"><visual><geometry><sphere radius="0.08"/></geometry></visual></link>
  <link name="finger"/><link name="copy"/><link name="copy2"/>
  <joint name="shoulder" type="revolute"><parent link="base"/><child link="arm"/>
    <origin xyz="0 0 0.1" rpy="0 0 1.5707963267948966"/><axis xyz="0 1 0"/>
    <limit lower="-1" upper="1" velocity="0.4" effort="10"/></joint>
  <joint name="tool_mount" type="fixed"><parent link="arm"/><child link="tool"/><origin xyz="0 0 1"/></joint>
  <joint name="grip" type="prismatic"><parent link="tool"/><child link="finger"/>
    <axis xyz="1 0 0"/><limit lower="0" upper="0.1"/></joint>
  <joint name="follower" type="prismatic"><parent link="tool"/><child link="copy"/>
    <axis xyz="1 0 0"/><limit lower="-0.2" upper="0.1"/><mimic joint="grip" multiplier="-2" offset="0.01"/></joint>
  <joint name="follower2" type="prismatic"><parent link="tool"/><child link="copy2"/>
    <axis xyz="1 0 0"/><limit lower="-0.1" upper="0.1"/><mimic joint="follower" multiplier="0.5" offset="0.02"/></joint>
</robot>'''

class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'robot.urdf'

    def tearDown(self):
        self.temp.cleanup()

    def load(self, xml=ROBOT, **kwargs):
        self.source.write_text(xml)
        return convert(self.source, **kwargs)

    def test_transforms_limits_mimic_material(self):
        model = self.load(tip='tool', tip_at=[0, 0, 0.2])
        self.assertEqual(model['root'], 'base')
        joint = model['joints'][0]
        self.assertEqual(joint['axis'], [0, 1, 0])
        self.assertEqual(joint['xyz'], [0, 0, 0.1])
        self.assertAlmostEqual(joint['rpy'][2], math.pi / 2)
        self.assertEqual((joint['lower'], joint['upper']), (-1, 1))
        self.assertEqual(model['joints'][3]['mimic'], {'joint': 'grip', 'multiplier': -2, 'offset': 0.01})
        self.assertEqual(model['links']['arm']['blocks'][0]['color'], [1, 0.5, 0])
        self.assertEqual(model['tip'], {'link': 'tool', 'at': [0, 0, 0.2]})

    def test_fixed_only_and_continuous(self):
        self.assertEqual(self.load('<robot name="Fixed"><link name="base"/></robot>')['joints'], [])
        joint = self.load(ROBOT.replace('type="revolute"', 'type="continuous"'))['joints'][0]
        self.assertEqual(joint['lower'], -math.pi)
        self.assertEqual(joint['type'], 'continuous')

    def test_invalid_models(self):
        replacements = [('type="revolute"', 'type="floating"'), ('axis xyz="0 1 0"', 'axis xyz="0 0 0"'),
                        ('lower="-1"', 'lower="2"'), ('lower="-1"', 'lower="nan"'), ('lower="-1"', 'other="-1"'),
                        ('mimic joint="grip"', 'mimic joint="follower2"'), ('mimic joint="grip"', 'mimic joint="missing"'),
                        ('parent link="base"', 'parent link="finger"'), ('</robot>', '<link name="extra"/></robot>'),
                        ('</robot>', '<link name="base"/></robot>'), ('child link="arm"', 'child link="absent"')]
        for before, after in replacements:
            with self.subTest(after=after), self.assertRaises(ValueError):
                self.load(ROBOT.replace(before, after))

    def test_ascii_binary_and_obj_bounds(self):
        ascii_stl = self.root / 'part.stl'
        ascii_stl.write_text('solid test\nvertex 1 2 3\nvertex 3 4 5\nvertex 2 3 4\nendsolid test')
        obj = self.root / 'part.obj'
        obj.write_text('v 1 2 3\nv 3 4 5\nv 2 3 4\n')
        binary_stl = self.root / 'binary.stl'
        binary_stl.write_bytes(b'solid' + b' ' * 75 + struct.pack('<I12fH', 1, 0, 0, 1, 1, 2, 3, 3, 4, 5, 2, 3, 4, 0))
        for path in [ascii_stl, binary_stl, obj]:
            self.assertEqual(mesh_bounds(path, [2, -1, 0.5]), {'box': [4, 2, 1], 'center': [4, -3, 2]})

    def test_package_mesh_visual_origin(self):
        (self.root / 'part.obj').write_text('v 1 2 3\nv 3 4 5\n')
        xml = '''<robot name="Mesh"><link name="base"><visual><origin xyz="1 0 0" rpy="0 0 1.57"/>
          <geometry><mesh filename="package://test_pkg/part.obj" scale="2 1 1"/></geometry></visual></link></robot>'''
        block = self.load(xml, packages={'test_pkg': self.root}, strict_meshes=True)['links']['base']['blocks'][0]
        self.assertEqual(block['center'], [4, 3, 4])
        self.assertEqual(block['at'], [1, 0, 0])
        self.assertEqual(block['rpy'], [0, 0, 1.57])

    def test_missing_mesh_reported_or_fails(self):
        xml = '<robot><link name="base"><visual><geometry><mesh filename="missing.dae"/></geometry></visual></link></robot>'
        self.assertIn('mesh omitted', ' '.join(self.load(xml)['warnings']))
        with self.assertRaises(ValueError):
            self.load(xml, strict_meshes=True)

    def test_offline_output_and_script_escaping(self):
        model = self.load()
        model['name'] = '</script><script>alert(1)</script>'
        output = self.root / 'viewer.html'
        render(model, output)
        html = output.read_text()
        self.assertNotIn('<script src=', html)
        encoded = re.search(r'id="robot-model">(.*?)</script>', html, re.S).group(1)
        self.assertEqual(json.loads(encoded)['name'], model['name'])
        self.assertNotIn('</script>', encoded)
        self.assertNotIn('id="tab-ik"', html)
        self.assertNotIn('function solveIK', html)

if __name__ == '__main__':
    unittest.main()
