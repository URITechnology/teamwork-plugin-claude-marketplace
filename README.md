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

### Updating the plugin

1. Make your changes to the skill source files
2. Repackage using the skill packager to create a new `.skill` file
3. Replace the `.skill` file in `plugins/`
4. Bump the `version` in `marketplace.json`
5. Commit and push — team members will get the update automatically

### Repo structure

```
teamwork-plugin-claude-marketplace/
├── marketplace.json                        # Marketplace manifest
├── README.md                               # This file
└── plugins/
    └── teamwork-sprint-manager.skill       # The packaged plugin
```

## Security

This repo contains no credentials or secrets. The plugin prompts each user for their Teamwork email and password at the start of every session. Credentials are held in memory only and never written to disk or included in any files.
