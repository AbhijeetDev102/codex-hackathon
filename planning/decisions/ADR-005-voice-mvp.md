# ADR-005: Push-to-talk voice MVP

**Status:** accepted

## Decision

The first voice experience records a maximum 30-second 16 kHz mono WAV question, transcribes it with Saaras v4, obtains the normal cited chat answer, and synthesizes it with Bulbul v4 Flash. It is not a continuous live voice agent.

## Why

Push-to-talk has a much smaller latency, browser, interruption, and testing surface while preserving the intended voice interaction.
