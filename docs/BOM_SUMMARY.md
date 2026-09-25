# Arctos MVP budget

**Start with one unloaded axis: about $140.** Expand to the full open-loop arm: about **$760 total**, with PLA already owned.

All USD prices are **unverified planning allowances**, not current vendor quotes. The [official BOM](https://arctosrobotics.com/bom/) has quantities and links but no prices.

| Stage | Estimated spend | What it demonstrates |
| --- | ---: | --- |
| 1 — One-axis bench prototype | **$133.32** | One fixed motor turns a printed indicator; verifies basic printing, wiring, and control |
| 2 — Complete open-loop arm | **$623.78 additional** | Six moving axes plus gripper, using stage 1 purchases |
| Both stages combined | **$757.10** | Full BOM open-loop allowance ($732.10) + $25 setup supplies |
| PLA | **$0.00** | Already owned; full BOM specifies 5 kg |

**Marginal cost by actual robot axis**

The bench motor belongs to **A / `joint_4`**, not the base. Structural mapping below comes from [geometry.yaml](../src/arctos_description/config/geometry.yaml) and [arctos.urdf](../src/arctos_description/urdf/arctos.urdf).

| Arctos axis | ROS joint | Parent → child link | Rotation axis in CAD pose |
| --- | --- | --- | --- |
| X | `joint_1` | `base_link` → `shoulder_link` | +Z |
| Y | `joint_2` | `shoulder_link` → `upper_arm_link` | +Y |
| Z | `joint_3` | `upper_arm_link` → `elbow_link` | +Y |
| A | `joint_4` | `elbow_link` → `wrist_roll_link` | +X |
| B | `joint_5` | `wrist_roll_link` → `wrist_pitch_link` | +Y |
| C | `joint_6` | `wrist_pitch_link` → `tool_link` | +X |

The [description package](../src/arctos_description/README.md) is a structural visual model: it omits motors, fasteners, covers, and the gripper. It cannot establish a complete per-axis shopping list. **Buy the unassigned hardware basket once in this schedule; the small axis increments below are not standalone assembled-joint prices.**

| Purchase after the $133.32 bench prototype | Marginal USD | Running total USD |
| --- | ---: | ---: |
| Shared / unassigned hardware, purchased once | $417.08 | $550.40 |
| X / `joint_1` | $43.00 | $593.40 |
| Y / `joint_2` | $57.00 | $650.40 |
| Z / `joint_3` | $39.50 | $689.90 |
| A / `joint_4` | $2.00 | $691.90 |
| B / `joint_5` | $22.00 | $713.90 |
| C / `joint_6` | $22.00 | $735.90 |
| Gripper accessory | $21.20 | $757.10 |

| Axis | Assigned BOM items | Reuse / allocation basis |
| --- | --- | --- |
| X | 9: belt; 15: pulley; 18: motor; 25: driver | One X motor channel |
| Y | 10: belt; 15: pulley; 18: motor; 25: driver; 63: pins | One Y motor channel and its named gearbox pins |
| Z | 11: belt; 14: pulley; 19: motor; 25: driver; 62: pins | One Z motor channel and its named gearbox pins |
| A | 13: pulley; 20: motor; 25: driver | $19 assigned total; $17 motor/driver already bought, leaving $2 |
| B | 12: belt; 13: pulley; 21: motor; 25: driver | Half of paired B/C motor and belt quantities |
| C | 12: belt; 13: pulley; 21: motor; 25: driver | Other half of paired B/C quantities |
| Gripper | 22: servo; 64: pins | Accessory beyond `tool_link`; not a seventh modeled axis |

Pulley assignments are inferred from shaft diameter, belt width, and channel counts. The model defines joint geometry, not motor-to-joint transmissions; the B/C split is bookkeeping, not proof that either wrist joint can operate independently. Plan their mechanical integration together.

The **$417.08** basket retains bearings, fasteners, idlers, rods, sensors, remaining shared electronics, cables, and consumables whose axis allocation is unverified. This avoids guessing bearing or screw counts from structural meshes. A's $2 increment therefore does **not** mean an assembled A joint costs $2.

**$133.32 bench + $417.08 shared + $185.50 axis additions + $21.20 gripper = $757.10.** [AXIS_BOM.csv](AXIS_BOM.csv) records every quantity split, reused purchase, model joint/link, and source purchase link. No price allowances were changed.

The URDF currently locks joint limits at zero and has no verified inertial or collision model. This schedule tracks purchasing, not readiness to enable robot motion.

**Stage 1: buy only these quantities**

| Parts | BOM item(s) | Quantity | USD |
| --- | --- | --- | ---: |
| A-axis NEMA 17, 1.3 A | 20 | 1 | $12.00 |
| Arduino Mega + CNC shield V3 | 23, 24 | 1 each | $25.00 |
| TMC2209 driver | 25 | 1 | $5.00 |
| Power supply | 31 | 1 | $30.00 |
| Panel connector + switch | 32, 33 | 1 each | $5.00 |
| Cooling fan | 35 | 1 | $4.00 |
| M3×10 mounting screws | 38 | 4; confirm fit | $0.32 |
| Motor cable, power cord, jumper set, USB cable | 73–76 | 1 each | $19.00 |
| Zip ties + heat shrink | 67, 68 | 1 pack each | $8.00 |
| Wiring, terminals, circuit protection | Added allowance | 1 allowance | $15.00 |
| Rigid bench fixture and attachment hardware | Added allowance | 1 allowance | $10.00 |
| **Stage 1 total** | | | **$133.32** |

Use the A-axis motor because its BOM rating is 1.3 A. Set the driver's current for that motor and the actual carrier's cooling limits. Verify shield pin mapping and driver orientation before power-up. Use a suitably rated, enclosed supply; do not leave mains terminals exposed.

Print a small indicator and rigid fixture from owned PLA; these are prototype fixtures to prepare. **Stage 1 is an unloaded bench demonstration, not an assembled Arctos joint or lifting test.** Base bearings, gearboxes, endstops, and the remaining axes wait until stage 2. Exact X-base hardware quantities were not verified.

| Stage 1 pass check | Required result |
| --- | --- |
| Motion | Repeatable slow forward/reverse commands with the motor secured |
| Printed fit | Indicator and fixture fit without slipping or cracking |
| Wiring and control | Accessible power cut; no loose terminals or driver thermal shutdown |
| Expansion | Keep every purchased component for the final arm |

**Full-arm cost breakdown — includes stage 1 parts**

| Category | USD |
| --- | ---: |
| Bearings | $231.50 |
| Six steppers + gripper servo | $134.00 |
| Screws + nuts | $77.90 |
| Open-loop control boards + drivers | $60.00 |
| Power + general electronics | $59.00 |
| Belts + pulleys + idlers | $51.50 |
| Rods + dowel pins | $50.70 |
| Cables | $36.50 |
| Magnets + consumables | $31.00 |
| Added setup supplies | $25.00 |
| Owned PLA | $0.00 |
| **Total** | **$757.10** |

Bearings are the largest allowance: the 22 × 61803 bearings alone account for $66, and 5 × 61812 account for $60. Compare matching sizes and pack prices before buying.

| Defer or reuse | Budget effect |
| --- | --- |
| Closed-loop electronics, items 26–30 | Not purchased for either MVP stage |
| Remaining motors, bearings, transmissions, gripper | Deferred during stage 1; retained in the full-arm total |
| PLA and purchased CAD | No new purchase cost |
| Cosmetic panels | Print later; no assumed hardware savings |

[MVP_BOM.csv](MVP_BOM.csv) provides both stage quantities, USD totals, remaining spend, and purchase/search links. [BOM.csv](BOM.csv) preserves the complete 76-item source list, including the closed-loop alternative. Full closed-loop source allowance with owned PLA is $900.10, before the added setup allowance.

Tools and a computer are assumed owned. Shipping, tax, duties, retail pack rounding, electricity, and replacements are excluded. The $25 setup reserve is provisional. Prices and component compatibility still require checking; this is a staged budget, not a verified checkout cart.

Sources: [Arctos BOM](https://arctosrobotics.com/bom/) for parts and quantities; [Arctos docs](https://arctosrobotics.com/docs/) for open-loop architecture and assembly context. Checked 2026-09-25.
