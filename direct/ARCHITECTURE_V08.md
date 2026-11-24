# EcoBlend Architecture v0.8
## Workflow A: geometry to images
1. Validate geometry and measurements with Architecture v0.5.
2. Run design_interpreter_v08.py brief --project JOB --style STYLE.
3. Read image_briefs.json. Generate or rectify one image per surface with a common palette and exact opening positions. Generation is done in ChatGPT or another authorized image editor, not by the local script.
4. Save PNG/JPG locally in photo_references, using F01/F02/F03/F04/P01 filenames.
5. Open Painter v0.8 at localhost:8789, select references, apply, inspect export report and compare visually in gallery.
6. To change a surface, select the latest successful revision and apply only the changed image. Keep previous versions.
## Workflow B: reference to geometry
ChatGPT interprets the reference image and produces a proposal JSON with spec (width,depth,height,wall,openings), dimension_status (verified/estimated/proposed for every field), and notes. Single image cannot establish hidden geometry.
Run design_interpreter_v08.py proposal --input proposal.json --build.
Outputs conceptual exterior plan SVG, provenance and editable rectangular shell in Blender and FreeCAD. No interior layout or roof yet. Not a construction drawing.
## Limits and acceptance
No automatic AI image generation or cloud transfer, no arbitrary mesh projection, no interior or roof support yet.
Validate Windows installation, both engines, all five textured surfaces and a single-face revision retaining other textures. Verify actual geometry and renders before calling photorealistic.
Next: interior geometry and per-face IDs, orthographic review renders, unified dashboard, first-person navigation and mobile AR.
