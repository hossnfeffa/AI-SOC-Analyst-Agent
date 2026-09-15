# AI SOC Analyst Agent

🚧 **Status: In development.** Core log-querying logic is underway locally and hasn't been pushed to this repo yet — this README lays out the project's direction while the build catches up.

## Overview

An AI-assisted tool that queries an Azure Log Analytics Workspace using Python and KQL, then uses AI to summarize and interpret the results in plain language — giving a SOC analyst a faster starting point for triage and investigation instead of reading raw query output line by line.

## Planned Capabilities

- [ ] Connect to an Azure Log Analytics Workspace via the Azure Python SDK
- [ ] Run KQL queries against Sentinel / Defender for Endpoint tables (e.g. sign-in logs, alert tables, device events)
- [ ] Parse and structure raw query results
- [ ] Use AI (Azure OpenAI) to summarize findings and flag anomalies in analyst-readable language
- [ ] Package the workflow into a reusable script/agent a SOC analyst can run against a live workspace

## Planned Tech Stack

**Data Source:** Microsoft Sentinel • Azure Log Analytics Workspace • KQL

**Language:** Python (Azure SDK for Python)

**AI Layer:** Azure OpenAI

## Why This Project

Most of the manual effort in early-stage SOC triage is running the same handful of KQL queries and reading through raw results by hand. This project explores how much of that first pass — running the query, pulling the relevant fields, and summarizing what's notable — can be handed to an AI layer, so an analyst starts their investigation with a summary instead of a blank query window.

## Roadmap

This repo is being built out from a working local prototype. Next milestones:

1. Push the initial Log Analytics connection + query script
2. Add the AI summarization layer
3. Document setup and usage once the core flow is stable

---

Part of a broader portfolio of AI and security automation projects — see [github.com/hossnfeffa](https://github.com/hossnfeffa).
