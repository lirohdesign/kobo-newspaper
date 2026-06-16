# Kids source planning

This document audits current ideas against E-ink layout reliability, early reader vocabulary (ages 5–6), and pipeline maintenance friction.

## Map of ideas
- Drop it list: high-friction or unreliable external scraping ideas
- Keep it list: deterministic local or API-backed sources
- Pivots & fixes required: risky modules that need additional engineering
- APOD micro-story: NASA Astronomy Picture of the Day as text
- Math generator: localized daily math challenge module
- Would You Rather: local question bank for zero-scrape content
- Wikipedia On This Day: JSON-based historical events with LLM filtering
- Romance language module: local French/Portuguese vocabulary builder
- Weekly ukulele lesson: music module with layout concerns
- Keyboard / lead-sheet alternative: lead sheet source for simple melody display

## 1. Drop it list (High friction / unreliable)
- External Content Scrapers (Ducksters, DOGO, NatGeo Kids, etc.)
  - Reason: High risk. Web scraping commercial kids' blogs means constantly fighting paywalls, dynamic JavaScript layouts, and unexpected site changes that break your automation pipeline.
- Continuous Ukulele Tabs (ASCII Strings)
  - Reason: Replaced by the piano decision. Continuous text lines stretch horizontally, causing disastrous wrapping or clipping on a narrow 6-inch Kobo screen.

## 2. Keep it list (Rock solid / deterministic)
- Wikipedia "On This Day" API + LLM Filter
  - The endpoint is permanent. Passing the raw JSON payload to an LLM build step handles selection, historical filtering, and vocabulary down-sampling down to a kindergarten level in a single operation.

## 3. Pivots & fixes required

### 3.1 LilyPond Sheet Music Integration
- The plan: ingest LilyPond (`.ly`) files from The Mutopia Project.
- The fix: you cannot easily build a raw text "HTML wrapper" directly out of LilyPond source code without an intermediary. The backend engineering script must modify the file headers to override standard page dimensions, pass it to the command-line `lilypond` compiler, and drop a scaled, cropped vector graphic (`.svg`) into your `assets-kids/` folder for the HTML page to reference.

### 3.2 French & Portuguese Vocabulary Source
- The plan: include a daily language lesson.
- The fix: scraping high-quality children's dictionaries for simple definitions and exact phonetic guides is messy. Since you only need 365 entries to loop indefinitely, use an LLM one time to generate a pristine, structured JSON array of high-contrast noun pairs (e.g., animals, nature) with clean phonetic sound-outs, and bake it directly into your local database code.

## 4. APOD micro-story source

### 4.1 NASA Astronomy Picture of the Day
- Source: `https://apod.nasa.gov/apod/astropix.html`
- Don't think of this as an image source—think of it as a daily micro-story.

### 4.2 Content structure
- Every single day, a NASA scientist writes a single, short paragraph explaining a cool space photograph.
- The text is self-contained, highly descriptive, and usually under 150 words.

### 4.3 Why it's zero-thinking
- It updates chronologically every 24 hours without fail.
- Your script can ignore the image entirely (or pull it for a high-contrast E-ink render) and grab that single, clean paragraph from the RSS `<description>` tag to use as a daily "Cool Space Fact" section.

## 7. Wikipedia "On This Day" API module

### 7.1 Overview
A highly stable, public domain REST endpoint hosted by the Wikimedia Foundation that delivers curated historical events, births, deaths, and holidays for a specific calendar date. It serves as a zero-maintenance chronological feed, eliminating the risk of website layout shifts or scraper breakage common with scraping targeted children's blogs.

### 7.2 URLs
- Selected milestones: `https://en.wikipedia.org/api/rest_v1/feed/onthisday/selected/{month}/{day}`
- All historic records: swap `/selected/` for `/all/`

### 7.3 Format
Standard JSON payload. No authentication keys, headers, or rate-limiting secrets required for standard low-frequency build pipelines.

### 7.4 Core JSON schema & node hierarchy
The payload organizes data into a top-level array (`selected`). Each item represents an individual historic milestone with predictable fields:

```json
{
  "selected": [
    {
      "year": 1752,
      "text": "American polymath Benjamin Franklin conducted his famous kite experiment...",
      "pages": [
        {
          "title": "Kite_experiment",
          "extract": "The kite experiment is a scientific experiment in which...",
          "description": "Scientific experiment conducted by Benjamin Franklin",
          "thumbnail": {
            "source": "https://upload.wikimedia.org/...",
            "width": 320,
            "height": 240
          }
        }
      ]
    }
  ]
}
```

### 7.5 Key properties for LLM pipeline ingestion
- `data['selected']`: the target iteration array containing the day's historic milestones.
- `item['text']`: a clean, single-sentence summary linking the year to the core event. Ideal as a condensed contextual hook.
- `item['pages'][0]['extract']`: the full introductory paragraph from the event's primary Wikipedia article. Useful for an LLM to down-sample into a kid-friendly narrative.
- `item['pages'][0]['description']`: a short metadata descriptor, useful for filtering out dry or inappropriate nodes.
- `item['pages'][0]['thumbnail']['source']`: a direct image URL for optional high-contrast E-ink rendering or layout decoration.

## 8. Romance language module (French & Portuguese)

### 8.1 Approach
For early readers, focus on high-contrast noun pairs (e.g., big/small, hot/cold) or nature/animal words, paired with a simple phonetic guide so they can practice saying them out loud.

### 8.2 Code strategy
Store these in a local dictionary array inside your project. The pipeline uses the current day of the year to pull a fresh pair every morning.

```python
# language_bank.py
ROMANCE_VOCAB = [
    {
        "topic": "☀️ In the Sky",
        "fr": {"word": "le soleil", "sounds": "luh soh-lay", "eng": "the sun"},
        "pt": {"word": "o sol", "sounds": "oo sawl", "eng": "the sun"}
    },
    {
        "topic": "🌳 Nature",
        "fr": {"word": "l'arbre", "sounds": "lar-bruh", "eng": "the tree"},
        "pt": {"word": "a árvore", "sounds": "ah ar-voh-ree", "eng": "the tree"}
    },
    {
        "topic": "🐱 Animals",
        "fr": {"word": "le chat", "sounds": "luh shah", "eng": "the cat"},
        "pt": {"word": "o gato", "sounds": "oo gah-too", "eng": "the cat"}
    }
]
```

### 8.3 Output layout
```text
==================================================
              DAILY LANGUAGE CORNER
==================================================
Topic: 🌳 Nature

🇨🇦 FRENCH: 
   l'arbre  -->  "the tree"
   How to say it: [lar-bruh]

🇧🇷 PORTUGUESE: 
   a árvore  -->  "the tree"
   How to say it: [ah ar-voh-ree]
==================================================
```

### 8.4 Source question
- How do we get a good source on definition and pronunciation? Only need 365 entries to start, so a structured prior source would be ideal, but an AI-generated list is also acceptable.

## 9. Weekly ukulele lesson

### 9.1 Goal
Include a clean, authentic 4-line ukulele tablature lesson on the screen once a week, scaling up to a full 52-week curriculum.

### 9.2 Display requirement
The lesson must look exactly like standard tablature, using a monospace grid to align strings (A, E, C, G), fret numbers, and lyrics vertically.

### 9.3 Core problem
The major technical roadblock is horizontal screen overflow on narrow E-ink displays.
- Traditional ukulele tabs are long continuous text strings.
- When they hit the page width, they either truncate or wrap, scrambling vertical timing.

### 9.4 Engineering requirement
To avoid layout failures, the system must store songs as short, isolated measures (bars) that print vertically down the page rather than stretch across.

## 10. Keyboard / lead-sheet alternative

### 10.1 What this is
A lead sheet collection (or "Fake Book") is the simplest form of traditional sheet music: melody line plus chord symbols.

### 10.2 Why it may be better than uke
- Simpler than full piano score.
- Only melody and chord symbols.
- Works well for nursery rhymes, folk songs, and holiday music.

### 10.3 Good source candidates
1. Michael Kravchuk
   - Clean, beginner-focused children's music.
   - Offers lead sheets and easy piano arrangements.
2. The Mutopia Project
   - Open-source public domain sheet music.
   - Provides raw LilyPond files, which can compile into clean staff images.
3. Traditional Music Library
   - Archive of folk and traditional melodies with stripped-down arrangements.
4. Wikifonia Archives / OpenBook Collections
   - Archived collections of children's lead sheets and fake books.
   - Search for "Children's Lead Sheet Fake Book PDF" for stable, consistent formatting.
This format is the easiest transition point for your project because an AI or a simple parser can read the treble clef notes to generate a melody line, and read the chord letters above it to generate the companion ukulele chords.

## 11. Spot the Difference puzzle

This prototype is an SVG-based "spot the difference" puzzle designed for E-ink screens. It uses a master image on the left and a modified copy on the right, hiding a few simple line-art elements to create the challenge.


2. The Mutopia Project (mutopiaproject.org)
Traditional sheet music layouts are designed for large print sizes or landscape screens. If a standard 8.5" x 11" page is dropped onto a narrow 6-inch E-ink screen, the musical staff and text compress into an unreadable, blurry mess.
Engineering Requirement
To ensure high-visibility on low-power displays without requiring user zooming, the compilation process must override the default LilyPond page layout rules. The automation pipeline needs to inject explicit layout overrides directly into the top of the file before rendering:
Custom Page Width: Set the paper size to match the exact pixel width of the target viewport.
Aggressive Staff Scaling: Force a large staff size (e.g., #(set-global-staff-size 26)) so the lines, notes, and lyric fonts are chunky and high-contrast.
Vertical Fluidity: Set the layout height to indefinite or multi-page so LilyPond automatically calculates line breaks based on the narrow width, stacking the measures vertically down the page.


<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Kobo Kids - Spot the Difference Prototype</title>
    
    <!-- 
      METADATA & PIPELINE REFERENCES
      ==========================================================================
      Primary Objective: Programmatic asset pipeline for monochrome E-ink screens.
      
      Recommended Master SVG Repositories:
      1. Lucide Icons (Formerly Feather Icons)
         - Repo: https://github.com/lucide-icons/lucide
         - Why: 100% uniform 2px stroke vectors, no fills, perfectly semantic.
         - Targets: /icons (e.g., home.svg, cloud-sun.svg, bird.svg, car.svg)
      
      2. FontAwesome Free (Solid/Regular Stroke variants)
         - Repo: https://github.com/FortAwesome/Font-Awesome
         - Why: Massive library of universally recognizable real-world objects.
         - Targets: /svgs/regular for clean, unfilled outlines.

      Data / Architecture Concept:
      - Raw Asset: Download clean master outlines into `assets/raw_vectors/`.
      - Build Task: Python script copies the master SVG twice. On the second 
        copy, it parses the XML with BeautifulSoup/lxml, targets 2-3 random 
        child tags (paths, circles), and injects `display="none"` or drops them.
    -->

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #fff;
            color: #000;
            text-align: center;
            padding: 20px;
        }

        h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }

        p {
            font-size: 16px;
            color: #555;
            margin-bottom: 25px;
        }

        /* Side-by-side container for the Kobo screen width */
        .puzzle-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            max-width: 800px;
            margin: 0 auto;
        }

        .panel {
            border: 2px solid #000;
            padding: 15px;
            background: #fff;
        }

        /* Bold, clean line art styles for E-ink */
        svg {
            width: 100%;
            height: auto;
            max-height: 300px;
        }

        /* Global line art rules */
        path, circle, line {
            stroke: #000;
            stroke-width: 3;
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
        }

        /* Class used by Python or JS to programmatically drop elements */
        .difference {
            display: none !important;
        }
    </style>
</head>
<body>

    <h1>Spot the 3 Differences!</h1>
    <p>Can you find the three things that are missing in the right picture?</p>

    <div class="puzzle-container">
        <!-- LEFT PANEL: THE MASTER IMAGE -->
        <div class="panel" id="original">
            <!-- A simple compound SVG scene: House, Sun, Cloud -->
            <svg viewBox="0 0 400 300">
                <!-- Sky Details -->
                <circle cx="60" cy="60" r="25" /> <!-- Sun Body -->
                <line x1="60" y1="20" x2="60" y2="10" class="diff-1" /> <!-- Sun Ray 1 -->
                <line x1="60" y1="100" x2="60" y2="110" class="diff-1" /> <!-- Sun Ray 2 -->
                <line x1="20" y1="60" x2="10" y2="60" class="diff-1" /> <!-- Sun Ray 3 -->
                <line x1="100" y1="60" x2="110" y2="60" class="diff-1" /> <!-- Sun Ray 4 -->
                
                <!-- Cloud -->
                <path d="M 300 70 A 20 20 0 0 1 340 70 A 25 25 0 0 1 370 90 A 20 20 0 0 1 350 110 L 290 110 A 20 20 0 0 1 300 70 Z" />

                <!-- House Frame -->
                <rect x="130" y="140" width="140" height="120" style="stroke:#000; stroke-width:3; fill:none;" />
                <!-- Roof -->
                <path d="M 110 140 L 200 60 L 290 140 Z" />
                <!-- Door -->
                <rect x="180" y="200" width="40" height="60" style="stroke:#000; stroke-width:3; fill:none;" />
                <circle cx="210" cy="230" r="3" class="diff-2" /> <!-- Doorknob -->

                <!-- Windows -->
                <rect x="150" y="160" width="30" height="30" style="stroke:#000; stroke-width:3; fill:none;" />
                <rect x="220" y="160" width="30" height="30" style="stroke:#000; stroke-width:3; fill:none;" class="diff-3" />
            </svg>
        </div>

        <!-- RIGHT PANEL: THE MODIFIED IMAGE -->
        <div class="panel" id="challenge">
            <!-- This will load the exact same SVG structure -->
        </div>
    </div>

    <script>
        // 1. Clone the master SVG over to the challenge side
        const masterSvg = document.querySelector('#original svg').cloneNode(true);
        document.getElementById('challenge').appendChild(masterSvg);

        // 2. Programmatically apply the 'difference' class to specific tagged selectors
        const challengePanel = document.getElementById('challenge');
        
        challengePanel.querySelectorAll('.diff-1').forEach(el => el.classList.add('difference')); // Remove Sun Rays
        challengePanel.querySelector('.diff-2').classList.add('difference');                     // Remove Doorknob
        challengePanel.querySelector('.diff-3').classList.add('difference');                     // Remove Right Window
    </script>

</body>
</html>


