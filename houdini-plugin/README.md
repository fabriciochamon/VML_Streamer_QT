# Vision ML Plugin for SideFX Houdini

Vision ML contains a set of decoder nodes for VML Streamer, plus a few utility nodes unrelated to the streamer but useful for general ML operations inside Houdini.

## Installation

1. Download `Vision_ML` to your machine
2. Open `vision_ml.json` and change "**VISION_ML**" variable to point to the current folder
3. Copy the json file to `<houdini user dir>/packages`
4. Restart Houdini

All nodes will appear under the "Vision ML" tab menu category.

---
## VML Streamer direct launch
To be able to tab > VML Streamer and launch the standalone app right inside Houdini, 
make sure you have the binary file properly placed under:

`Vision_ML/bin/Windows/vml_streamer.exe`(**Windows**)

or

`Vision_ML/bin/Linux/vml_streamer`(**Linux**)

