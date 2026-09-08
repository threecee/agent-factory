#!/usr/bin/env bash
# Exercises strict validation and archival against a temporary two-capability project.
set -u

if ! command -v openspec >/dev/null 2>&1; then
  echo 'SKIP capability-spec-flow: openspec 1.12.0 is not on PATH'
  exit 0
fi

export CI=1
export OPENSPEC_TELEMETRY=0
export DO_NOT_TRACK=1
export OPENSPEC_NO_UPDATE_CHECK=1
unset FORCE_COLOR

version="$(openspec --version 2>&1)"
if [ "$version" != '1.12.0' ]; then
  printf 'not ok - capability-spec-flow requires openspec 1.12.0, found: %s\n' "$version" >&2
  exit 1
fi

T="$(mktemp -d "${TMPDIR:-/tmp}/capability-spec-flow.XXXXXX")"
trap 'rm -rf "$T"' EXIT
cd "$T" || exit 1

mkdir -p \
  openspec/specs/checkout \
  openspec/changes/add-profile-notices/specs/profile-notices \
  openspec/changes/replace-checkout-draft/specs/checkout \
  openspec/changes/archive

cat > openspec/specs/checkout/spec.md <<'EOF'
# Checkout

## Purpose

Preserve a customer's checkout work across the ordinary interruptions of a purchase.

## Requirements

### Requirement: Retain a checkout draft

The system SHALL retain an unfinished checkout for the returning customer.

#### Scenario: Customer returns

- **WHEN** a customer returns to an unfinished checkout
- **THEN** the system restores the saved checkout
- **AND** the customer can continue from the saved step

#### Scenario: Customer completes checkout

- **WHEN** a customer completes the saved checkout
- **THEN** the system removes the checkout draft
EOF

cat > openspec/changes/add-profile-notices/specs/profile-notices/spec.md <<'EOF'
# Profile notices delta

## ADDED Requirements

### Requirement: Show a profile notice

The system SHALL show a notice when a customer's profile needs attention.

#### Scenario: Profile needs attention

- **WHEN** the customer's profile is incomplete
- **THEN** the system shows a profile notice
- **AND** the notice identifies the missing information
EOF

cat > openspec/changes/replace-checkout-draft/specs/checkout/spec.md <<'EOF'
# Checkout delta

## MODIFIED Requirements

### Requirement: Retain a checkout draft

The system SHALL retain an unfinished checkout for the returning customer.

#### Scenario: Customer returns

- **WHEN** a customer returns to an unfinished checkout
- **THEN** the system restores the saved checkout
- **AND** the customer can continue from the saved step
EOF

if openspec validate replace-checkout-draft --strict >"$T/modified.out" 2>&1; then
  echo 'not ok - strict validation accepted a MODIFIED requirement missing a surviving scenario' >&2
  exit 1
fi
if ! grep -Fq 'omits scenario(s) the current spec still has:' "$T/modified.out" ||
   ! grep -Fq 'MODIFIED requirement replaces the whole block' "$T/modified.out"; then
  cat "$T/modified.out" >&2
  echo 'not ok - MODIFIED validation failed for an unexpected reason' >&2
  exit 1
fi

rm -rf openspec/changes/replace-checkout-draft

if ! openspec validate add-profile-notices --strict >"$T/added.out" 2>&1; then
  cat "$T/added.out" >&2
  echo 'not ok - strict validation refused the bare ADDED delta' >&2
  exit 1
fi

if ! openspec archive add-profile-notices --yes >"$T/archive.out" 2>&1; then
  cat "$T/archive.out" >&2
  echo 'not ok - archive refused the validated bare change directory' >&2
  exit 1
fi

if [ ! -f openspec/specs/profile-notices/spec.md ]; then
  echo 'not ok - archive did not merge the added capability spec' >&2
  exit 1
fi

set -- openspec/changes/archive/*
if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
  echo 'not ok - archive did not create exactly one dated change directory' >&2
  exit 1
fi
case "$(basename "$1")" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-add-profile-notices) ;;
  *)
    printf 'not ok - archive directory has the wrong name: %s\n' "$(basename "$1")" >&2
    exit 1
    ;;
esac

capabilities="$(find openspec/specs -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
if [ "$capabilities" -ne 2 ]; then
  printf 'not ok - archive left %s capability directories, expected 2\n' "$capabilities" >&2
  exit 1
fi

live="$(find openspec/changes -mindepth 1 -maxdepth 1 ! -name archive -print)"
if [ -n "$live" ]; then
  printf 'not ok - archive left live change directories:\n%s\n' "$live" >&2
  exit 1
fi

echo 'capability-spec-flow: strict ADDED/archive green; incomplete MODIFIED refused; no live changes remain'
