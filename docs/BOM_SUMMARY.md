# Joint 1 MVP budget

**Build the X / `joint_1` base and rotate its printed output. Budget about $175 before shipping and tax.** PLA is already owned; downstream joints and payload are deferred.

| Milestone | Result |
| --- | --- |
| Electrical checkout | Secured Joint 1 NEMA 23 turns slowly in both directions |
| **MVP complete** | Assembled base drives its output through the 630 mm belt, with bearings and tensioner installed |
| Later | Homing, remaining arm, gripper, ROS hardware interface and full-arm loading |

Use USB → Nano-compatible board → external STEP/DIR driver → NEMA 23. A loose motor spinning is only an intermediate check. Single-axis firmware still needs implementation; the repository currently provides a robot description, not this hardware control.

**Shopping list — USD, checked 2026-09-25**

Amazon amounts are observed whole-pack asking prices, **not a verified market-wide cheapest cart**. AliExpress returned page challenges, so matching variant prices could not be confirmed. Blank CSV prices mean unknown, not free.

| Buy for Joint 1 | Required / purchased | Amazon pack cost | AliExpress | Budget |
| --- | --- | ---: | --- | ---: |
| NEMA 23, 2.8 A, 6.35 mm shaft, 76 mm body | 1 / 1 | [$29.99](https://www.amazon.com/dp/B00PNEPI0A) | [Check price](https://www.aliexpress.com/item/4001179117186.html) | $29.99 |
| External TB6600-style driver | 1 / 1 | [$9.98](https://www.amazon.com/dp/B0FFGGJTYX) | [$8.53 tracker lead*](https://www.pricearchive.org/aliexpress.com/item/1005006860889354) | $9.98 |
| Nano-compatible board with USB cable | 1 / 3 boards | [$15.99](https://www.amazon.com/dp/B07G99NNXL) | [Check price](https://www.aliexpress.com/item/1005006003220843.html) | $15.99 |
| Enclosed 24 V, 5 A supply with AC cord | 1 / 1 | [$23.99](https://www.amazon.com/dp/B0DJ92N275) | [Search exact rating](https://www.aliexpress.com/w/wholesale-24v-5a-power-adapter.html) | $23.99 |
| 6806 / 61806, 30×42×7 mm bearings | 2 | Unavailable | [Check price](https://www.aliexpress.com/item/1005004655110314.html) | $10 allowance |
| 625, 5×16×5 mm bearings | 12 / 12 | [$8.99](https://www.amazon.com/dp/B0BRQP2QG7) | [Check price](https://www.aliexpress.com/item/4001139691289.html) | $8.99 |
| GT2 closed belt, 630×10 mm, 2 mm pitch | 1 | Unavailable | [Select 630 mm / 10 mm](https://www.aliexpress.com/item/1005003425274376.html) | $6 allowance |
| 20T GT2 pulley, 6.35 mm bore, 10 mm belt | 1 / 5 | [$7.99](https://www.amazon.com/dp/B07BT6MVXB) | [Select exact variant](https://www.aliexpress.com/item/1005001793654408.html) | $7.99 |
| Smooth idlers, 5 mm bore, 10 mm belt | 2 / 5 | [$9.99†](https://www.amazon.com/dp/B07BPHRSN5) | [Select exact variant](https://www.aliexpress.com/item/32817328238.html) | $9.99 |
| Base screws and nuts | See takeoff below | Pack not selected | Links in CSV | $20 allowance |
| Rigid base board and four M8 attachments | 1 set | Pack not selected | Links in CSV | $10 allowance |
| Motor/power wire, connector, terminals, fuse, DC disconnect, insulation | 1 basket | Pack not selected | Links in CSV | $15 allowance |
| Signal jumpers | 1 / 120-wire pack | [$6.98](https://www.amazon.com/dp/B01EV70C78) | Link in CSV | $6.98 |
| Printed base/transmission parts | 1 set | Owned PLA | — | $0 |
| **Observed-price subset** | Includes idler caveat† | **$113.90** | No verified AliExpress subtotal | |
| **Unpriced allowances** | Bearings, belt, hardware, fixture, wiring | | | **$61.00** |
| **Provisional MVP total** | | | | **$174.90** |

*Search-indexed PriceArchive figure, not a live AliExpress quote; variant, availability and US delivery cost remain unverified. [Direct listing](https://www.aliexpress.com/item/1005006860889354.html). Excluded from totals. No welcome coupons, subscriptions, or fractional pack costs are used in the budget.

† The idler title says **5 mm bore**, but one description bullet says **3 mm**. Confirm 5 mm before purchasing; $9.99 is an observed price, not a cleared purchase recommendation.

**Final item review**

| Item / group | Source confirmation | Remaining check |
| --- | --- | --- |
| Motor | [Official BOM](https://arctosrobotics.com/bom/) item 18 specifies 1.8 Nm, 2.8 A, 6.35 mm shaft, 76 mm body; selected listing offers 1.9 Nm with matching dimensions | Motor lead length and mounting fit |
| Driver | Custom MVP substitution; [DFRobot documentation](https://www.dfrobot.com/product-1547.html) supports external STEP/DIR architecture | Generic module differs from DFRobot; verify its current table, signal current and cooling |
| Controller | BOM 29 identifies Nano with cable | Open-loop STEP/DIR is a substitution; verify headers/cable and prepare firmware; Mega firmware is not a drop-in |
| Supply | Selected listing specifies 24 V / 5 A / 120 W and AC cord | Confirm connector polarity/rating and driver requirements; power Nano over USB |
| Central bearings | BOM 1 and local CAD: two 6806 bearings on the X shaft | Exact-size pack price |
| Support bearings | BOM 2 and local CAD: twelve 625 bearings around the base | Printed fits and free rotation |
| Belt | BOM 9 explicitly names X and 630×10 mm | Closed-loop variant and pack cost |
| Motor pulley | BOM 15 matches 20T / W10 / B6.35; one pulley belongs to X | Belt alignment and shaft attachment |
| Idlers | BOM 16; two X-tensioner locations in CAD | Seller's bore contradiction |
| Base fasteners | BOM 40, 46, 48, 54, 56 provide sizes; local CAD supplies provisional X-only counts; assembly step 724 calls out washers | Dry-fit lengths/thread engagement and washer stack; price retail packs |
| Base attachment | Four CAD mounting positions; CAD models M8×25, global BOM 51 says M8×40 | Length depends on fixture thickness |
| Power wiring | Required by external-driver architecture; original cable rows do not select all necessary connectors | Select wire, connector, fuse and DC disconnect ratings together |
| Signal jumpers | BOM 75 | Signal use only; do not carry motor power |
| Printed parts | Purchased 2.9.7 CAD/STLs; [official assembly viewer](https://arctosrobotics.com/wp-content/uploads/2026/Assembly/viewer.html) is the assembly reference | Physical assembly fit and belt tension |

Base fastener takeoff: **11× M3×20 + 11× M3 nuts; 10× M5×20; 12× M5×30; 10× M5 nuts; 2× M5 washers**, plus four fixture-dependent M8 attachments. Counts are CAD-derived for the base and output only; sensor holders and electronics panels are excluded.

Final assembly-doc pass: steps **721–726** cover tensioner/idlers/belt; **753 and 801** identify the two central bearings; **806–808** cover support bolts/bearings; **814** identifies table fasteners. Step **724** labels a washer “M3,” but the corresponding CAD part measures **5.3 mm ID / 10 mm OD**: use M5 dimensions. CAD also contains coincident printed WasherXIdler spacers; confirm the intended stack by dry fit rather than blindly stacking both representations. This remains an unresolved assembly detail.

Print X lower core, X upper Core, X motor CORE, X pulley shaft, X pulley, X pulley nut, X idler tensioner, and both WasherXIdler spacers. Purchased assets and derived meshes remain local under `cad/`.

**Review corrections:** rejected the old supply link because it identifies a Resvent adapter; rejected the cheaper $25.99 motor because it has an 8 mm shaft and 82 mm body. Removed the wrist NEMA 17, CNC shield, TMC2209, full-arm 20 A supply, cosmetic panels and full-arm hardware basket from the first purchase.

Start with supervised slow jogs of the unloaded base and an accessible DC power cut. Homing sensors/magnets, automatic homing, unattended operation and payload tests are deferred. Establish travel from physical clearance before motion; project limits use the nearest collision angle divided by 1.5. The model does not validate hardware travel or implement control.

[MVP_BOM.csv](MVP_BOM.csv) is the current Joint 1 plan, including per-item evidence and price status. [BOM.csv](BOM.csv) remains the full-arm source inventory. [AXIS_BOM.csv](AXIS_BOM.csv) describes the **superseded wrist-bench schedule**; its reuse columns and totals do not apply here. The previous $757.10 full-arm estimate is not an updated expansion quote.

Assumed owned: computer, tools and PLA. Shipping, tax, duties, print electricity and replacements are excluded. The $174.90 total remains provisional until unpriced packs and flagged variants are resolved.
