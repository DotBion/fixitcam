# Failure log

## macbook_cable_clean.mp4 — baseline
- expected: magsafe (frayed Apple MagSafe MacBook charger cable)
- baseline query: Apple MagSafe charger
  1. Apple AUTHENTIC MagSafe Charger (1m) (kw=True, fit=None) — judge: This is a wireless MagSafe charger for iPhones/AirPods, not a MacBook MagSafe charger cable.
  2. MAGSAFE CHARGER (2 M) (kw=True, fit=None) — judge: This is a wireless MagSafe charger for iPhones and AirPods, not a MacBook MagSafe charger cable.
  3. Apple MagSafe Charger (2 m): Wireless Charger with Fast-Charging Capability (kw=True, fit=None) — judge: This is a wireless MagSafe charger for iPhones, not a MacBook MagSafe charger cable.

## macbook_cable_messy.mp4 — baseline
- expected: magsafe (frayed Apple MagSafe MacBook charger cable)
- baseline query: ballpoint pen with cap
  1. R.S.V.P.® 1.0MM CAPPED BALLPOINT PEN - WATCO-BK91N (kw=False, fit=None) — judge: This is a ballpoint pen, not a MagSafe MacBook charger cable.
  2. Kaweco - Ballpoint Pen - Liliput - Silver (With Cap) (kw=False, fit=None) — judge: This is a ballpoint pen, not a MagSafe MacBook charger cable.
  3. Fisher Space Cap-O-Matic Ballpoint Pen in Yellow with Brass Trim (kw=False, fit=None) — judge: This is a ballpoint pen, not a MagSafe MacBook charger cable.

## aerator_messy.mp4 — baseline
- expected: aerator (worn swivel faucet aerator)
- baseline query: garden hose quick connect coupler
  1. 🍃Stainless Steel Garden Hose Quick Connect Fittings Set (kw=False, fit=None) — judge: This is a garden hose quick connect fittings set, not a faucet aerator.
  2. 🔥🔩Garden Hose Quick Connector (kw=False, fit=None) — judge: This is a garden hose quick connector, not a faucet aerator.
  3. MTM Garden Hose Quick Connect Coupler + Plug (kw=False, fit=None) — judge: This is a garden hose quick connect coupler and plug, not a faucet aerator.

## brakepads_clean.mp4 — baseline
- expected: brake pad (worn metallic disc brake pads)
- baseline query: bicycle disc brake pads
  1. Shimano J03A Resin Disc Brake Pads (kw=True, fit=None) — judge: These are resin pads rather than metallic disc brake pads, and compatibility with the specific caliper is not confirmed.
  2. SRAM Code / DB8 / G2 RE / Guide RE / Motive – Factory Racing Organic Disc Brake Pads | Gorilla Brakes (kw=True, fit=None) — judge: These are organic pads rather than metallic disc brake pads, and they only fit specific SRAM calipers.
  3. Disc Brake Pads (kw=True, fit=None) — judge: The pad compound is not specified as metallic, and compatibility with the specific brake caliper is not confirmed.

## brakepads_messy.mp4 — baseline
- expected: brake pad (worn metallic disc brake pads)
- baseline query: bicycle disc brake pads
  1. Shimano J03A Resin Disc Brake Pads (kw=True, fit=None) — judge: These are resin disc brake pads, not metallic, and compatibility with the specific caliper is not guaranteed.
  2. SRAM Code / DB8 / G2 RE / Guide RE / Motive – Factory Racing Organic Disc Brake Pads | Gorilla Brakes (kw=True, fit=None) — judge: These are organic disc brake pads, not metallic, and compatibility with the specific caliper is not guaranteed.
  3. Disc Brake Pads (kw=True, fit=None) — judge: These are generic disc brake pads that do not specify metallic compound or guaranteed compatibility.
