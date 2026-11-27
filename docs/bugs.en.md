# Bug Library · Public Edition

[中文](bugs.zh.md) · [English](bugs.en.md)

Failures collected while producing English versions of Chinese motion films. Grouped by where they bite: motion and layout, export, then the localisation/draft work.

Each entry states the symptom, the cause, and the rule that prevents a repeat. IDs follow the internal ledger, so gaps are simply entries not published here.

> All entries come from delivered work. Local paths and file inventories are removed; the checks are kept, because a check transfers and a conclusion does not.

## Motion and layout (DB-01 – DB-30)

### DB-01 · An absolutely positioned sibling covers the label written before it

**Symptom:** a status badge at the top-right of every thumbnail was invisible, although the CSS was correct.
**Cause:** the badge `span` came first in the DOM, the thumbnail `div.pad` came second; both absolutely positioned, so DOM order decided who painted on top.
**Rule:** among same-level absolute siblings, order comes from the DOM; `z-index` is only for escaping the level. After writing one, ask what absolute element comes after it. Check: `document.elementFromPoint()` at the badge centre must return the badge.

### DB-02 · `aspect-ratio` derives height from width and overflows fixed-height containers

**Symptom:** a 16:9 box inside a grid cell (400 wide, 150 tall) computed 225 px high and pushed into the footer.
**Cause:** `width:100%; aspect-ratio:16/9` in a container whose height is fixed.
**Rule:** `aspect-ratio` is for containers where width is free and height follows. In grid cells and fixed slots, set both dimensions explicitly.

### DB-03 · A structure line drawn in the divider colour is invisible on a dark panel

**Symptom:** none of the connector lines on a dark diagram appeared. Half an hour went into checking the SVG DOM.
**Cause:** `stroke="var(--line)"` — a colour meant to separate two surfaces, not to be seen on its own.
**Rule:** "structure line" describes a purpose, not a brightness. On a dark background use the next brighter step. Check: scale the image to 25% and ask whether the line is still there.

### DB-04 · `.k` collides: fine on light panels, white pills on dark cards

**Symptom:** four key labels inside a dark card rendered as white rounded pills covering their text; the same markup on a light panel looked fine.
**Cause:** a single-letter class name reused by a component library.
**Rule:** never use one-letter class names. `.k`, `.v`, `.t` will be reused by something else in the same project. Check the page on the darkest surface available — dark backgrounds expose stray fills.

### DB-05 · `.chip` collides: a component-library pill name is not a colour block

**Symptom:** eight colour blocks meant to be full-width 96 px squares rendered as 36 px vertical strips.
**Cause:** the local class reused the kit's `.chip`, which carries `display:inline-flex` and padding.
**Rule:** don't reuse kit semantic names (`.chip`, `.card`, `.tag`, `.badge`) for local elements. If you must, check whether the class already sets `display` or `height`.

### DB-06 · A camera keyframe cannot end one segment and start a hard cut at the same time

**Symptom:** the "push in on P4" shot never pushed; it stayed wide for its whole duration.
**Cause:** the same timestamp served as the end of one camera interval and the `cut` start of the next.
**Rule:** `cut` belongs to the start of an interval and needs its own timestamp. Leave one frame (1/30 s) between them, or keep two tables: segments and intra-segment camera.

### DB-07 · `ease` belongs to the first frame of an interval

**Symptom:** a push-in configured with a snap ease played as a plain ease-in-out and barely moved for the first 0.3 s.
**Cause:** the easing was written on the end keyframe.
**Rule:** interval properties (easing, duration, direction) go on the start keyframe. Check: swap the easing for an extreme one — if the rhythm does not visibly change, the property never took effect.

### DB-08 · A HUD container without an `id` silently drops nine CSS selectors

**Symptom:** eight HUD modules never appeared. `querySelectorAll('#hud2 > *').length` returned 13, opacity was 1, the screen was empty.
**Cause:** CSS addressed children by id (`#grid15`, `#bits`…), JS created the elements without ids.
**Rule:** if CSS uses id selectors, JS must set ids. Check: `document.getElementById('grid15') !== null`, or use classes on both sides.

### DB-09 · The same comment anchor exists in both CSS and JS, and `replace` hits the wrong one

**Symptom:** the page went white with `SyntaxError: Private field '#term' must be declared in an enclosing class`.
**Cause:** a text replacement anchored on a comment string that appeared twice.
**Rule:** never anchor a replacement on comment text. Include surrounding code, or address by function name or line range. The same sentence easily exists in both a stylesheet and a script.

### DB-10 · A threshold carries the background it was calibrated on

**Symptom:** the final-frame check "pixels brighter than 90 should be 2–40%" measured 84% and failed.
**Cause:** the threshold was calibrated for a dark frame; this frame was light.
**Rule:** absolute thresholds (luminance, area, contrast) are relative to a background. Re-calibrate when the background changes, and ask what a number was measured against before reusing it.

### DB-11 · Ink density cannot measure a light-background frame

**Symptom:** ten groups of vector elements were added to a light frame; ink (pixels deviating >48 from background) moved from 4.1% to 5.3%.
**Cause:** thin white/grey lines barely move an ink metric.
**Rule:** use ink for dark or solid frames, edge density (first derivative >12) for light frames with thin lines. Report both; they are not interchangeable.

### DB-12 · `.fbox` carries `z-index:2`, so a later full-screen vector layer paints underneath

**Symptom:** a full-screen `<svg>` appended last to `#world` never showed; opacity was 1, rect was correct, console was clean.
**Cause:** the SVG had no stacking context of its own and lost to a component with `z-index:2`.
**Rule:** "element exists, opacity 1, invisible" starts with the z-index stack, not the DOM. Also check that the element is positioned — `z-index` does nothing on `position:static`.

### DB-13 · Group-level `opacity` silently erases per-element windows

**Symptom:** two elements that should fade out individually stayed visible, or vanished early, depending on the loop order.
**Cause:** `VG[k].style.opacity = on ? 1 : 0` in a loop, then a later line set the group back to 1.
**Rule:** one property, one writer. Per-element fade multiplies into the group value (`q * f1`); never assign group opacity in a second place. "Just one more line" is the entire source of this bug.

### DB-14 · A vector layer's window must end with its group's fade

**Symptom:** a card had faded out at 33.18, but its vector label `01` floated over the frame until 33.65.
**Cause:** the decoration window ended at the next scene's start instead of the group's fade end.
**Rule:** decorations layered over content take their end from the content group's fade-out, not from the next cut.

### DB-15 · "Group visible" must come after "group in place"

**Symptom:** one frame flashed during a vertical push: a row of audio cards appeared on top of the browser window.
**Cause:** the group's visible window began 0.02 s before the push animation moved it into place.
**Rule:** for groups pushed in from off-screen, `ON` starts at or after the push start and `OFF` ends at or before the push end. One frame of difference is a visible flash.

### DB-16 · Hard cut plus an already-faded-in element equals two titles on top of each other

**Symptom:** two lines of text occupied the same position at 25.95, looking like a render fault.
**Cause:** the outgoing element was cut, not faded, and the incoming one had already appeared.
**Rule:** in a transition, decide the order of disappearance: subject first, attachments after; attachments must never outlive their subject. Give the incoming element a place to land before it shrinks into position.

### DB-17 · A vector layer does not inherit its group's transform

**Symptom:** during a vertical push, the page content moved but its vector elements stayed behind, floating over the new page.
**Cause:** decorations were siblings of the transformed group, not children of it.
**Rule:** schedule decoration lifetimes against content settling, not against cuts. Close the outgoing side before the content leaves; open the incoming side after it lands.

### DB-18 · Push distance is not "one screen"

**Symptom:** 0.83 s of near-empty frame in the middle of a push (edge density 2.2‰).
**Cause:** the offset was set to a full screen height, larger than the actual content height, so both pages left the frame at once.
**Rule:** compute the distance from the two pages' content extents so they overlap mid-push (`D ≤ outgoing content bottom − incoming content top`). Add a late fade to the outgoing page as well.

### DB-19 · The incoming page must start with the push, not after it

**Symptom:** the frame was empty right after the push finished; the next page appeared later.
**Cause:** incoming elements were scheduled at the push end.
**Rule:** a page change is a relay, not a handover. The incoming element starts moving before the outgoing one lets go.

### DB-20 · A full-screen decoration layer must not live inside a layout-offset container

**Symptom:** corner ticks on a blueprint background showed only their lower halves; edge rulers lost their top segment.
**Cause:** the decoration SVG was placed inside `#world`, which carries a layout offset.
**Rule:** full-screen decorations hang directly under `#stage`, outside the offset container, and use frame coordinates.

### DB-21 · A group window that starts after its earliest element eats the fade-in

**Symptom:** 0.23 s of near-empty frame; moving an element 0.12 s earlier changed nothing.
**Cause:** `VWIN[3]` began at 7.63 while its first element entered at 7.56; the group's `opacity:0` swallowed it.
**Rule:** the window start is the earliest element's entry, not the page's nominal start. With DB-24, the window must enclose every element in the group.

### DB-22 · Multiplying `opacity` every frame drives it to zero

**Symptom:** elements meant to fade over 0.18 s disappeared within two seconds.
**Cause:** `el.style.opacity = parseFloat(el.style.opacity) * k` inside the render loop.
**Rule:** compute opacity as a pure function of `t` and assign once per frame. Never read back a style you wrote last frame.

### DB-23 · Cross-fades written as "A ends where B starts" leave a blank at the seam

**Symptom:** four swap points each went fully white for 0.2–0.5 s.
**Cause:** adjacent windows touched end-to-start, so both images had opacity 0 at the boundary.
**Rule:** the outgoing window must end at or after the incoming window starts, overlapping by at least one fade duration. Touching endpoints guarantee a blank midpoint.

### DB-24 · A group window that ends after its last element leaves shows an empty board

**Symptom:** 1.8 s of blueprint background between two pages.
**Cause:** group window ended at 14.72 while the last element left at 12.92.
**Rule:** the window end must not exceed the last element's exit. Enclose the group on both sides — see DB-21 for the start.

### DB-25 · One throw stops the whole `<script>`, and hoisting makes it look alive

**Symptom:** calling `render(1.9)` failed with a TDZ error about `ONS`, unrelated to the real fault.
**Cause:** a `TypeError` inside `markBox` aborted the script; function declarations were hoisted, so the page still looked partially functional.
**Rule:** wrap `render` in try/catch so one fault cannot kill the film, and watch the browser's `pageerror` event during capture — not just whether `render` is callable.

### DB-26 · "Show the finished frame, then disassemble it" is a semantic error

**Symptom:** a full file list was visible at t=0.22, then two rows were punched out at t=0.95. The owner's note: "why show it complete and then do the effect again?"
**Cause:** the animation started from the finished state and replayed assembly.
**Rule:** any assembly animation starts from the missing state. Showing the answer first makes every later move redundant.

### DB-27 · A row slot and its `background-position` must derive from the same y

**Symptom:** each punched hole displayed the previous row's fragment, offset by 34 px.
**Cause:** slot position and background offset were computed from two different origins.
**Rule:** when an element's position and its inner content offset depend on one baseline, that baseline is computed once and reused.

### DB-28 · Ask which coordinate system a design spec uses

**Symptom:** a spec gave `{top: 385.9, bg: '-160.3px -217.9px'}`; rows rendered one row off.
**Cause:** `bg` was the position inside the crop window, not an image offset: `385.9 − 168 = 217.9`.
**Rule:** before coding a coordinate table, subtract two known quantities and see which number you get. Every later adjustment inherits the baseline you chose here.

### DB-29 · Group windows must tile with only a frame-level gap

**Symptom:** two stretches of 1.7 s and 2.37 s had no edges at all — an empty board.
**Cause:** no group was "on duty" between windows.
**Rule:** at any timestamp exactly one group owns the frame. Gap ≤ 0.10 s; overlap means two visual languages on screen at once.

### DB-30 · Hard-wrapping subtitles by character count breaks mid-sentence

**Symptom:** all technical checks passed, but the owner re-cut 15 lines by hand: "it's still not breaking at periods."
**Cause:** the splitter cut at the 60th character, ignoring grammar, producing lines like `...for the call at a` / `target 15 fps,`.
**Rule:** break at periods, then semicolons, commas, clause starts, before prepositional phrases. Never after an article, preposition, conjunction, "be" or intensifier. Character count is a ceiling only; if you hit it mid-phrase, walk back to a legal break. Subtitle breaks are invisible to timing checks — audit them separately.

## Export and frames (DB-INTRO)

### DB-INTRO-01 · An opaque PNG written as RGB is not an alpha failure

**Symptom:** the alpha gate rejected frame 0 because it was PNG colorType 2 (RGB). The first 179 frames were RGB, later frames RGBA.
**Cause:** Chrome writes opaque frames as RGB; the gate assumed every frame must be RGBA.
**Rule:** allow opaque frames at the head. Normalise the intermediate sequence to RGBA (keep RGB channels, add A=255) for a stable pixel format, and still read alpha=0 back from the MOV. An opaque frame is the negative control, not a failure. Never substitute "PNG has an alpha channel" for checking MOV pixels.

### DB-INTRO-02 · Count frames per output; correct duration still loses frames

**Symptom:** three encodes reported 15.5 s, but the static preview had 462 frames instead of 465; a normalised overlay lost one frame at EOF.
**Cause:** two separate issues — RGBA normalisation and a framesync boundary at EOF.
**Rule:** set input RGBA and explicit PTS/CFR, clone a tail buffer on the overlay foreground, and hard-trim with `-frames:v N` plus `-t`. Verify by counting frames, not by reading duration. Short tests that cross a boundary and land on EOF, 30 frames each, catch both.

## Localisation and the edit (DB-31 – DB-44)

### DB-31 · The render bakes the player UI into the film

**Symptom:** two clips rendered as a full-screen cover play button; others carried Play/Replay, a progress bar, or a timecode.
**Cause:** two layers. The renderer's `--query` flag was passed only to the stills path, so the main render received no query string; and the pages had inconsistent bare-mode conventions — one had none at all, and its `.preview` was fixed at 1320 px, cropping the 1920 stage.
**Rule:** every player page needs a bare mode (`?t=` for stills, `?export` for the full film) that hides cover, controls and toolbars. Verify the flag reaches the main render path. Check: sample a frame and inspect the bottom 60 px — that is where progress bars live, and the middle always looks fine.

### DB-32 · PSRAM read letter by letter

**Symptom:** the acronym was spoken as P-S-R-A-M instead of "pee ess ram".
**Cause:** edge-tts expands all-caps tokens letter by letter.
**Rule:** write `P S ram` (spaces, lowercase "ram"); the word boundaries become three tokens. `P-S-ram` fails because it stays one token. Same for SPIRAM and the RAM part of QSPI.

### DB-33 · A replaced video plays silent, even with `has_audio=True`

**Symptom:** no waveform on the timeline, no sound, while the material reported `has_audio=True` and the segment volume was +5 dB.
**Cause:** three layers: Jianying does not build an audio cache for an mp4 written by a script; the new audio material was created from a `sound` template, and that type does not read local files (flat waveform, no error); and the path contained `..`, which Python resolves but the loader does not.
**Rule:** always split audio out. Extract to mp3 192k, create the material with `type='extract_music'`, normalise the path, and copy the segment template from a known-good voice segment. Set the video segment volume to 0. Check: waveform present, material mean ≈ −17 dB, zero overlap on the narration track.

### DB-34 · Replacing whole clips and re-timing the film is the wrong direction

**Symptom:** the first English pass lengthened the film by 9 s and moved every hand-made cut.
**Cause:** treating the English animation as a standalone film instead of a replacement shot inside an existing edit.
**Rule:** cut the English clip to the Chinese segment's exact duration, position and start. Keep the video silent and let the existing voice track carry the audio. Runtime must equal the original unless a segment is explicitly deleted; every replaced segment's `target.start` must match the pre-change value.

### DB-35 · Narration numbers disagree with the picture

**Symptom:** the frame said 32 MB PSRAM, the voice said "8 megabytes".
**Cause:** the spec sentence was typed from memory, not copied from the frame. Changing the number also invalidated the word anchor used to place it.
**Rule:** copy spec numbers from the picture. When a number changes, update the word anchor too, then rebuild and re-render (the audio is embedded in the HTML). Check: sample the frame at that timestamp and compare digit by digit — a wrong number is not audible as an error, only as something slightly off.

### DB-36 · Subtitles copied from Chinese timing while the voice was re-timed

**Symptom:** subtitles ran 2.5 s ahead of the voice at the start; the second half drifted the other way.
**Cause:** subtitle text was replaced but its timing kept, while the voice was re-scheduled to English speed — two independent timelines.
**Rule:** dialogue subtitles follow speech; on-screen labels follow picture. Build subtitles from word timestamps: start = voice start + first word offset, end = last word end. Count may change. Check every subtitle against the voice segment that covers it: start ∈ [voice start − 0.2, voice start + duration].

### DB-37 · Subtitle text and spoken words diverge (cache key without text, audit without content)

**Symptom:** three lines showed one sentence while the voice said another; timing was perfect, so the timeline looked correct.
**Cause:** the TTS cache was keyed by segment index and rate only. After editing the text, the old audio was reused while subtitles used the new text. The audit checked coverage, never content.
**Rule:** include `md5(text)[:6]` in the cache filename. Add a word-level comparison to the audit: normalise both sides to word sets, diff words longer than two characters; more than two missing on either side is a failure. Timing checks cannot see this class of bug.

### DB-38 · "English is longer" was silence and track structure, not speaking rate

**Symptom:** the first half ran 1.3–2.2 s late, twice reported as "not aligned with the Chinese".
**Cause:** edge-tts leaves 0.77–0.80 s of silence at the end of every segment (22 s across 29 segments), and 29 segments spread over three tracks were scheduled as one sequence, although the Chinese original allows cross-track overlap.
**Rule:** trim trailing silence before scheduling; keep a separate cursor per track. The schedule table should contain no `pushed +x.xx`. If it does, check those two things before touching the text.

### DB-39 · Cutting the verb to fit the duration removed the point of the opening

**Symptom:** the opening became a model number with no statement of what the video does.
**Cause:** the verb ("this video shows") was dropped to save 0.6 s.
**Rule:** never delete verbs, actions or qualifiers (official, compatible, support). Compress particles, repetition and optional connectives only. If it still doesn't fit, use engineering: trim silence, schedule per track, raise the rate. Ask before cutting meaning.

### DB-40 · Translation loses the premise: `or` with nothing to choose, manual read as automatic, `down` read as offline

**Symptom:** three cases — `It is open source, or clone it on GitHub` (the left side is a state, not an option); `Brightness follows the light` (the original says the user adjusts it); `Even with the C61 down` (down means broken, not disconnected).
**Cause:** word-level mapping without checking the logic of the sentence.
**Rule:** for `or/but/so/because`, find the left-hand item and confirm it is the same kind. For "can adjust / supports", decide manual versus automatic. For state words, pick by observed behaviour: `offline` or `never connects` for a network, `down` only for a dead component.

### DB-41 · A chapter animation opened with the film's opening line

**Symptom:** the HARDWARE title played while the voice said "today we turn the board into a teleprompter".
**Cause:** the chapter's audio was assembled as "block 1 + block 3 + spec + block 4", and block 1 belonged to the film intro, already spoken at 0.3 s.
**Rule:** the first sentence of a chapter animation must be about that chapter. Before assembling, ask where the line sits in the whole film; if it was already said, it does not belong here.

### DB-42 · English copy overflows the frame because row width was hard-coded for Chinese

**Symptom:** `INTRODUCTION` lost its first letter and the model name lost its last, both at the frame edge.
**Cause:** `openingWidths` was fixed at the width of the three-character Chinese subject; the layout only centred the row and never tested for overflow, so `left` went negative.
**Rule:** measure at runtime (`offsetWidth`) and scale down to the available width when the row does not fit. Check the locked frame with `--stills`, not the middle of the shot; text must sit ≥ 40 px from the left and right edges. Any coordinate derived from Chinese character counts must be re-measured for English.

### DB-43 · An English cut longer than the Chinese pushes every later picture and subtitle

**Symptom:** one segment was 25.5 s against a 21.47 s original; the next clip moved from 128.1 to 132.1, and the film grew from 206 to 213.6 s.
**Cause:** duration was treated as adjustable.
**Rule:** duration is the edit's contract. Compress in this order — trim trailing silence, shrink gaps, raise the rate (≤ +15%), warp the animation to the Chinese timeline. If it still does not fit, ask. Runtime may only change when a whole segment is added or deleted.

### DB-44 · Two copies of the motion code: external `.js` and inlined HTML

**Symptom:** the build printed `EN_FRAMES=644 (21.47 s)`, but the rendered video still read 25.10 and the audio did not match.
**Cause:** the single-file page inlines its JS; an external copy also sits in the folder. The build edited the external file, the renderer read the inlined one. No error.
**Rule:** at the end of the build, write `EN_FRAMES`, the warp table and the render function into the HTML and grep them back. Before rendering, the HTML's frame count must equal the build's printed value; after rendering, `ffprobe` duration must equal frames / 30. "Build succeeded" does not mean "the artefact is new".
