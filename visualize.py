"""
Swimlane visualization of a negotiation log: one lane per agent, time on
the x-axis, each message plotted as an arrow. This is the demo visual --
a negotiation doesn't have a natural "map" like a robot grid, so a
timeline of who-said-what-when is the clearest way to show it live.
"""

import matplotlib.pyplot as plt

AGENT_ORDER = ["Clinic", "ER", "Surgery", "ICU"]
AGENT_Y = {name: i for i, name in enumerate(AGENT_ORDER)}

COLOR_BY_PERFORMATIVE = {
    "cfp": "#4C72B0",
    "propose": "#55A868",
    "accept": "#2E7D32",
    "refuse": "#C44E52",
    "reject": "#8B0000",
}


def plot_swimlane(log, title: str, out_path: str):
    fig, ax = plt.subplots(figsize=(13, 5))

    for name, y in AGENT_Y.items():
        ax.axhline(y, color="#DDDDDD", linewidth=1, zorder=0)
        ax.text(-1.5, y, name, va="center", ha="right", fontsize=11, fontweight="bold")

    for m in log.messages:
        y_from = AGENT_Y[m.sender]
        y_to = AGENT_Y[m.receiver]
        color = COLOR_BY_PERFORMATIVE.get(m.performative, "#888888")
        ax.annotate(
            "", xy=(m.round_id, y_to), xytext=(m.round_id, y_from),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.6, alpha=0.85),
        )
        mid_y = (y_from + y_to) / 2
        show_label = m.performative in ("cfp", "accept", "refuse", "reject") or "pushed back" in m.detail.lower()
        if show_label:
            label = m.performative.upper()
            if "pushed back" in m.detail.lower():
                label = "DISPLACED"
            ax.text(m.round_id, mid_y + 0.08, label, fontsize=7, rotation=90,
                    va="bottom", ha="center", color=color)

    ax.set_ylim(-0.5, len(AGENT_ORDER) - 0.3)
    ax.set_xlim(0, max((m.round_id for m in log.messages), default=1) + 1)
    ax.set_yticks([])
    ax.set_xlabel("negotiation step (t)")
    ax.set_title(title, fontsize=13, fontweight="bold")

    handles = [plt.Line2D([0], [0], color=c, lw=2, label=p)
               for p, c in COLOR_BY_PERFORMATIVE.items()]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=len(handles), frameon=False, fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path