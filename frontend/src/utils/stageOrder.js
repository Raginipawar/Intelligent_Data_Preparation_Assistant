// stageOrder.js — the pipeline order Person 3's real orchestrator applies
// suggestions in (see person3_engine/README.md's Orchestration section):
// imputation -> encoding -> scaling -> transform -> binning -> interaction ->
// drop_redundant. Note drop_redundant runs LAST, not third — it's excluded
// from Person 3's conflict-resolution rule 2 for exactly that reason ("it runs
// last in the pipeline order, so anything else still gets to run first").
export const STAGE_ORDER = [
  "imputation",
  "encoding",
  "scaling",
  "transform",
  "binning",
  "interaction",
  "drop_redundant",
];
