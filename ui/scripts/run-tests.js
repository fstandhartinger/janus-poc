#!/usr/bin/env node
import { spawnSync } from 'node:child_process';

const args = process.argv.slice(2);
const wantsUnit = args.some(
  (arg) => arg.startsWith('--coverage') || arg.startsWith('--watchAll'),
);
const filteredArgs = args.filter((arg) => !arg.startsWith('--watchAll'));

const command = wantsUnit ? 'vitest' : 'playwright';
const baseArgs = wantsUnit ? ['run'] : ['test'];

const result = spawnSync(command, [...baseArgs, ...filteredArgs], {
  stdio: 'inherit',
  shell: process.platform === 'win32',
});

process.exit(result.status ?? 1);
