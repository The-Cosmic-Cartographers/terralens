// The three study regions in the current snapshot (decision D26).
// Boxes match data/regions.json; centre and zoom only frame the map.
const allRegions = [
  {
    id: 'ireland',
    name: 'Ireland',
    shortLocation: 'North Atlantic · 51–55°N, 10–6.25°W',
    signal: 'Cool, maritime, and highly seasonal.',
    center: [-8, 53],
    zoom: 5.2,
  },
  {
    id: 'iberia',
    name: 'Iberia',
    shortLocation: 'Southwestern Europe · 36–44°N, 10–2°W',
    signal: 'A strong contrast of dry interiors and Atlantic edges.',
    center: [-4, 40],
    zoom: 4.8,
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
    id: 'nw_south_asia',
    name: 'Northwest India',
    shortLocation: 'Indus plain and northwest India · 22–32°N, 68–80°E',
    signal: 'Monsoon, irrigation, dust, and urban pressure meet here.',
    center: [75, 28],
    zoom: 4.6,
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

// The app shows the five snapshot regions (decision D31).
const APP_REGION_IDS = ['ireland', 'iberia', 'sahel', 'nw_south_asia', 'us_southwest']
export const regions = allRegions.filter((region) => APP_REGION_IDS.includes(region.id))
