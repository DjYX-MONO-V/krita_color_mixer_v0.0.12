# Color Mixer Studio for Krita

Color Mixer Studio is a Python plugin for Krita that lets you mix colors, create palettes, and analyze color differences and contrast. It adds two dockers: **Color Mixer Studio** and **Color Mixer: Palettes**.

## Download

Download the project archive using **Code → Download ZIP** in the GitHub repository. If a release is available, use the **Releases** section.

The archive should contain `krita_color_mixer.desktop` and the `krita_color_mixer` folder.

## Installation

1. Close Krita.
2. Copy `krita_color_mixer.desktop` and the `krita_color_mixer` folder into Krita's `pykrita` directory:
   - **Windows:** `%APPDATA%\krita\pykrita`
   - **Linux:** `~/.local/share/krita/pykrita`
   - **macOS:** `~/Library/Application Support/Krita/pykrita`
3. Launch Krita and enable **Color Mixer Studio** under **Settings → Configure Krita → Python Plugin Manager**.
4. Restart Krita.
5. Open the dockers from **Settings → Dockers**:
   - **Color Mixer Studio**
   - **Color Mixer: Palettes**

Create the `pykrita` directory if it does not exist. The plugin uses the Python and PyQt packages bundled with Krita; no additional Python packages are required.

## Color Mixer Studio

The mixer docker has two color pickers: **Start Color** and **End Color**.

- Pick a color using the hue and saturation wheel, or adjust its brightness with the slider.
- Enter or edit HEX and RGB values; the HSL value is displayed alongside them.
- Use the screen picker to sample a color from anywhere visible on screen.
- Generate a gradient between the two colors in **OKLCH**, **LAB**, or **RGB** color space.
- Set the number of intermediate steps from 1 to 15.
- Choose a color label format: **HEX**, **RGB**, or **HSL**.
- Click the brush button next to a color to apply it as Krita's foreground color. The color's HEX value is also copied to the clipboard.

## Color Mixer: Palettes

### Color harmonies

Generate a palette from the current **Start Color** using these schemes:

- Complementary
- Triadic
- Analogous
- Split-Complementary
- Monochromatic

Generated colors can be applied as Krita's foreground color.

### Images and manual selection

Load an image or click **Snip Screen** to capture a rectangular area of the screen. **Image mode** determines what happens when you click the preview:

- **Start Color** — send the selected color to the start color picker.
- **End Color** — send the selected color to the end color picker.
- **Extract Palette** — extract a palette of the most frequently occurring colors.
- **Custom Palette (Manual)** — fill palette slots by manually selecting colors from the image.

Palette extraction options:

- **Extract Colors** — desired number of colors, from 2 to 16.
- **Sort extracted colors** — sort by frequency, hue, or brightness.
- **Merge tolerance** — threshold for merging similar colors using CIE76 Delta E. A value of zero keeps only exact matches; increasing it merges more similar colors. The resulting palette may contain fewer colors than the **Extract Colors** value.

For a manual palette, set between 2 and 16 slots. Click a slot to select it, then click the desired point in the image. After a slot is filled, the plugin advances to the next empty slot. **Clear Manual** clears the slots.

### Color difference and contrast

In **Color difference and contrast**, choose two colors from the current palette:

- The preview displays the first color as text and the second as the background.
- **CIE76 color difference** shows the numerical difference between the colors in CIELAB.
- **Contrast** shows the contrast ratio and an evaluation against WCAG thresholds for normal or large text.

The WCAG evaluation can help assess text readability against the selected background. It is not a complete accessibility audit and does not replace checking colors in their actual design context.

### Exporting palettes

- **Add Palette as Layer (64x64)** creates a raster layer in the active Krita document. Colors appear in a horizontal row, each as a 64×64-pixel block with no gaps.
- **Save Palette as PNG** saves the same horizontal palette strip as a PNG.

An open document is required to add a layer. All manual palette slots must be filled before export.

## Limitations

- Palette extraction is available from a loaded image or a captured screen area. Direct extraction from the active layer, the whole document, or a Krita selection is not currently supported.
- Contrast is evaluated for the selected pair of colors; the result depends on which color is chosen as text and which as background.
- Color presets and CSS copying are not included.

## Project files

- [Plugin manual](./krita_color_mixer/Manual.html)
- [Krita plugin descriptor](./krita_color_mixer.desktop)
- [Source code](./krita_color_mixer/krita_color_mixer.py)
- [Krita Artists Resources category](https://krita-artists.org/c/resources/10)

Created by **Dj YX**. [Support the project](https://donatello.to/Dj_YX).
