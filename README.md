# URI Technology — Claude Plugin Marketplace

Plugin marketplace for the URI Technology team. This repo is public so all team members (including contractors and external collaborators) can install plugins without needing GitHub org access.

## Setup for Team Members

### 1. Add this marketplace to your Claude desktop app

In Claude desktop, go to **Settings > Plugins > Add Marketplace** and enter:

```
https://raw.githubusercontent.com/URITechnology/teamwork-plugin-claude-marketplace/main/marketplace.json
```

### 2. Install the Teamwork Sprint Manager plugin

Once the marketplace is added, you'll see "Teamwork Sprint Manager" in your available plugins. Click Install.

### 3. Using the plugin

When you start a session that involves sprint management, Claude will activate the skill automatically. It will ask for your Teamwork credentials (email and password) at the start of each session. Your credentials are only held in memory for that session — nothing is saved to disk.

**Example prompts:**

- "What's the status of Sprint-25?"
- "Compare our estimates vs. actuals for the last sprint"
- "Help us plan Sprint-26 based on our velocity"
- "Who has the most tasks right now?"
- "What's overdue?"

## For Admins

### Organization-level managed settings

Add this to your Claude managed settings (Admin Settings > Claude Code) to make the marketplace available to all org members:

```json
{
  "extraKnownMarketplaces": {
    "uri-technology-tools": {
      "source": {
        "source": "github",
        "repo": "URITechnology/teamwork-plugin-claude-marketplace"
      }
    }
  },
  "enabledPlugins": {
    "teamwork-sprint-manager@uri-technology-tools": true
  }
}
```

### Updating the plugin

1. Make your changes to files in `plugins/teamwork-sprint-manager/`
2. Bump the `version` in both `.claude-plugin/marketplace.json` and `plugins/teamwork-sprint-manager/.claude-plugin/plugin.json`
3. Commit and push — team members will get the update automatically

### Repo structure

```
teamwork-plugin-claude-marketplace/
├── .claude-plugin/
│   └── marketplace.json                          # Marketplace manifest
├── README.md
└── plugins/
    └── teamwork-sprint-manager/                  # Plugin root
        ├── .claude-plugin/
        │   └── plugin.json                       # Plugin manifest
        └── skills/
            └── sprint/
                ├── SKILL.md                      # Main skill instructions
                ├── references/                   # API documentation
                │   └── api-endpoints.md
                └── scripts/                      # Helper scripts
                    ├── tw_api.py
                    ├── sprint_overview.py
                    ├── time_analysis.py
                    └── velocity_report.py
```

## Security

This repo contains no credentials or secrets. The plugin prompts each user for their Teamwork email and password at the start of every session. Credentials are held in memory only and never written to disk or included in any files.
