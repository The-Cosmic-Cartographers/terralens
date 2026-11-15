# Ground-station direction check (NAS-44)

Generated 2026-11-15 by `python -m analysis.station_check` from NOAA Climate Data Online (GSOM monthly summaries). A **direction check**: stations measure a point, the model a box average, so slopes are not expected to match, only their sign and the broad significance. The same statistics (seasonal Mann-Kendall with Hamed-Rao correction, Sen's slope) are used for the stations and the model.

## Ireland

### Air temperature (1981-2025)

| Station | Months present | Slope per decade | p (serial-correlation corrected) | Direction |
| -- | -- | -- | -- | -- |
| Armagh, Uk (UK000047811) | 538 | +0.294 | 1e-07 | increasing |
| Lough Navar Forest, Uk (UKE00105878) | 522 | +0.222 | 0.00025 | increasing |
| Dublin Phoenix Park, Ei (EI000003969) | 486 | +0.376 | 5.67e-12 | increasing |
| Malin Head, Ei (EI000003980) | 438 | +0.268 | 1.37e-08 | increasing |
| Ballyshannon Cathleens Fall, Ei (EIE00107808) | 501 | +0.337 | 2.83e-09 | increasing |
| **Model box (MERRA-2)** | 540 | **+0.209** | **1.53e-05** | **increasing** |

Units: °C per decade. 5 of 5 stations have the same direction as the model box. Correlation of monthly anomalies between the mean of the stations and the model box: 0.97.

### Precipitation (1980-2025)

| Station | Months present | Slope per decade | p (serial-correlation corrected) | Direction |
| -- | -- | -- | -- | -- |
| Armagh, Uk (UK000047811) | 546 | -1.350 | 0.987 | decreasing |
| Lough Navar Forest, Uk (UKE00105878) | 506 | +26.736 | 0.447 | increasing |
| Dublin Phoenix Park, Ei (EI000003969) | 480 | -5.700 | 0.857 | decreasing |
| Malin Head, Ei (EI000003980) | 493 | +2.160 | 0.371 | increasing |
| Ballyshannon Cathleens Fall, Ei (EIE00107808) | 500 | +28.193 | 0.263 | increasing |
| Waterford Tycor, Ei (EIE00107762) | 468 | +15.672 | 0.681 | increasing |
| Valentia Observatory, Ei (EI000003953) | 491 | +43.257 | 0.137 | increasing |
| **Model box (MERRA-2)** | 552 | **+18.206** | **0.187** | **increasing** |

Units: mm (annual total) per decade. 5 of 7 stations have the same direction as the model box. Correlation of monthly anomalies between the mean of the stations and the model box: 0.92.

## US Southwest (Colorado Basin)

### Air temperature (1981-2025)

| Station | Months present | Slope per decade | p (serial-correlation corrected) | Direction |
| -- | -- | -- | -- | -- |
| Lizard Head Pass, Co Us (USS0007M29S) | 447 | +0.548 | 3.64e-07 | increasing |
| Maverick Fork, Az Us (USS0009S02S) | 435 | +0.630 | 5.15e-10 | increasing |
| Lily Pond, Co Us (USS0006M23S) | 461 | +0.687 | 1.17e-09 | increasing |
| Beartown, Co Us (USS0007M32S) | 490 | +0.124 | 0.061 | increasing |
| Slumgullion, Co Us (USS0007M30S) | 462 | +0.444 | 6.72e-06 | increasing |
| Alamosa Bergman Field, Co Us (USW00023061) | 540 | +0.386 | 1.42e-05 | increasing |
| Idarado, Co Us (USS0007M27S) | 443 | +0.292 | 0.000955 | increasing |
| Hopewell, Nm Us (USS0006N14S) | 443 | +0.667 | 1.05e-10 | increasing |
| **Model box (MERRA-2)** | 540 | **+0.464** | **1.09e-11** | **increasing** |

Units: °C per decade. 8 of 8 stations have the same direction as the model box. Correlation of monthly anomalies between the mean of the stations and the model box: 0.87. 7 of the 8 stations are SNOTEL mountain sites, which sit higher and wetter than the box average.

### Precipitation (1980-2025)

| Station | Months present | Slope per decade | p (serial-correlation corrected) | Direction |
| -- | -- | -- | -- | -- |
| Maverick Fork, Az Us (USS0009S02S) | 543 | -57.358 | 0.000909 | decreasing |
| Lily Pond, Co Us (USS0006M23S) | 545 | -48.283 | 0.00223 | decreasing |
| Castle Valley, Ut Us (USS0012M13S) | 543 | -14.490 | 0.0723 | decreasing |
| Red River Pass Number 2, Nm Us (USS0005N11S) | 552 | -18.160 | 0.0467 | decreasing |
| Beartown, Co Us (USS0007M32S) | 519 | -53.875 | 0.00288 | decreasing |
| Chamita, Nm Us (USS0006N03S) | 552 | -53.083 | 0.000374 | decreasing |
| Widtsoe Number 3, Ut Us (USS0011M03S) | 552 | -13.167 | 0.358 | decreasing |
| Fry, Az Us (USS0011P13S) | 543 | -16.462 | 0.253 | decreasing |
| Workman Creek, Az Us (USS0010S01S) | 543 | -71.056 | 0.00802 | decreasing |
| Harris Flat, Ut Us (USS0012M05S) | 552 | -8.419 | 0.417 | decreasing |
| Culebra Number 2, Co Us (USS0005M03S) | 552 | -56.400 | 0.000116 | decreasing |
| Lizard Head Pass, Co Us (USS0007M29S) | 545 | -52.926 | 0.000389 | decreasing |
| **Model box (MERRA-2)** | 552 | **-23.230** | **0.000571** | **decreasing** |

Units: mm (annual total) per decade. 12 of 12 stations have the same direction as the model box. Correlation of monthly anomalies between the mean of the stations and the model box: 0.84. 12 of the 12 stations are SNOTEL mountain sites, which sit higher and wetter than the box average.

## Summary

| Region | Variable | Stations agreeing in direction | Anomaly correlation (station mean vs model) |
| -- | -- | -- | -- |
| Ireland | air temperature | 5 of 5 | 0.97 |
| Ireland | precipitation | 5 of 7 | 0.92 |
| US Southwest (Colorado Basin) | air temperature | 8 of 8 | 0.87 |
| US Southwest (Colorado Basin) | precipitation | 12 of 12 | 0.84 |

Data: NOAA National Centers for Environmental Information, Climate Data Online, dataset GSOM (Global Summary of the Month). Queried with a personal API token that is not stored in this repository.
