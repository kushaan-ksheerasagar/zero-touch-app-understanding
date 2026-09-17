# Zero-Touch App Understanding
## Project Specification

Version: 1.0
Status: Initial Build

---

# 1. PROJECT OVERVIEW

We are building an AI system that can take an Android application that it has never seen before, explore the application autonomously, understand its screens and interactions, and create a structured representation called an App Knowledge Pack.

The goal is to reduce the need for humans to manually document how an Android application works.

The system should behave like an AI explorer.

It should:

SEE → UNDERSTAND → DECIDE → ACT → REMEMBER → REPEAT

At the end of exploration, the system should know:

- What screens exist
- What UI elements exist on each screen
- What those elements do
- How screens connect to each other
- What actions are possible
- What the application's visual/design language looks like

This information is stored in an App Knowledge Pack.

---

# 2. PROBLEM WE ARE SOLVING

AI agents need to understand applications before they can reliably operate them.

Currently, understanding an application can require manually documenting:

- Screens
- Buttons
- Inputs
- Navigation
- User flows
- Visual components
- Application states

This becomes difficult when an application changes.

Our system aims to automatically discover this information.

Instead of:

Human → manually documents app → AI uses documentation

we want:

Android App → AI explores app → Knowledge Pack → AI can understand app

---

# 3. CORE PRODUCT

Our product has four major components.

## 3.1 Android Controller

Controls the Android application.

It should eventually support:

- Launching an application
- Taking screenshots
- Reading available UI information
- Tapping elements
- Scrolling
- Entering text
- Pressing back
- Waiting for screen changes

The controller should NOT decide what to do.

It only executes actions requested by the agent.

---

## 3.2 Perception System

The perception system observes the current application state.

Inputs:

- Android screenshot
- Android UI information/tree
- Current application state

Outputs:

- Detected UI elements
- Element types
- Text/labels
- Positions
- Available actions
- Screen description
- Screen purpose

The perception system should combine structured UI information with visual understanding where necessary.

---

## 3.3 Autonomous Exploration Agent

This is the brain of the system.

The agent receives:

- Current screenshot
- Structured UI elements
- Current screen description
- Previously visited screens
- Previously performed actions
- Available actions
- Exploration goal

The agent decides what action should happen next.

Possible actions initially include:

- TAP
- TYPE
- SCROLL
- BACK
- WAIT
- STOP

The agent should prioritize previously unexplored functionality.

The agent should avoid repeatedly performing actions that lead to already-known states.

The agent should not perform destructive or irreversible actions unless explicitly permitted in the test environment.

---

## 3.4 Knowledge Builder

The Knowledge Builder converts exploration results into an App Knowledge Pack.

The Knowledge Pack should contain:

- Application information
- Screens
- Screen descriptions
- UI elements
- Element purposes
- Available actions
- Navigation relationships
- Visual/design information
- Exploration metadata

The Knowledge Pack should be structured, compact, machine-readable, and reusable.

---

# 4. AGENT LOOP

The core agent loop is:

1. Observe the current screen.
2. Capture a screenshot.
3. Extract available UI information.
4. Understand the current screen.
5. Identify possible actions.
6. Check exploration memory.
7. Select the most useful unexplored action.
8. Validate the action.
9. Execute the action.
10. Wait for the application state to update.
11. Observe the new state.
12. Record the transition.
13. Repeat.

Conceptually:

Android App
    ↓
Observe
    ↓
Understand
    ↓
Decide
    ↓
Validate
    ↓
Act
    ↓
New Screen
    ↓
Remember
    ↓
Repeat

---

# 5. EXPLORATION GOAL

The primary goal is not simply to click as many things as possible.

The agent should maximize useful application understanding.

It should prioritize:

1. Previously unexplored screens
2. Previously unexplored navigation paths
3. Important interactive elements
4. Forms and input fields
5. Main application functionality
6. Relevant visual/design information

The agent should minimize:

- Repeated actions
- Infinite loops
- Duplicate screens
- Unnecessary navigation
- Destructive actions
- Random exploration

---

# 6. APPLICATION STATE

The system must maintain memory of what it has discovered.

At minimum, memory should contain:

## Visited screens

Example:

- Login
- Home
- Search
- Product
- Profile

## Explored actions

Example:

Home → Search
Home → Profile
Search → Product

## Unexplored actions

Example:

Home → Cart
Home → Settings

## Failed actions

Example:

Search → Product failed once

---

# 7. SCREEN REPRESENTATION

Every discovered screen should have a structured representation.

Example:

{
    "screen_id": "screen_001",
    "name": "Home",
    "purpose": "Main application screen",

    "elements": [
        {
            "element_id": "element_001",
            "type": "button",
            "label": "Search",
            "purpose": "Opens search",
            "action": "tap"
        }
    ],

    "actions": [
        {
            "element_id": "element_001",
            "action": "tap",
            "destination": "screen_002"
        }
    ]
}

This is an example only. The final schema can evolve during development.

---

# 8. NAVIGATION GRAPH

The system should represent the application as a graph.

Example:

Login
  ↓
Home
  ├── Search
  │     ↓
  │   Product
  │
  ├── Profile
  │
  └── Cart

Screens are nodes.

Actions/navigation paths are edges.

This graph will be displayed in the dashboard.

---

# 9. SCREEN DEDUPLICATION

The system should recognize when it encounters a screen that it has already discovered.

A screen should not be duplicated simply because it was reached through a different navigation path.

Screen similarity may use:

- UI element structure
- Element text
- Element types
- Element positions
- Screenshot similarity
- Semantic screen descriptions

The implementation can evolve as testing progresses.

---

# 10. DESIGN UNDERSTANDING

The system should attempt to capture the application's visual language.

Relevant information may include:

- Primary colors
- Background colors
- Text colors
- Typography
- Button styles
- Cards
- Borders
- Corner radius
- Spacing
- Navigation components
- Light/dark theme
- General visual style

The goal is not pixel-perfect design extraction in the first version.

The goal is to capture enough design information to describe and partially reconstruct the application.

---

# 11. APP KNOWLEDGE PACK

The final Knowledge Pack should be machine-readable.

It should contain:

## Application

- Name
- Package identifier
- Exploration timestamp

## Screens

- Screen ID
- Name
- Purpose
- Screenshot reference
- UI elements
- Actions

## Elements

- Element ID
- Type
- Text/label
- Position
- Purpose
- Possible action

## Navigation

- Source screen
- Action
- Destination screen

## Design

- Colors
- Typography
- Components
- Theme
- Layout information

The format will initially be JSON.

---

# 12. DASHBOARD

The project should include a web-based dashboard.

The dashboard should allow the user to see:

- Application name
- Exploration status
- Number of screens discovered
- Number of elements discovered
- Number of transitions discovered
- Application navigation graph
- Screen screenshots
- Screen descriptions
- UI elements
- Actions
- Design information

Example layout:

----------------------------------------------------
| APP UNDERSTANDING                                |
----------------------------------------------------
|                                                  |
| APP MAP          SCREENSHOT       SCREEN INFO    |
|                                                  |
| Login            [ screenshot ]    Home          |
|   ↓                                Main screen   |
| Home                               Elements: 12  |
| ↙  ↓  ↘                            Actions: 8    |
| Search Profile Cart                              |
|                                                  |
----------------------------------------------------

---

# 13. SCREEN RECONSTRUCTION

The system should eventually support a rebuild demonstration.

The process should be:

Original Android App
        ↓
Autonomous Exploration
        ↓
App Knowledge Pack
        ↓
Original App removed
        ↓
Knowledge Pack used alone
        ↓
Reconstructed UI

The prototype should demonstrate reconstruction of approximately 2–3 screens.

The first version does not need to reproduce the entire application.

The purpose of this feature is to demonstrate that the Knowledge Pack contains meaningful information about the original application.

---

# 14. SAFETY

The agent must have an action validation layer.

The AI should not automatically perform dangerous or irreversible actions.

Examples include:

- Purchases
- Money transfers
- Account deletion
- Sending messages
- Changing passwords
- Destructive settings

The hackathon prototype should use controlled test applications and test credentials/data.

Authentication should only be handled using legitimate test credentials or test environments provided for the prototype.

The system must not attempt to bypass real authentication, security controls, CAPTCHAs, or access restrictions.

---

# 15. INITIAL MVP

We are NOT attempting to solve every Android application immediately.

The first working prototype should demonstrate:

1. Connect to an Android emulator.
2. Launch a test application.
3. Capture a screenshot.
4. Read UI information.
5. Identify interactive elements.
6. Decide on a next action.
7. Execute the action.
8. Detect the resulting screen.
9. Remember the screen.
10. Build a navigation graph.
11. Generate a Knowledge Pack.
12. Display the Knowledge Pack in a dashboard.
13. Reconstruct 2–3 screens.

A small controlled Android application should be used during initial development.

---

# 16. INITIAL TEST APPLICATION

Before testing on unfamiliar production applications, we will use a small controlled Android application.

The initial test application should contain approximately:

Login
  ↓
Home
 ├── Search
 │     ↓
 │   Product
 │
 └── Profile

This allows us to verify that the agent works correctly before testing on unknown applications.

---

# 17. TEAM STRUCTURE

We have three developers.

## Person 1 — Agent / AI

Primary responsibility:

- Exploration agent
- Screen understanding
- Action selection
- Exploration memory
- Agent prompts
- Agent decision logic

Primary folder:

agent/

---

## Person 2 — Android Automation

Primary responsibility:

- Android emulator
- ADB
- UI interaction
- Screenshot capture
- UI information extraction
- Tap
- Scroll
- Type
- Back
- Application state detection

Primary folder:

android-controller/

---

## Person 3 — Knowledge / Dashboard

Primary responsibility:

- Knowledge Pack
- JSON schema
- Screen representation
- Navigation graph
- Dashboard
- Screen viewer
- Reconstruction prototype

Primary folders:

knowledge/
dashboard/

---

# 18. SHARED DEVELOPMENT RULES

All developers work from the same GitHub repository.

The main branch must remain functional.

Each developer should work primarily on their own branch.

Suggested branches:

agent
android
dashboard

Before making major changes:

1. Pull the latest main branch.
2. Work on the assigned branch.
3. Test changes.
4. Commit changes.
5. Push the branch.
6. Create a pull request.
7. Review before merging into main.

Do not modify another person's module without discussing it first.

---

# 19. MODULE COMMUNICATION

The modules must communicate through clearly defined interfaces.

Agent → Android Controller

Example:

{
    "action": "tap",
    "element_id": "search_button"
}

Android Controller → Agent

Example:

{
    "success": true,
    "screenshot": "screen_004.png",
    "ui_elements": []
}

Agent → Knowledge Builder

Example:

{
    "screen": {},
    "action": {},
    "transition": {}
}

The exact API contract will be defined separately in API_CONTRACT.md.

---

# 20. DEVELOPMENT PRINCIPLES

We are beginners, so the system should prioritize:

- Simple architecture
- Readable code
- Small modules
- Clear documentation
- Frequent testing
- Minimal unnecessary dependencies
- Working prototype over theoretical complexity

Do not introduce complex infrastructure unless it solves a demonstrated problem.

Do not build features that are not required for the MVP before the core exploration loop works.

---

# 21. DEFINITION OF SUCCESS

The prototype is considered successful when:

1. An Android application can be connected to the system.
2. The agent can observe the application.
3. The agent can choose actions autonomously.
4. The actions can be executed on the Android device.
5. Multiple screens can be discovered.
6. Previously discovered screens can be recognized.
7. Navigation relationships can be recorded.
8. A Knowledge Pack can be generated.
9. The Knowledge Pack can be displayed visually.
10. At least 2–3 screens can be reconstructed from the Knowledge Pack.

---

# 22. DEVELOPMENT ORDER

Do not build everything simultaneously.

Build in this order:

PHASE 1
Android connection and basic controls

PHASE 2
Screenshot and UI information extraction

PHASE 3
AI screen understanding

PHASE 4
AI action selection

PHASE 5
Autonomous exploration loop

PHASE 6
Exploration memory and screen deduplication

PHASE 7
Knowledge Pack generation

PHASE 8
Dashboard and navigation graph

PHASE 9
Screen reconstruction

PHASE 10
Testing, reliability and presentation polish

---

# 23. IMPORTANT RULE FOR AI CODING AGENTS

Any AI coding agent used by the team must:

1. Read this file before starting work.
2. Understand the existing architecture before changing code.
3. Work primarily within the developer's assigned module.
4. Avoid rewriting working code without a reason.
5. Explain major architectural changes.
6. Create tests where practical.
7. Run tests before claiming that a feature is complete.
8. Clearly report errors instead of hiding them.
9. Never add unnecessary dependencies without justification.
10. Keep the project runnable after changes.

The AI coding agent is a development tool.

The final product must contain its own autonomous exploration agent.

These are two different things.

---

# 24. CURRENT PRIORITY

Our immediate priority is NOT the dashboard.

Our immediate priority is proving:

OBSERVE
    ↓
UNDERSTAND
    ↓
DECIDE
    ↓
ACT
    ↓
OBSERVE AGAIN

Once this loop works reliably on a small test application, we will build the Knowledge Pack and dashboard around it.
