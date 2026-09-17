# App Knowledge Pack & Dashboard (Phase 1)

This module implements the **App Knowledge Pack** storage layer, the **Navigation Graph**, the **Screen Reconstruction Engine**, and the web-based **Dashboard** for the `zero-touch-app-understanding` project.

---

## 1. Overview

The **Knowledge Pack** serves as the machine-readable digital blueprint of an explored Android application, recording:
- Discovered screens and their semantic purposes
- UI elements and their interaction bounds
- Possible actions and transitions
- Full application navigation graph
- Design system tokens (colors, typography, layout)

The **Dashboard** is a web interface for inspecting the Knowledge Pack and demonstrating autonomous screen reconstruction to judges.

---

## 2. Directory Structure

```text
zero-touch-app-understanding/
├── knowledge/
│   ├── __init__.py                # Module exports
│   ├── models.py                  # Dataclass models (ScreenData, UIElementData, AppKnowledgePack)
│   ├── builder.py                 # KnowledgeBuilder: updates pack, builds graph, exports/loads JSON
│   ├── sample_knowledge_pack.json # Realistic 5-screen exploration fixture
│   └── tests/
│       ├── __init__.py
│       └── test_builder.py        # Unit tests for builder and serialization
└── dashboard/
    ├── index.html                 # 3-column dashboard UI
    ├── styles.css                 # Dark-mode design system
    ├── app.js                     # Dashboard interaction, graph rendering & overlay inspector
    ├── reconstruct.js             # Autonomous Screen Reconstruction Engine
    └── README.md
```

---

## 3. Running the Dashboard

You can run the dashboard locally using Python's built-in HTTP server:

```bash
# From the repository root
python -m http.server 8000
```

Then open your browser and navigate to:
[http://localhost:8000/dashboard/](http://localhost:8000/dashboard/)

> **Note:** The dashboard includes an embedded fallback of `sample_knowledge_pack.json`, so it also functions if you directly double-click `dashboard/index.html` in your file browser without a server. You can also import any custom JSON using the **Import JSON** button in the header.

---

## 4. Key Dashboard Features

1. **Header & KPI Metrics**:
   - Displays application name, package identifier, exploration status, and live counters for total discovered screens, UI elements, and navigation transitions.
2. **Interactive Topology Graph (App Map)**:
   - Visualizes the application's directed navigation graph (`Login → Home → Search → Product` and `Home → Profile`).
   - Clicking any node in the graph instantly focuses that screen.
3. **Screen Viewport (Dual Modes)**:
   - **Screenshot & BBox View**: Shows screen preview with hoverable/clickable bounding box overlays corresponding to individual UI elements.
   - **Reconstructed UI View**: Renders the screen dynamically in HTML/CSS using `reconstruct.js` derived purely from the Knowledge Pack's element bounds and types.
4. **Screen & UI Inspector**:
   - Inspects screen metadata (name, semantic purpose, Android Activity).
   - Lists all available actions and destination transitions.
   - Interactive UI elements table: hovering over any element highlights its corresponding bounding box on the screen preview.

---

## 5. Screen Reconstruction Engine

The reconstruction engine (`dashboard/reconstruct.js` and `KnowledgeBuilder.generate_reconstruction_data`) demonstrates that the Knowledge Pack stores sufficient structural fidelity to recreate the application UI without the original Android APK.

Supported component translations:
- `TextView` → Responsive typography headings, body text, ratings, and price tags.
- `Button` → Interactive styled action buttons.
- `EditText` → Form input fields with accessibility labels and placeholders.
- `ImageView` → Image placeholders with content descriptions.
- `CardView` / `ViewGroup` → Structured card components.
- `BottomNavigation` → Fixed bottom navigation bars.

---

## 6. Running Unit Tests

Run all unit tests from the repository root:

```bash
python -m unittest discover -s knowledge/tests -v
```

Expected output:
```text
Ran 12 tests in ~0.02s
OK
```
