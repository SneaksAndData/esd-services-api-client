# ESD services Api client

This repository contains connectors to internal services:
- Beast
- Boxer
- Crystal

## Nexus OSS Release - IMPORTANT NOTICE

Nexus is a lightweight framework for running and executing ML/AI workloads on any Kubernetes cluster. For some time, Nexus was developed as a side-project in ECCO Data & AI and only worked with the proprietary execution framework. With the release of [Nexus Scheduler](https://github.com/sneaksanddata/nexus)
for Golang, Nexus Python framework transitions to true open-source. Code in `nexus` subpackage here will be in maintenance mode until the end of 2025, and no new features will be added. Once Nexus v1 is released, please consider upgrading to a new [Nexus SDK Python](https://github.com/SneaksAndData/nexus-sdk-py).

All feature requests raised for Nexus in this repository will be automatically transferred to `nexus-sdk-py`. On January 31st, 2026, `nexus` and `crystal` packages will be removed from this library.