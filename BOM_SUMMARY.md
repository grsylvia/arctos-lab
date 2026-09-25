# Arctos MVP budget

**Start with one unloaded axis: about $140.** Expand to the full open-loop arm: about **$760 total**, with PLA already owned.

All USD prices are **unverified planning allowances**, not current vendor quotes. The [official BOM](https://arctosrobotics.com/bom/) has quantities and links but no prices.

| Stage | Estimated spend | What it demonstrates |
| --- | ---: | --- |
| 1 — One-axis bench prototype | **$133.32** | One fixed motor turns a printed indicator; verifies basic printing, wiring, and control |
| 2 — Complete open-loop arm | **$623.78 additional** | Six moving axes plus gripper, using stage 1 purchases |
| Both stages combined | **$757.10** | Full BOM open-loop allowance ($732.10) + $25 setup supplies |
| PLA | **$0.00** | Already owned; full BOM specifies 5 kg |

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
