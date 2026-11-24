# EcoBlend Direct v0.1
Experimental Windows CLI, no MCP. Requires Python 3 and installed Blender/FreeCAD.
Run `py -3 agent.py status`, then `py -3 agent.py demo --engine blender` or `py -3 agent.py demo --engine freecad --size 20`.
The optional `py -3 mailbox.py` downloads a single public job from this branch, validates an allowlist, and requires local YES approval. No listener, arbitrary scripts, secrets, automatic upload or live GUI control. Never put private project data in job.json. Output stays under ~/EcoBlendDirect. Copy only the status summary into chat. Blender units are meters, FreeCAD millimeters. FreeCAD CLI behavior needs actual Windows validation. If detection fails set ECOBLEND_BLENDER or ECOBLEND_FREECAD to the executable path. This is not a deployed cloud service.
