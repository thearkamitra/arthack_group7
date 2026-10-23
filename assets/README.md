# Input images

The original JPEGs and transparent derivatives are stored here. These folders
can also hold future user-provided image pairs.

| Input | Current artwork | Suggested path |
| --- | --- | --- |
| Image one | Mona Lisa | `input_one/example_rgba.png` |
| Image two | Girl with a Pearl Earring | `input_two/example_rgba.png` |

Each folder retains its original `example.jpg` unchanged. Transparent copies
use PNG because JPEG cannot store alpha. Training uses the PNG copies.

These cutouts were made with the built-in image generation/editing tool.
Prompt for each: remove only the background, preserve the visible person,
painted face, pose, clothing, headwear and original composition, and output
actual RGBA transparency. For Mona Lisa, also remove the chair; for Girl with
a Pearl Earring, retain the pearl and trailing turban fabric. Generated edits
are not guaranteed to preserve every original pixel or the source dimensions.

Use PNG or JPEG. Keep the file extension consistent with the actual format.
For a different pair, add new files instead of replacing originals. Pass their
paths to the backend CLI using `--image-one` and `--image-two`. These folders
do not automatically load or process uploads.

Auto-MIA supports RGBA images with an alpha mask. For images without alpha,
it derives a foreground mask from luminance; full rectangular paintings may
need deliberate cropping or masking before meaningful sculpture optimization.

This pair has a working fixed-surface prototype at the two target viewpoints.
Back views remain abstract; stereo VR and arbitrary image pairs are unvalidated.
