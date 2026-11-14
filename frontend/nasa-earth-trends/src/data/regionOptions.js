// The three study regions in the current snapshot (decision D26).
// Boxes match data/regions.json; centre and zoom only frame the map.
export const regions = [
  {
    id: 'ireland',
    name: 'Ireland',
    shortLocation: 'North Atlantic · 51–55°N, 10–6.25°W',
    signal: 'Cool, maritime, and highly seasonal.',
    center: [-8, 53],
    zoom: 5.2,
  },
  {
    id: 'sahel',
    name: 'Sahel (West Africa)',
    shortLocation: 'Sahel belt · 12–18°N, 0–20°E',
    signal: 'A transition zone shaped by rainfall and heat.',
    center: [10, 15],
    zoom: 3.9,
  },
  {
    id: 'us_southwest',
    name: 'US Southwest',
    shortLocation: 'Arid western United States · 31–38°N, 115–105°W',
    signal: 'A dryland system where heat and water availability are tightly linked.',
    center: [-110, 34.5],
    zoom: 4.6,
  },
]
