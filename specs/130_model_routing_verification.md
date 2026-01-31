# Spec 130: Model Routing Verification Upgrade

## Status: COMPLETE
**Priority:** High
**Complexity:** Medium
**Prerequisites:** Spec 49, Spec 59, Spec 92

---

## Overview

Expand the routing verification step to output a single, structured decision that selects both execution path (fast path vs agent mode) and the best model for the task. Decisions must be fast, deterministic, and compatible with OpenAI-compatible requests. The model router must remain fully functional when no pre-decision is provided, and image inputs must always route to a multimodal-capable model. Changes must not break the agent-as-a-service Ops Console, Sandy integration, or the Janus chat UI.

### User Stories
- As a chat user, I get fast responses for simple requests without losing quality for harder prompts.
- As an operator, I can rely on consistent routing decisions across fast path and agent runs without breaking existing clients.

---

## Functional Requirements

### FR-1: Expanded Verification Decision Taxonomy
The verification step outputs a single structured decision with an enumerated value that directly maps to both path and model, using a fast decision model to minimize latency.

**Acceptance Criteria:**
- [ ] The verification output is a single structured tool/function call containing exactly one enumerated decision value.
- [ ] The enumerated decision values include and map to the following path/model pairings:
  - FAST + Qwen/Qwen3-30B-A3B-Instruct-2507 (plain, non-reasoning)
  - FAST + nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 (light reasoning / longer answer)
  - FAST + moonshotai/Kimi-K2.5-TEE (harder reasoning, no tools)
  - AGENT + nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 (simple agent task)
  - AGENT + moonshotai/Kimi-K2.5-TEE (all other agent tasks)
- [ ] The verification step uses nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 as the decision model.

### FR-2: Decision Propagation and Enforcement
The selected decision must be carried end-to-end so both fast-path execution and agent mode use the intended model without being overridden by downstream defaults.

**Acceptance Criteria:**
- [ ] A stable, optional decision field is available on incoming requests (via request metadata) and is honored by both fast path and agent mode.
- [ ] When a decision is provided, the router and agent runtime use the specified model and path without re-classifying or overriding it.
- [ ] The agent mode uses Claude Code with the specified model, matching the decision output.

### FR-3: Router Fallback and Multimodal Override
The model router must be able to make its own decision when no pre-decision is supplied, and must always route image inputs to a multimodal model.

**Acceptance Criteria:**
- [ ] If no decision is provided, the router performs the same decision logic itself and emits an explicit decision using the same enum values as FR-1.
- [ ] Router-side decisioning uses nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 as the decision model.
- [ ] If the OpenAI-compatible request includes an image, the selected model is always moonshotai/Kimi-K2.5-TEE regardless of other factors (path selection may still be fast vs agent based on complexity).
- [ ] The router continues to accept and serve standard OpenAI-compatible requests with no new required fields.

### FR-4: Backward Compatibility and System Safety
The upgrade must not break existing integrations or UI flows across Janus components and Sandy.

**Acceptance Criteria:**
- [ ] The Janus chat UI continues to function with no changes required from the user.
- [ ] The agent-as-a-service Ops Console and Sandy integration continue to route and execute requests successfully.
- [ ] Existing clients that do not send routing metadata continue to work without errors.

---

## Success Criteria

- Verification decision latency remains fast (p95 decision time under 1 second).
- Image-bearing requests always route to moonshotai/Kimi-K2.5-TEE.
- No regressions in existing end-to-end flows (baseline CLI, router, Sandy Ops, Janus chat UI).
- Routing decisions are consistent whether provided by the verifier or computed by the router.

---

## Dependencies
- Availability of the specified models (Qwen3 30B A3B, Nemotron 3 Nano 30B A3B, Kimi K2.5 TEE).
- Ability to detect image content in OpenAI-compatible requests.
- A stable request metadata channel to carry optional routing decisions across components.

## Assumptions
- Clients can ignore additional optional routing metadata without breaking compatibility.
- Agent execution environments can accept and run the specified models.
- The same decision taxonomy is shared across verifier and router components.

---

## Completion Signal

### Implementation Checklist
- [ ] Add a structured verification decision with enumerated outcomes and model mapping.
- [ ] Ensure routing decisions propagate to fast path and agent mode without overrides.
- [ ] Implement router fallback decisioning and multimodal override behavior.
- [ ] Validate backward compatibility across Sandy, Ops Console, and Janus chat UI.
- [ ] Update relevant documentation and examples to describe the optional routing decision.

### Testing Requirements

The agent MUST complete ALL before outputting the magic phrase:

#### Code Quality
- [ ] All existing unit tests pass
- [ ] All existing integration tests pass
- [ ] New tests added for new functionality
- [ ] No lint errors

#### Functional Verification
- [ ] All acceptance criteria verified
- [ ] Edge cases handled
- [ ] Error handling in place

#### Visual Verification (if UI)
- [ ] Desktop view looks correct
- [ ] Mobile view looks correct
- [ ] Design matches style guide

#### Console/Network Check (if web)
- [ ] No JavaScript console errors
- [ ] No failed network requests
- [ ] No 4xx or 5xx errors

### Iteration Instructions

If ANY check fails:
1. Identify the specific issue
2. Fix the code
3. Run tests again
4. Verify all criteria
5. Commit and push
6. Check again

**Only when ALL checks pass, output:** `<promise>DONE</promise>`

NR_OF_TRIES: 1
