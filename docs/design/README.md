# Design reference

The user-provided dashboard reference is the canonical visual direction for the desktop application. The original vector mockup remains available as a structural reference only.

The application opens to a dark, native desktop dashboard with a violet accent, a compact top menu, branded navigation rail, text-and-icon status cards, a Browser Source URL card, session controls, embedded overlay preview, and a right-side appearance panel. The implementation should retain this hierarchy at common Windows display scales, rather than presenting a generic web page inside a window.

The visual contract from the reference is:

- Near-black charcoal surfaces with subtle borders and a violet primary action color.
- A clearly labelled Live state, plus individual Twitch, OBS, Overlay Server, and Session status cards.
- Dashboard-first workflow, with Tasks, Connections, Appearance, and Help in the left rail.
- A live overlay preview beside its controls.
- Appearance fields visible without navigating away from the dashboard, with a fuller Appearance page for advanced settings.
- Large, clear start/stop/restart controls and readable setup guidance.
