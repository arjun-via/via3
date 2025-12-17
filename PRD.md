# Plan for Via2 Orchestration Improvements and IDE Integration







## Deep Research Report







### Latest Research and Landscape Overview





Recent advances in autonomous coding agents on the SWE-bench benchmark reveal clear patterns in what works. Simplicity in orchestration and strong models trump overly complex agent designs. For example, the open-source mini-SWE-agent achieves 65–74% on SWE-bench Verified using only ~100 lines of Python and a single powerful model (Claude Sonnet 4)  . Its strategy is “bash-only” commands via Python’s subprocess.run with no persistent session or fancy tool plugins – every action is an independent shell command. This radical simplicity eliminates multi-agent coordination overhead and deployment complexity, yet matches the performance of far more elaborate systems  . What Via2 should copy: minimize custom orchestration logic and let the LLM’s own capabilities handle as much as possible. A linear Think→Act→Observe loop with one command at a time (especially using real shell execution) prevents hallucinated tool behaviors and is easy to sandbox. Additionally, a lightweight design is easier to maintain and scale (e.g. running 100+ agents in parallel) than a monolithic “agent cloud.” What to avoid: complex multi-agent handoff pipelines that can introduce state sync bugs and error propagation – our internal results already showed a 4-model pipeline had high overhead  without commensurate gain. What to verify: that simplifying the architecture does not omit any essential capabilities; we must ensure our prompts and single-agent loop reliably handle the tasks that multi-agent systems attempted (e.g. code review or multi-step reasoning) in a simpler way.



Another key insight is the benefit of runtime diversity and search, but in a controlled way. The new Live-SWE-agent takes the minimal baseline (built on mini-SWE-agent) and adds a twist: it allows the agent to modify or extend its own code during runtime  . The system “self-evolves” by generating new strategies or tools on the fly, which led to state-of-the-art results: Claude Opus 4.5 + Live-SWE-agent scored 79.2% on SWE-bench Verified  , nearly matching Anthropic’s proprietary orchestrator. This suggests that giving the agent more flexibility at runtime (to try alternative approaches when stuck) can yield real gains. However, not all of Live-SWE’s wins may be due to true self-improvement. Some improvements might come simply from better prompts or configuration, since Live-SWE-agent is “very minimal modifications” to mini-SWE-agent plus a self-editing loop . What Via2 can adopt safely: the idea of dynamic strategy switching – e.g. running multiple independent attempts or adjusting the approach on failures – without literally letting the agent rewrite its own codebase. We can implement a controlled form of self-improvement by pre-defining a few fallback strategies (or model prompts) and letting the agent choose among them when needed (for instance, a different localization method if initial guess fails). What to be cautious about: unconstrained self-modification can introduce unpredictable behavior or security issues. Any self-evolution mechanism must be sandboxed and require the agent to prove the benefit of a change (via tests) before trusting it. We should set safety boundaries – e.g. the agent can propose code for a new analysis tool, but it runs in isolation and is reviewed or tested before use in the main loop.



The OpenHands SDK provides a comprehensive blueprint for production-ready agent architecture, emphasizing modularity and integration with developer tools  . Its design includes an event-sourced state (every action logged with deterministic replay), an immutable agent configuration, and a robust tool interface (with a standardized Model Context Protocol for connecting to external tools) . Crucially, OpenHands comes with a built-in REST/WebSocket server and a web-based VS Code-like IDE UI   – exactly the kind of setup Via2 will need for IDE integration. It also supports multiple model backends and routing out-of-the-box, and provides security features (sandboxing, a security analyzer for agent actions) and QA instrumentation (unit tests & integration tests for agent behaviors) . What Via2 should copy: a modular architecture with clear separation between the agent logic, execution environment, and UI, connected by well-defined APIs. We should leverage event-sourced logging (for replay and auditability) and possibly adopt the same communication protocols (REST/WS) to interface with an IDE. The concept of a workspace abstraction that lets the agent run locally or remotely with the same code is valuable  – Via2’s IDE agent could execute on a developer’s machine or a cloud container without code changes. OpenHands also demonstrates multi-LLM routing and plugin-style tool interfaces, which we can reuse to allow, say, swapping out the LLM or adding a new static analysis tool easily . What to avoid: Over-engineering the integration – OpenHands V0 learned that forcing every action through a Docker sandbox hurt flexibility  . We should follow their V1 principle of making sandboxing optional: run tools in-process for simplicity unless isolation is needed . In short, adopt OpenHands’ robust infrastructure (APIs, event model, multi-backend support) while keeping the default execution loop as simple as possible.



From the original SWE-agent (ACI) project, the lesson is that giving the LLM agent proper tools and interfaces to interact with code vastly improves performance . SWE-agent introduced an Agent-Computer Interface (ACI) with abilities to read/write files, navigate the repository, and execute tests, all exposed in a structured way to the LLM  . This yielded state-of-art results at the time (12.5% on SWE-bench with GPT-4) when compared to plain LLM with no tools . What Via2 should borrow: ensure the agent has a rich interface to the codebase and test framework. This means our agent should be able to list project files, open relevant ones, run targeted tests or linters, etc., through clear commands (not just via long context prompts). The ACI concept shows that how we present the environment to the LLM (file paths, test names, error outputs) can guide it to better solutions. We should refine our prompts to include structured context (e.g. a list of failing test names and their stack traces, or a summary of the file where an error occurred) rather than a raw dump of text. What to avoid: assuming the LLM will “figure it out” from an unstructured blob of context. The interface should be explicit – e.g., instead of pasting an entire file, we might say: “Function X in file Y is failing with Z, here is the function code…”. Also, ACI research warns that too many tools can confuse the agent; it’s better to provide a few well-scoped actions (edit code, run tests, search for string in repo) and have the agent plan using those.



Notably, Agentless approaches have challenged the need for any agent loop at all. Agentless (Xia et al. 2024) uses a simple three-phase pipeline (localize → repair → validate) with no iterative planning by the LLM  . The LLM is prompted once to find the bug location and suggest a fix, which is applied and then tested – no self-reflection or multi-step reasoning beyond that. Surprisingly, this simplistic approach achieved 32.0% on SWE-bench Lite (the highest of all open agents at the time)  and at very low cost ($0.70 per issue) . Why did it work? Because it turns out a competent model, given a good problem statement and maybe a few hints, can often jump directly to a valid fix. The agent loop (thinking step-by-step) sometimes adds more chances to go off-track. What Via2 should copy: incorporate a “single-shot” mode or heuristic – for easier issues or as a first attempt, have the model directly propose a patch without an elaborate loop. This could be an optional path: if the issue is straightforward, one prompt with the issue + relevant file content might solve it faster and just as well. We might even integrate Agentless’s localization-first idea: run a quick static analysis or search to pick the file/function to focus on, then ask the LLM for a fix in that context. What to avoid: letting the model run amok with no structure on complex tasks. Agentless is great for simple bugs, but for harder problems, a naive one-shot might fail silently or produce an incomplete fix. We should use data (e.g., issue difficulty or prior failures) to decide when to employ a minimal approach vs. a richer loop. Also, even in one-shot mode, we need to validate the patch with tests and possibly do a second try if it fails. In summary, we want the option to bypass a lengthy chain when it’s not needed – essentially a dynamic choice between “agent mode” and “direct mode.”



A recurring theme is the importance of search and localization as a first-class component of the solution. Several top methods invest heavily in pinpointing where to make a change before attempting to write code. For instance, AutoCodeRover combines LLMs with static code analysis and iterative search over the AST (abstract syntax tree) to find the likely fault area  . It even uses spectrum-based fault localization (SBFL) when tests are available, to narrow down suspicious functions or lines . The result was a 19% solve rate on SWE-bench Lite – higher than the earlier SWE-agent baseline – at only $0.43 cost  . This demonstrates that better search beats more agent steps: focusing the LLM on the right part of code yields better outcomes than brute-force trying many actions. What Via2 should copy: integrate a “SWE-search” stage where we leverage tools to gather clues: e.g., use BM25 or embedder-based search to find files related to the issue description, use stack traces or error messages (if any) to locate where in code the failure happens, and use call graphs or AST analysis to understand the context. This should happen before or at least alongside invoking the LLM for a fix, so that the model’s context window is filled with the most relevant information. We can also incorporate SBFL by running the test suite (or just the failing test) on the unpatched code under instrumentation to see which lines are executed leading up to the failure – giving the model a hint like “suspicious lines: X.py line 120”. What to avoid: solely relying on the LLM’s internal knowledge to navigate a large codebase. Even the best models benefit from explicit retrieval of relevant code (since it “improves success-per-token” by reducing irrelevant context). We should verify that any search results fed to the model truly include the bug location; if our search fails to find the right file, the model likely will too. Thus, an evaluation of our localization accuracy is needed (e.g., measure if the known fix file is in our top-N suggestions).



Finally, recent benchmark analyses stress the need for rigorous validation and honest reporting of results. A meta-study of 67 systems on SWE-bench   found that many agents (even by big tech companies) suffered from patch overfitting – producing patches that pass the limited tests but are actually incorrect. On average, resolution rates may be overstated by ~6 percentage points due to these false positives  . Another analysis by Wang et al. found the official SWE-bench Verified harness was running only a subset of tests (those touched by the PR), missing some regressions; when running all tests, ~7.8% of “successful” patches actually failed  . Implication for Via2: We must match the official evaluation exactly – i.e. function-level test execution as in SWE-bench’s harness – and also consider augmenting our validation to catch overfitting. For example, we might implement a PatchDiff style check (comparing behavior of patched vs. ground-truth solution on extra tests)   to flag patches that only incidentally pass. We should also log and analyze any cases where our internal validation says “pass” but the official says “fail” (or vice versa) – these are gold nuggets for understanding gaps. What to verify: that every improvement we claim is on the basis of faithful validation. No “hand-wavy” internal metrics – if we try a new idea (e.g. multi-patch filtering), we must evaluate it with the exact same criteria as the SWE-bench leaderboard does and measure real solve rate uplift. Additionally, we should continue to track why tasks fail or succeed (e.g., log if a failure was due to a test we didn’t run, or a flaky environment issue) to constantly ensure we’re not chasing phantom gains.





### Establishing the True Baseline (B1)





To accurately measure progress, we first need to re-run our best current system with the exact official SWE-bench protocol. Our current top configuration (Opus-Conductor V4 from the previous report) achieved 71.8% “internal” success  using a slightly imperfect validation method, which likely overestimates the true solve rate. In fact, we discovered a “validation gap” where our in-house harness was too coarse: we ran entire test modules, whereas the benchmark runs individual test functions  . This meant some patches that broke other tests in the module slipped through our validation as false positives . When this was first identified, it explained a massive 50-point discrepancy (80% vs ~30%) in one scenario  – though that was before many fixes; for the final system it won’t be that large. We have since developed validation_harness.py to mirror the official behavior . Action: Re-evaluate Opus-Conductor V4 (and any other contenders) using function-level test execution exactly as SWE-bench does. We will parse each issue’s failing test names and run them individually (ensuring no incidental passes due to other tests). We’ll also capture full output and use exit codes as the primary pass/fail signal (to avoid mis-parsing verbose output)  .



After this rerun, we will quantify the validation gap for our baseline. Specifically, we will log for each previously “passed” issue whether it fails under the stricter harness, and categorize the failure cause. Likely causes include: (a) Sibling test breakages – the patch fixed the targeted test but caused a different test to fail (this is exactly what function-level granularity will catch) . (b) Timeout or resource limits – perhaps our agent took too long or used too much memory on some issues; under official constraints these count as failures. (c) Flaky outcomes – e.g., if a test passes intermittently or a nondeterministic environment issue occurred. (d) Patch application errors – though we solved this earlier (ensuring correct git checkout) , we should verify if any submitted patch failed to apply or was incomplete. Each failure will be tagged with one of these causes (we’ll extend our logging to note test results, any exceptions, etc.). This analysis will produce a true baseline success rate (expected to be somewhat lower than 71.8%) and a breakdown of what’s leaving us short of 80%. For example, we might find hypothetically that our true pass rate is, say, ~65%, with 20 failures due to sibling tests, 10 due to timeouts, etc. This guides where to focus improvements.



Importantly, this faithful re-evaluation will be our new baseline for all experiments – all proposed changes must be measured against it. We will treat any result not validated with the official-like harness as “diagnostic only” (no matter how promising). This principle is non-negotiable: as our summary above noted, many projects have stumbled by optimizing to an improper metric. Via2 will not fall into that trap; every percentage point of improvement we report will be real per SWE-bench’s criteria.





### Intervention Proposals and Rankings (B2)





To systematically improve from ~70% towards 80%+, we propose interventions in five categories. For each, we assess impact (how much it could raise success), confidence (how certain we are it will help), and effort (cost to implement). We then prioritize accordingly. The interventions are:



1. Harness Fidelity & Reliability: The foundation is to eliminate false passes and flakes. We’ve mostly addressed fidelity (function-level tests as above), but we will further improve reliability:



- Output tail capture & structured parsing: Ensure we don’t miss failure signals. We will capture at least the last ~5000 characters of test output (rather than truncating head) to get the full picture . Our harness will parse results primarily by process exit code, falling back to text patterns (“OK”, “FAIL”) only if needed . Impact: High (removes false positives/negatives), Confidence: High (straightforward fix), Effort: Low.
- Flake retry policy: Some tests or external steps might fail sporadically (e.g., network timeout in a test). We implement a policy to auto-rerun a test failure once if it’s an infrastructure error or a known flaky test. For example, if a test fails with a segmentation fault or out-of-memory, we might retry in a fresh container with more memory or mark the issue differently. We’ll also set decision criteria: e.g., if a rerun passes, count as flaky success but log it; if it consistently fails, it’s a true failure. Impact: Low-medium (won’t create successes, but avoids penalizing flukes), Confidence: Medium (flakes are not too common but present), Effort: Low.
- Time/memory controls per repo: We will fine-tune resource limits. Some tasks might time out due to default settings. E.g., we know Django tests needed --parallel=1 to avoid OOM . We’ll set a reasonable timeout per test (perhaps 2 minutes each, 10 minutes overall) and memory limit per process, and crucially, adjust these per repository if needed (Django vs smaller projects can differ). Impact: Medium (prevents avoidable timeouts), Confidence: High, Effort: Medium (needs some profiling of each repo).





Priority consideration: These harness fixes are highest priority to implement immediately – they might not raise the success rate directly (they mostly prevent miscounting passes as successes), but they ensure all other gains are real. They also prevent us from chasing issues that aren’t code problems (like an infrastructure timeouts) by making those visible.



2. Patch Generation Strategy: This is likely the biggest lever for improving actual success rate. We will experiment with test-time generation of multiple candidate patches and better use of model power:



- Single-loop (Opus-solo minimal): As a baseline, we’ll try a simplified version of our agent using one strong model (Claude Opus 4.5) in an iterative loop, similar to our V5 minimal system. Our earlier results hinted that a minimal loop solved some hard tasks better . We will compare performance at equal budget. Impact: Baseline – may not improve much beyond current, but establishes if complexity was hurting. Confidence: High (we have data V5 was competitive), Effort: Low (just run our existing V5 code on all tasks).
- Multi-patch generation + execution filter: This approach generates, say, 3–5 patch ideas from the model for each issue, then runs tests on all and picks a winner if any passes. The hypothesis is that increasing “coverage” of solution space at runtime can boost success significantly – e.g. if the model has a 50% chance to fix a bug per try, having 5 independent tries could raise success to ~90% for that issue (assuming independence). This aligns with recent “test-time scaling” findings: allowing more compute (trials) yields higher solve rates  . We’ll implement this by prompting the model for multiple solutions (either via an instruction like “propose 3 possible fixes” or by simply sampling multiple times with temperature). Then run each patch through validation harness in parallel. If one passes all tests, we consider it solved. We will need a tie-break or selection rule if multiple pass (perhaps choose the smallest patch or the first chronologically). Impact: High – this directly targets raising the success count (expected +3-5 percentage points if many near-miss failures currently), Confidence: High – many leaderboards entrants report multi-sample helps (e.g., Anthropic’s “Claude 3.7” submissions use multi-output + selection to reach >70% ), Effort: Medium – requires managing multiple patches and running multiple containers, but we can parallelize this.
- Small ensemble of strong models (optional): We consider using 2 different top models (e.g., Claude and GPT-4 or Claude and a future Gemini model) to generate patches, increasing diversity. Prior research suggests ensembles of strong models can outperform a single model   (whereas ensembles of weak models did not help). This is more expensive, so we will only justify it if single-model multi-patch plateaus. Impact: Potentially medium (if models have complementary strengths, maybe +1-2% solve rate), Confidence: Low-medium (not many have tried multi-frontier-model ensembles; risk of just duplicating cost), Effort: Medium-high (need integration of another API, handling two models’ outputs).





Priority: The multi-patch execution filtering is a top priority “big bet” – we expect it to yield a noticeable jump in solves for relatively low added cost (since we only pay for extra generations and test runs, which on average is still cheaper than a human). We will implement this right after solidifying the harness. The ensemble idea is lower priority and will be tested only if we need an extra push towards 80% and if budget allows.



3. Localization Improvements: To increase the chance that a patch attempt is fixing the right area, we will upgrade our bug localization subsystem:



- BM25 and regex search: We’ll use information retrieval (e.g., Lucene/BM25) over the repository to find candidate files given the issue title/description. Many issues have a stack trace or error message – we will regex-search the code for those identifiers (function names, error strings). This provides a list of suspect files. Impact: Medium – ensures we feed the model the right file paths most of the time, which is prerequisite for a correct fix, Confidence: High (AutoCodeRover and others saw big gains from better search  ), Effort: Medium (we can integrate an existing search library).
- Test name → source mapping: Since we know the failing test (function name and class), we can map that to target code. For instance, if a test is auth_tests.test_validators.UsernameValidatorsTests.test_unicode_name , our agent should automatically deduce the code under test (perhaps function username_validator in validators.py). We’ll maintain heuristics: e.g., find a code file whose name matches a prefix (here validators.py) or search for UsernameValidatorsTests class to find references to the functionality. This can directly pinpoint the module or function to inspect. Impact: Medium, Confidence: Medium (works well if test names are descriptive), Effort: Low.
- Call graph / import graph indexing: As a more advanced step, we can preprocess each repo to build a lightweight static call graph or module import graph. Then, given a starting point (say a failing test or an error in logs), we can trace backward to likely source files. E.g., if test X fails in function f(), and we know f() is defined in file A but calls code in file B, we might need to look at B. We can use existing tools or AST parsing for this. Impact: Low-medium (helps on more complex issues where the failure is two layers deep), Confidence: Medium, Effort: High (needs static analysis; we’ll likely do this if simpler methods aren’t enough).
- “Suspicion ranking” heuristics: Combine the above signals into a ranked list of files/functions to fix. For example, a file that contains an error message substring and was recently modified in the failing commit, or that has the highest TF-IDF relevance to the issue description, gets rank 1. The agent will focus on top-1 initially, but could fall back to rank 2 if needed (e.g., if a patch doesn’t resolve the tests). Impact: Medium (ensures we fix the right file), Confidence: High (simple to implement), Effort: Low.





Priority: High. Mis-localization is essentially wasted effort – no matter how good our model is, if it’s looking in the wrong place, it won’t fix the bug. We will implement the easier parts (BM25 search and test-to-code mapping) early. We expect this to reduce the number of “attempts” the model needs and increase success on tasks where relevant code wasn’t obvious. This is relatively low-hanging fruit with high upside in success rate and possibly speed.



4. Prompt and Policy Refinements: We will refine what we ask the model to produce and how, to discourage bad fixes:



- “Don’t break other tests” constraint: We will explicitly instruct the model that a valid patch must not only fix the target issue but also not regress other tests. For instance, add a line in the system prompt: “The fix should be minimal and not introduce failures in other parts of the test suite.” While the model cannot run tests itself, this nudges it towards safer, smaller changes rather than sweeping refactoring that might break unrelated things. Impact: Medium (reduces overfitting patches), Confidence: Medium (the model might still do risky changes, but anecdotal evidence suggests prompt instructions can reduce reckless fixes), Effort: Very low.
- Diff size budgets: We set an expectation (via prompt or code) that patches should ideally be small – e.g., “prefer a fix that changes under 10 lines.” Our data shows many issues are fixed with one-liners or few lines . Large diffs often correlate with hallucinations or introducing new bugs. We won’t hard-enforce line count, but we will have the agent justify if a fix is big (“I had to refactor X because…”). We can then review those more carefully. Impact: Low-medium (helps maintain quality, though sometimes a bigger change is needed), Confidence: High (easy to implement), Effort: Low.
- Minimal refactor guidance: In cases where a larger change is necessary (e.g., a design flaw), we guide the model to do it in a controlled way. For example, instruct: “If a major refactor is needed, ensure all existing tests still pass and explain why the change is safe.” Essentially, encourage the model to only do broad changes if it has a clear reason. Impact: Low (mainly a safety net), Confidence: Medium, Effort: Low.
- Hypothesis → change → targeted-test loop: This is a subtle policy improvement: have the model articulate a hypothesis of the bug cause, propose a code change, then run only the relevant test to check. This is similar to how a human would iteratively debug. Our current loop does something like this implicitly, but we can formalize it. E.g., the model’s output format could be: “Hypothesis: X is causing a null pointer. Proposed Fix: change Y in file Z. Next: run test T to confirm.” We then execute that and feed back only test T’s result. This focuses the model on one failing test at a time. If there are multiple failing tests, it tackles them one by one. Impact: Medium (could improve reasoning by focusing the model), Confidence: Medium (some agents did similar stepwise reasoning successfully), Effort: Medium (requires prompt and loop logic tweaks).





Priority: Medium. These changes fine-tune the agent’s behavior to avoid common pitfalls (overfitting, doing too much). They likely won’t add huge numbers of new solves, but they will improve the quality of patches and ensure our multi-patch approach doesn’t just generate a bunch of overfit solutions. We will implement the simple prompt tweaks immediately (since low cost), and monitor if patch sizes or regression incidents improve.



5. Caching and Reuse: To drive down cost and runtime (and indirectly allow more attempts within budget), we introduce caching:



- Prompt caching: Anthropi’s API offers caching where identical prompts + model = cached completion. We will use this aggressively . For instance, if the agent re-runs on a issue with the same context, it won’t spend another 1,000 tokens of billing for the same analysis step. Impact: Low on success rate (doesn’t change outcomes), but high on cost reduction, Confidence: High, Effort: Low.
- Repo indexing cache: Cache the expensive embedding or indexing of repository code for search. E.g., compute embeddings for all files once, reuse across issues (until repo changes). Impact: None on success, Confidence: High (saves time on repeated ops), Effort: Low.
- Reuse localization artifacts across retries: If one patch attempt fails and we try another, we shouldn’t redo the entire search from scratch. We can reuse the list of top suspicious files, maybe just remove the one we already tried. This saves time in multi-patch mode. Impact: Slight on speed, Confidence: High, Effort: Low.
- Solution memory (templates/archetypes): Over time, the agent will solve many issues. We can build a knowledge base of common fix patterns (e.g., “ValueError: X – usually solved by adding a check in function Y”). We could allow the agent to query this by a short description. However, we must do this carefully to avoid overfitting to specific solutions. Perhaps we maintain a library of generic patch templates (like “if input is None: return …”) that are known safe. Impact: Unknown (could help on recurring bug types), Confidence: Low (risk of misapplication), Effort: Medium. We will consider this a research direction rather than immediate action – perhaps start by logging recurring themes and see if a lookup would have helped.





Priority: Low for success rate, high for efficiency. Caching mechanisms will be implemented as we go, to keep iteration fast and cheap. The solution memory idea will be revisited once we have more data – it’s not required to reach 80%, but could be a differentiator later or help with long-tail issues by leveraging past experience.



After brainstorming and analyzing these interventions, we rank their overall priority (considering impact, confidence, effort together):



1. Exact Validation & Harness fixes – P0 (must-have ASAP) – Ensures trustworthy evaluation; prerequisite for all else.
2. Multi-patch generation & filtering – P1 – Likely +3-5% points improvement , high ROI.
3. Better Localization (search & mapping) – P1 – Likely +2-3%, especially on issues we currently miss; low cost to implement.
4. Prompt/Policy tweaks (small fixes, constraints) – P2 – Improves quality, maybe +1-2% by avoiding backslides; quick win.
5. Single-model iterative baseline (Opus-solo) – P2 – May not improve much but needed to confirm simpler scaffold performance.
6. Resource/Timeout tuning – P2 – Reduces “technical” fails, potentially recovering a few percent on timeouts.
7. Ensemble of models – P3 – Potentially +1-2% but costly; do later if needed.
8. Solution memory – P3 – Experimental, uncertain benefit; revisit after above are done.





This prioritized list will inform our roadmap (see Roadmap & Uplift below for timeline and expected gains).





### Experimentation Plan (B3)





To validate each major intervention, we will run controlled experiments with proper ablations. Rather than immediately rolling out everything, we’ll test changes in isolation or in logical groupings. Our experiment matrix will have dimensions:



- Subsets of instances: We will create stratified subsets of the 500 SWE-bench Verified issues for diagnostic tests. For example: a subset per major repository (to see if improvements help one codebase more than another), and subsets by failure type. Failure-type grouping means, for instance, collect all issues our baseline fails due to timeouts – test if the timeout tuning fix solves those. Or all issues failing with patch apply errors – see if the git-checkout fix solved them. We’ll also isolate “hard tasks” (e.g., ones that needed multiple attempts historically) versus “easy tasks” (solved in one try by baseline) to see how multi-patch helps the former.

- Metrics to track: For each experiment run, we will capture not just overall pass rate but also cost per success, time per success, average patch size, number of retries, and flake rate. The official pass rate (using function-level harness) is the primary metric. But cost and time per success are critical secondary metrics – we want to raise success without blowing up cost. We expect multi-patch to increase cost per issue, so we’ll measure Cost/Success (dollars spent divided by number of successes) for each strategy . We will also monitor patch size (lines changed) and whether interventions like the diff budget prompt actually reduce it on average. Retries: how many loop iterations or patch attempts an issue takes on average – this is a proxy for efficiency. Flake rate: percentage of tasks that passed after a retry (meaning first run failed, second passed), to quantify instability.

- Comparative experiments: Key experiments include:

  

  - Baseline V4 (one-pass) vs. multi-patch (N=3,5,7 candidates): on a representative 100-issue set, measure success uplift and cost increase.
  - With vs. without improved localization: e.g., take 50 issues where baseline failed, run agent with new search module vs without, see how many more it solves and if it lowers tokens consumed (by focusing context).
  - Prompt/policy ablations: run 30 tricky issues with old prompt vs new “don’t break tests” prompt and compare outcomes (are fewer regressions observed? do patches differ in size?).
  - Caching on/off: measure speed/cost on a fixed set when using caching to quantify savings (ensuring no effect on success).
  - Opus-solo minimal vs. current orchestrated: run both on the same subset to confirm if performance is similar (if minimal is close, we lean toward simplicity).

  





Each big change will first go to a small-scale test. For example, before deploying multi-patch for all issues, we might run it on 50 issues to gauge improvement and cost, then iterate prompt format for presenting multiple solutions (maybe the model needs a specific prompt to give distinct attempts).



- Kill criteria: We will define “stop/modify” triggers for each experiment. For instance, if an intervention does not improve pass rate by at least X or if it increases cost per success above Y, we reconsider. Concretely: if multi-patch (5 candidates) only adds <1% success but doubles cost, that approach might be shelved for now (or we try 3 candidates instead). If improved localization yields no improvement on a subset (meaning our current method was already sufficient), we might drop the heavier parts like AST analysis to save effort. Each “big bet” has a threshold – e.g., ensemble of 2 models: kill if cost/success > 2× single-model cost and success < +2%. These criteria ensure we focus on changes that deliver ROI.





We will maintain a living experiment tracking document. After each intervention test, we’ll integrate what works (e.g., if multi-patch with 5 candidates yields +4% and cost+50%, that’s likely a go, maybe with some optimization) and drop what doesn’t (e.g., if ensemble adds negligible benefit, we won’t pursue it further).



Through this systematic experimentation, we expect to converge on a configuration that empirically lifts Via2’s SWE-bench Verified solve rate to the 80%+ range, while controlling cost within acceptable bounds.





### Roadmap and Expected Uplift





Based on the above priorities and experiments, we outline a phased roadmap to reach our goal, along with estimated impact on the solve rate:



- Phase 1 (Immediate, Week 0-1): Implement exact validation harness and critical bug fixes (git checkout, output capture). Expected uplift: 0% (just ensures accurate measurement), but likely will reveal true baseline ~5-10 points lower. Also deploy prompt tweaks (“don’t break other tests”) and rerun baseline to get true starting point.
- Phase 2 (Week 1-2): Integrate multi-patch generation (N=3) and improved localization (basic BM25 + test mapping). Run experiments on 100 issues to calibrate. Expected uplift: +3–5 percentage points from multi-patch (catching those issues a single try missed) and +1–2 points from catching mis-localized bugs. Cost per task may rise ~2-3×, but cost-per-success might actually improve since success rate goes up .
- Phase 3 (Week 2-3): Scale multi-patch to N=5 if cost allows, add flakiness handling and resource tweaks for stability. Expected uplift: +1–2% (diminishing returns, but covers edge cases and eliminates some timeouts). At this stage we anticipate approaching ~80% on Verified in internal tests.
- Phase 4 (Week 3-4): Run Opus-solo minimal vs current on full benchmark to validate that simplifying to one-model loop doesn’t hurt. If comparable, plan transition to simpler architecture (removing extra models from pipeline) for maintainability. This may not change success %, but simplifies system and cuts cost ~30-50%. Also consider ensemble of 2 models on the hardest 50 issues. If that yields say +2 issues solved, decide if worth the cost to integrate full-time.
- Phase 5 (Week 4+): Focus on IDE integration prep (see PRD below) and any remaining long-tail improvements. For example, if certain repositories like Sympy still lag, implement specialized strategies (perhaps their own test harness adapter, or fine-tuned prompts). By now, we expect to have ~80% solve rate confirmed with exact validation. Any further gains might come from diminishing-return ideas (ensemble, self-evolution features). We will only pursue these if needed to consistently exceed 80%. Otherwise, shift focus to productization (IDE, telemetry, user experience).





In summary, our roadmap front-loads the high-impact, high-confidence changes (accurate validation, multi-patch search, better localization), which we estimate should take us from the mid-60s (true baseline) to the high 70s in success rate. The final push to 80%+ will come from polishing reliability and possibly a few strategic extra attempts (ensuring no stone is left unturned on each issue). Each stage will be backed by experiment data before full deployment. By the end of this plan, Via2 is expected not only to surpass the 80% solve rate target, but to do so with a leaner architecture and a clear path to integration in developers’ IDEs.





## Product Requirements Document (PRD) – Via2 IDE Agent Integration







### 1. Overview





Problem Statement: Software engineers need a way to automatically diagnose and fix issues within their development environment. Via2’s autonomous coding agent has proven capable on benchmark tasks; the next step is to integrate it into an IDE so that developers can leverage its power on real issues in real time. The goal is to create a Via2 IDE Agent that can take a bug or feature request (e.g. a GitHub issue or failing test) and autonomously produce a code patch along with verification, all from within the IDE. This should streamline the debugging/fixing workflow, reduce context-switching (no need to copy data to an external tool), and increase developer trust by making the agent’s process transparent and controllable.



Target Users:



- Internal Evaluation Engineers: who run the agent on SWE-bench tasks or internal codebases to measure performance. They need fine-grained control and logging to analyze agent behavior.
- Open-Source Maintainers: who can use the agent to generate draft fixes for incoming GitHub issues in their projects. They value correctness and the ability to review patches and test results quickly.
- Product Software Engineers: (at our company or enterprise clients) who want to speed up bug-fixing in their own code. They might use the agent as a pair programmer that suggests fixes, but they remain in the loop to approve changes.





Non-goals: This integration is not intended to fully autonomously handle large new feature development or architectural changes – it’s focused on issue resolution (bugs, small feature requests) where there is a clear error or test failure to fix. It’s also not a chatty code assistant for general coding; rather than offering syntax help or code completions, it runs a whole solve procedure for a given problem. We also do not aim to create a new full-fledged IDE – instead, we integrate into existing ones (like VS Code) or provide an add-on service. Lastly, it’s not a black-box “auto-commit” bot: developer oversight and approval are built-in (the agent won’t directly push code without review).





### 2. User Stories





- “Run agent on issue” – As a developer, I want to select a bug report or failing test in my IDE and instruct the Via2 agent to attempt a fix. Example: Right-clicking an issue in a tracker pane and choosing “Let Via2 Solve” should initiate the agent. The agent will then analyze the issue, run the necessary steps, and return with a proposed code change.
- “Inspect localization” – As a developer, I want to see which files or lines the agent thinks are relevant to the issue, so I can understand its reasoning. Example: The agent produces a list like “Likely affected files: user_model.py, auth_validators.py (because the error message ‘InvalidUsername’ was found there)” which I can view. This helps me trust that the agent is looking in the right place.
- “Approve patch” – As a developer, I want to review the code diff the agent generated and have the option to apply it to my codebase. Example: After the agent finishes, a diff is shown (like a unified git diff). I can comment or make minor edits, then click “Apply Patch” to merge it into my working directory. Alternatively, if I don’t like it, I can reject it.
- “Run targeted tests” – As a user, I want to easily run either the specific test that was failing or the entire test suite to verify the fix, all from the IDE. Example: The interface might have a toggle between “Function-level test” vs “Module-level tests.” If I choose function-level and hit “Run Tests,” it executes only that test function (the same way SWE-bench would). I might toggle to run the whole module or all tests for extra assurance if needed.
- “Retry with N candidates” – As an engineer, if the agent’s first attempt doesn’t fix the issue, I want to be able to let it try alternative solutions (multiple candidates) without starting from scratch. Example: After a failed attempt, I click “Retry (3 attempts)” – the agent will generate 3 different patch ideas and test them all, presenting me with either the best one or information on each attempt. I can then choose which (if any) patch to apply.
- “Export artifact” – As an engineering lead or researcher, I want to export the full details of what the agent did (patch, logs, test outcomes, etc.) for record-keeping or analysis. Example: After the agent solves an issue, I click “Export Solution” and it saves a bundle (e.g., a ZIP file) containing the patch file (diff or actual changed files), the conversation/log of agent steps, and a README of reproduction steps. This could be attached to a pull request or stored for audit.







### 3. Core Workflows





The Via2 IDE Agent will support several core workflows, described below in sequence-diagram style:



- Solve Loop (single attempt): The user triggers “Via2 Solve” on an issue. Step 1: IDE sends a start request to the agent service with issue details (description, failing test name, etc.). Step 2: Agent service (back-end) reads the codebase (or relevant parts) and forms the initial prompt for the LLM, including problem description and any retrieved context. Step 3: Agent enters the THINK-ACT-OBSERVE loop: it may THINK (LLM proposes a plan or patch), ACT (run a command like executing tests or editing a file), then OBSERVE results. These steps repeat until a SUBMIT (final patch) or agent gives up. For example, the agent might first run the failing test to see the error (ACT: run test, OBSERVE: test fails with specific error). Then it edits the code (ACT: apply patch suggestion), then runs test again, OBSERVE result. Step 4: Once the agent believes the issue is resolved (tests passed or max steps reached), it sends the proposed patch back to the IDE. Step 5: The IDE presents the diff to the user in a review panel. Throughout this loop, the IDE received streaming updates (see below) so the user could follow along each THINK/ACT step in the logs panel.
- Multi-patch generation + execution filter: When the user requests multiple candidates (or the agent decides to, per settings), the workflow branches after initial analysis. Step 1: The agent service spawns parallel candidate generations – e.g., it prompts the LLM for 3 different patches (this can be done sequentially or via parallel calls). Step 2: It applies each candidate in a separate sandbox or sequentially, and runs the relevant tests on each. Step 3: It gathers the results: say Patch A fails 5 tests, Patch B fails 1 test, Patch C passes all tests. Step 4: Selection: if any patch fully passes, choose that as the recommended solution; if none fully passes, perhaps choose the one that got furthest (least failures) or report that all failed. Step 5: The IDE then shows either the best patch diff or possibly a list for the user: “Patch A (passed 90% tests), Patch B (passed 100% – recommended), Patch C (failed).” The user can then inspect whichever diff they want. Behind the scenes, this workflow ensures the heavy-lifting of testing each candidate happens automatically, and the user sees only the outcomes.
- Validation harness (official-faithful mode): This workflow ensures that when the agent runs tests, it mimics SWE-bench exactly. Step 1: The agent receives a test identifier (function name, class, etc.) for the failing test (from the issue or user). Step 2: When executing, instead of running pytest on an entire file or module, it constructs the exact command: e.g., pytest tests/auth_tests/test_validators.py::UsernameValidatorsTests::test_unicode_name (if using PyTest), or the equivalent for Django’s runtests.py . Step 3: It runs that specific test function. If more than one failing test is relevant, it runs them one by one. Step 4: It captures results and returns a structured outcome (pass/fail, output log, exit code). In the IDE, this appears in the Tests panel as, say, “✅ test_unicode_name passed” or “❌ test_unicode_name failed (AssertionError at line 45)”. This workflow is invoked whenever the agent needs to verify a patch. The user can also manually trigger it via the “Run targeted tests” toggle in the UI. Essentially, it’s a test runner that exactly matches the benchmark harness, giving confidence that a “pass” in the IDE equals a real pass on SWE-bench.
- Failure triage & rerun policy: When the agent fails to solve on the first try (tests still failing or agent exceptions), the system enters a triage workflow. Step 1: The agent service reports failure status and the reason (e.g., “Patch did not fix the bug, 2 tests still failing”). The IDE might surface this as a notification in the Plan/Logs panel. Step 2: The user can inspect logs or diff of the attempt. Step 3: If the failure is due to something trivial (like a flakey test or minor mistake), the user might click “Rerun” (which repeats the solve loop from scratch or from last state). Alternatively, the agent itself can have a policy to auto-rerun: e.g., “test failed due to a timeout – will retry once with higher timeout.” Step 4: On rerun, certain caches are reused (the localization results, etc.) to speed up the attempt, as mentioned. Step 5: If after N attempts (possibly N=2 or 3, configurable) the agent still fails, it will stop and mark the issue unsolved, and perhaps suggest “Consider describing the issue in more detail or seek human help.” The user is then back in control to either abandon the agent or adjust something (maybe provide a hint and try again).







### 4. Functional Requirements





IDE UI Panels: The integration will provide dedicated interface components:



- Issue Panel: Displays the current issue description, steps to reproduce (if any), and failing test names. This is where the user initiates the agent. It might integrate with an issue tracker or be a simple text input where user can paste an issue.
- Plan/Actions Panel: Shows the agent’s step-by-step thinking and actions. For example: “1. Running failing test… 2. Test output indicates X… 3. Deciding to modify Y… 4. Running tests again…”. It’s essentially a live log of the agent’s actions (thoughts can be shown in a collapsed or commented style for clarity). This helps user follow the agent’s reasoning path.
- Diff Panel: Shows the diff of the proposed code changes. We will highlight additions/deletions, similar to a Git diff viewer. If multiple files changed, either show all in one view or allow toggling file by file.
- Tests Panel: Shows test results in a readable format. E.g., green checkmarks for passed tests, red X for fails. It should show the test name and possibly the failure message/traceback for fails. The user can filter this panel to see only failing tests or all tests run.
- Logs Panel: (or combined with Plan panel) shows low-level logs – e.g., raw command outputs, any warnings, or debug info from the agent. This would be used by power users or for debugging the agent itself. It can be toggleable (collapsed by default for normal users).





These panels should be docked in the IDE (like VS Code’s panel area or as tabs in a sidebar) and update in real-time as the agent progresses.



Code Editing Interface Integration: The agent will integrate with the editor such that:



- When the agent proposes a patch, the diff can be applied to the actual workspace. This might create a virtual branch or git stash so that changes can be reviewed and undone easily.
- Apply Patch: User triggers this to merge changes. If using Git, behind the scenes this could create a commit or apply a stash.
- Rollback: If the user applied a patch but then decides to revert, there should be an “Undo Patch” button that restores the files to pre-agent state. This could be done via Git revert or by keeping a backup of files.
- Branch Management: Optionally, we could have the agent work on a separate branch (e.g., via2-fix-issue-123) to avoid mixing with unsaved user work. The PRD requirement is that the user can edit code as usual – so the agent’s changes should not be locked or hidden. Once applied, they’re just in the workspace and the user can modify them further.





This integration ensures the developer remains in control of the code. The agent never directly modifies files without either showing a diff or being explicitly allowed to apply.



Test Runner Abstraction: The system must handle multiple testing frameworks seamlessly:



- Many repos use pytest, some (like Django) use custom runners (runtests.py), others might have shell scripts or use unittest. We need a test adapter interface. Essentially, define an abstraction: run_tests(target) where target could be a function name or module. Implement adapters for:

  

  - PyTest – where target is file::Class::test format.
  - Django – target might be a fully qualified test name passed to runtests.py.
  - Others (unittest, nose, etc.) as needed.

  

- The agent service can auto-select the adapter by detecting the repo type (via config, or presence of manage.py vs pytest.ini, etc.). The configuration files (like we had validation_harness.py) will encode these rules.

- This requirement ensures that whether it’s a Django issue or a Sympy issue, the “Run targeted test” action just works. It also means in the architecture we have a plugin point to add new test frameworks easily (e.g., if a user has a custom test command, they can add an adapter).





Localization subsystem interface: We will implement the localization features as a service that the agent can call. Requirements:



- A function or API like find_relevant_files(issue_text, error_text) -> list of files using BM25 search over the repo.
- A function map_test_to_code(test_name) -> file or function for known frameworks (e.g., if test class name ends with “Tests”, try to find a corresponding module).
- This subsystem should be accessible to both agent automated runs and user manually (e.g., user clicks “Why did it choose these files?” and we show maybe a relevance score from this system).
- We might also integrate an on-demand grep: if the agent wants to search for a symbol, it can call something like grep_symbol("SymbolName") -> occurrences.
- Essentially, we expose “search” and “analyze” tools to the agent, similar to how DevTools might have search in files. These must run quickly (likely on local code, so no network latency).





Model routing interface (optional, with guardrails): The architecture should allow for multiple model usage. For example, maybe we have a cheaper model to do simple classification (like “is this issue trivial or complex?”) and a strong model to do the actual coding. Or if we incorporate the ensemble idea: run GPT-4 and Claude in parallel.



- The system should have a routing configuration: e.g., model_routing.yaml that can specify “use Model A for step1, Model B for step2” or “use Model B if repo = X”. For now, initial implementation might keep it simple (one primary model), but design such that adding another is straightforward.
- Guardrails: If using multiple models or tools, ensure outputs are sanitized. For instance, if a model returns a command to run, the agent should validate it’s not destructive (the sandbox should help here). We can incorporate an allow/deny list of actions for safety (e.g., prevent rm -rf / obviously).
- In the IDE settings, possibly let advanced users choose the model (like “Use Claude” vs “Use GPT-4”) if they have API keys, etc. The interface should make switching models easy (this is more a product feature, but underlying support is needed).







### 5. Non-functional Requirements





The Via2 IDE Agent must meet several non-functional criteria to be viable:



- Determinism & Reproducibility: As much as possible, running the agent on the same input should produce the same outcome. This means controlling sources of randomness (set random seeds for the LLM if applicable, or use deterministic mode if available). Where nondeterministic behavior occurs (like concurrency timing or external tool flakiness), log it and handle it (via retries). We also need to ensure that someone else (or future us) can replay an agent session using the event log to get the same results. Deterministic replay is supported by our event-sourcing approach (each prompt, action, outcome is recorded), so we can debug or audit after the fact.
- Audit Logs: Every action the agent takes should be logged in detail. This includes: timestamps, the exact prompt sent to the model (or a hash if we can’t store full prompt for IP reasons, though internally we likely can store it)  , which tool/command was executed with what arguments, the exit code and tail of its output, etc. These logs will be stored either in a file or a database for each session. They enable both internal debugging and external auditing (e.g., if a user says “the agent made a wrong change,” we can inspect exactly why it did that). The UI will expose these logs in a user-friendly way (the Logs panel). The system should also have an option to export these logs (as part of the artifact bundle or separately).
- Security Boundaries: Running code suggestions from an AI has risks. We enforce that all agent code execution happens in a sandbox. Concretely, the agent’s “Act” steps that execute commands will run in an isolated environment (like a Docker container or a restricted subprocess chroot jail) that has no access to the user’s system beyond the project folder. This prevents any malicious or accidental destructive operations (the agent shouldn’t be able to exfiltrate secrets or delete arbitrary files). The IDE plugin itself will not execute arbitrary commands; it delegates to the agent service which has these controls. Also, the agent service will have network access off by default (or only allow whitelisted domains if needed for package installation, etc.), preventing it from, say, calling external APIs unless explicitly allowed (some tasks might need internet, but that would be opt-in). We will also sanitize log content shown to the user (no leaking of sensitive file paths or keys). Essentially, treat the agent like running untrusted code – because it sort of is – and sandbox accordingly.
- Performance Budgets: To ensure a good UX, we’ll set budgets and timeouts. For example, if the agent is taking more than, say, 5 minutes without result, the UI should surface an option to cancel or notify the user. We might set default cost limits as well if using paid API (e.g., don’t spend more than $X per run without user confirming). The UI will show a progress indicator or step count so the user knows it’s working and not hung. We’ll implement streaming output so that even a long-running test will show partial progress (e.g., if tests are running for 2 minutes, stream the output every few seconds to the Logs panel, rather than nothing then a big dump). For memory, the agent should not exhaust the system: we may need to monitor and kill if it uses too much (especially important in an IDE setting where user’s machine might be modest). The design target is that for most issues, the agent produces a result in under ~2 minutes and costs maybe a few cents of API usage – these are soft goals, but we’ll test and refine to approach them. If an attempt is exceeding these, it likely indicates a problem (stuck in a loop or extremely large code; we then prompt user to continue or stop).
- Privacy: If this is used on proprietary code, we must ensure that code or descriptions are not sent to external services without permission. That means if we integrate with a cloud LLM API, we need user API keys and clear info that code will be sent to vendor. In an enterprise setting, there might be an on-prem model instead. Our PRD assumes an architecture flexible to use local or remote models. We should also store as little sensitive data as possible – e.g., logs can contain code snippets, so those logs should be kept locally or in a secure store. If a user opts out of telemetry, we don’t upload their logs. Any crash reports or analytics need to anonymize or hash content. Essentially, treat user code as highly confidential by default.







### 6. Telemetry & Evaluation





To continuously improve the agent, we’ll build telemetry into the system:



- Event Logging: As mentioned, each significant event during an agent run will be logged with structured data. Concretely, for each step we log:

  

  - A unique session ID and step index.
  - If it’s an LLM call: a hash or ID of the prompt, which model, and maybe length of input/output.
  - If it’s a tool call (e.g., run tests): the command run, timestamp, exit code.
  - The outcome: e.g., “exit_code=1, tests_failed=2” or “exit_code=0, all tests passed”.
  - Patch stats: when a patch is generated, log number of files changed, lines added/deleted.
  - Cost information: token usage for each LLM call (if available), etc.

  

  These logs are output to local files (for user to see) and can optionally be sent to an internal server for aggregate analysis (with user consent, in an open-source scenario).

- Metrics Dashboard: We will develop (internally) a dashboard that aggregates this telemetry to track:

  

  - Overall pass rate by repository (so we can see, e.g., 90% on Django, 70% on Sympy, etc., and identify weak spots).
  - Failure taxonomy: categorize failures from logs (did we fail due to a test assertion, a timeout, an exception in agent, etc. – this we can parse from the logs). We’d produce a chart like “30% of failures are due to test assertion remained, 20% due to coverage (patch incomplete), 10% due to timeouts…”.
  - Cost distribution: average cost per issue, and distribution (e.g., 50% of issues cost <$0.05, but 5% cost >$0.50 because they needed many attempts). This helps optimize cost.
  - We will also track usage: how often users invoke multi-patch, how often they accept vs. modify patches, etc., to inform product decisions.

  

  These dashboards may be implemented using existing analytics (could be as simple as logs that can be loaded into a Jupyter notebook for analysis by the team, or a more formal Grafana if needed). For the scope of the PRD, it suffices that the system produces the data needed to evaluate itself.

- Exact logging of events: Each agent run should produce a structured log that can be analyzed. For example, a JSON or YAML log per session:



```
session_id: 2025-12-17_abc123
issue: "Cannot login with unicode username"
model: "Claude-Opus-4.5"
events:
  - step: 1, action: "run_tests", target: "UsernameValidatorsTests.test_unicode_name", outcome: "fail", error: "AssertionError 'InvalidUsername'..."
  - step: 2, action: "model_think", prompt_id: "hash123", summary: "Model suggests adding normalization in validate_username"
  - step: 3, action: "edit_code", file: "auth/validators.py", diff_summary: "+1 line"
  - step: 4, action: "run_tests", target: "UsernameValidatorsTests.test_unicode_name", outcome: "pass"
  - step: 5, action: "finish", result: "success"
metrics:
  duration: 45s
  tokens_used: 12000
  cost_usd: 0.36
```

(The actual data may differ, but this illustrates what we gather.)



These logs allow us to regenerate metrics like pass rate easily. For example, pass rate = (# of sessions with result success) / (total sessions). We can filter by repo or other tags easily from structured logs.



- User-facing telemetry: We will allow power users to see some metrics in the IDE too (especially internal ones). For instance, after running on a whole set of issues, show “Via2 solved X of Y issues (Z%). Avg cost: $0.NN, Avg time: MM:SS.” This is more for our internal evaluation engineers – but it could also be a selling point for users to know how effective the agent was on their code.







### 7. Architecture





The system will follow a client-server architecture within the IDE integration:



- IDE Extension (Client): This is the part running inside the user’s IDE (e.g., a VS Code extension). It handles the UI (panels, buttons) and communicates with the agent service. It is responsible for capturing user actions (e.g., user clicked “Run Agent”) and displaying results (diffs, logs). The extension should be fairly thin, delegating heavy computation to the service. It communicates via a local API – likely HTTP or WebSocket to the agent backend.

- Agent Service (Server): A local (or network) service that encapsulates the Via2 agent logic. It can be a process launched with the IDE or a persistent daemon. It receives JSON requests like “solve issue {id} with description…and failing test…”, and orchestrates the agent loop. It interacts with the codebase (reading/writing files in a sandbox workspace) and possibly spawns sandbox containers for test execution. It interfaces with the LLMs via a Model Gateway component (could call out to cloud APIs or a local model).

- Sandbox Runner: A subsystem (could be part of Agent Service or separate) that executes code safely. For example, a Docker container image preloaded with the project’s dependencies and tests. The agent service will send commands to this sandbox (like “run tests” or “apply this patch and run code”). The sandbox returns outputs securely. In a local setup, this might just be a subprocess with restricted permissions, but enterprise users might configure an isolated container or VM. The architecture will treat it as a replaceable component (e.g., implement Sandbox.run(command, context) which can have different backends – local, Docker, remote).

- Model Gateway: This component abstracts the LLM API. We can plug in different providers. For instance, it might have implementations for calling Anthropic, OpenAI, etc., or even a local model server. The Agent Service uses the gateway rather than calling the model APIs directly, to allow easy switching. The gateway can also implement caching of prompts as discussed.

- APIs: Communication between these components:

  

  - IDE -> Agent Service: likely HTTP REST or JSON-RPC. For example, a POST /solve with issue data, and a GET /status/{session} to poll progress, or a WebSocket that pushes events. WebSocket is ideal for streaming (logs, partial results).
  - Agent Service -> Sandbox: Could be direct function calls if sandbox is a thread or local process. If using Docker, it might be via Docker Engine API or a command-line. But the Agent Service should encapsulate it so that the rest of the code just calls something like sandbox.execute("pytest...").
  - Agent Service -> Model Gateway: Could be local function if gateway is a library, or HTTP if gateway is remote. But likely just a Python API call that hides whether it’s calling an API or a local model.

  





We will define request/response schemas for these APIs. For instance, the solve request contains:

```
{ "issue_id": "123", "description": "...", "failing_tests": ["module.TestClass.test_name"], "repo_path": "/path/to/workspace", "options": {"candidates": 1} }
```

and the response (streamed) will include events like:

```
{ "event": "status", "message": "Running tests", "phase": "testing", "progress": 0.2 }
{ "event": "test_result", "test": "TestClass.test_name", "status": "fail", "details": "...trace..." }
{ "event": "patch_generated", "diff": "diff --git a/... etc." }
{ "event": "final", "status": "success", "patch_applied": false }
```

(This is illustrative; exact schema to be refined.)



- Plugin points: Our architecture will allow extension in key areas:

  

  - Test adapters: As mentioned, we can add new adapters for running tests. This could be done by having an interface (abstract class) TestRunner with methods run_test(test_identifier) that each framework implements. The agent service decides which one to use based on config. Adding a new testing framework would mean implementing that interface and registering it.
  - Repo adapters: If we integrate with different version control or project types, we abstract away operations like applying a patch. Right now, we assume a git-based file system project. If someone wanted to adapt Via2 to, say, a database of code or a different environment, they could implement a repository interface with methods like load_file, save_file, etc. For our scope, repository is just the file system, but we design with this abstraction in mind (for example, to integrate with remote repo or a large monorepo with special rules).
  - Model adapters: The Model Gateway can have multiple model drivers. We ensure it’s easy to add, say, a new LLM API by writing a small wrapper that conforms to our interface (e.g., generate_text(prompt, **params) returns text). Also allow choosing model per task or using multiple simultaneously (for ensemble) through configuration.

  





Overall, the architecture emphasizes modularity: the IDE extension, agent core, and sandbox are distinct so we can upgrade one without affecting others (for instance, we could run the agent service on a more powerful machine or cloud, and the IDE just connects to it).





### 8. Acceptance Criteria





To consider this project successful, we define clear criteria for each feature:



- SWE-bench parity: Validation harness produces identical outcomes as official SWE-bench. For acceptance, we will run a sample of issues with our IDE-integrated harness and compare results to running them with the SWE-bench CLI – they should match 100%. For example, if an issue passes in our IDE, it must pass in SWE-bench CLI (function-level) and vice versa, barring flake. Acceptance metric: 100% correlation within tolerance (e.g., a known 6.2% overfit issues aside, which we’ll handle by manual check)  .
- Patch application: User can apply and revert patches with no code corruption. We will test: agent suggests a patch, user clicks apply, the changes appear in the editor and all tests still pass. If user clicks revert, code returns exactly to previous state. Acceptance: In 10 trial runs on sample issues, patch apply and revert work each time without losing any unrelated code changes.
- IDE responsiveness: Agent status updates at least every X seconds and UI remains interactive. Acceptance threshold: Even during a long operation (e.g., running tests for 2 minutes), the UI should show progress (like streaming test output) at least every 5 seconds, and the user should be able to press “Cancel” to abort. We simulate a long test and ensure the cancel button stops the agent within 5 seconds and frees the UI.
- Multi-candidate workflow: Agent can produce multiple solutions and highlight the best. Acceptance if: in a scenario with an ambiguous bug (where two different fixes both pass tests), the system presents at least two candidate diffs to the user, and clearly indicates which one it recommends (e.g., “Patch A fixed the bug and passed all tests”). Also, if none pass, it should present the partial info (“all attempts failed”) without crashing. We’ll create a dummy issue where one candidate fixes one test but breaks another and ensure the agent picks correctly or shows both outcomes.
- Telemetry logging: System logs the required metrics/events per run. We will complete a run and then inspect the generated log or telemetry output. Acceptance if the log contains: prompt hash, each command and its exit code, tail of output, patch diff stats, etc., as enumerated earlier. Also ensure sensitive info (like full code) is either not logged or properly protected (depending on settings).
- Security test: Agent actions are contained and cannot affect system outside workspace. We will perform a pentest-like scenario: have the agent suggest a malicious command (like writing to /etc/passwd or reading an env var). In the sandbox, that should either fail or be a no-op, and the security monitor should flag it. Acceptance if the agent cannot delete or modify files outside the project folder and cannot access network (unless explicitly allowed). Also ensure that if agent tries something disallowed, the user is warned or it’s logged.
- Usability (developer acceptance): A senior IDE engineer can follow the agent’s process and use it without confusion. This is qualitative: we will have a couple of experienced developers use the plugin on a sample bug and gather feedback. Acceptance criteria: they are able to run the agent, understand what it’s doing (thanks to the UI panels), and apply a patch successfully. Any point of confusion (e.g., unclear messaging, or they don’t know what to do next) will be addressed. Essentially, “could an engineer use this tool end-to-end on a real bug and be satisfied with the experience?” must be yes.





Each of these criteria will be tested before release. Meeting all means the product is ready to roll out.





### 9. Rollout Plan





We will roll out the Via2 IDE Agent in phases to mitigate risk and gather feedback:



- Phase 0: Internal SWE-bench Runner in IDE (alpha) – Timeline: ~1 month from now. This is a version used by our team to run SWE-bench evaluations through the IDE interface. We integrate it with our internal codebase and use it on the 500 benchmark issues. Purpose: shake out any discrepancies in harness, ensure all metrics/logging are correct, and refine UX for the solve workflow without external pressure. In this phase, we likely limit to our evaluation engineers. Success criteria: internal team can reproduce the 71.8% (or new 80% after improvements) via the IDE tool, and we catch any UI or performance bugs.
- Phase 1: Real Repos Opt-In (beta) – Timeline: ~2 months from now. We extend access to selected power users (could be some open-source maintainers we collaborate with, or an internal dev team) to use Via2 on actual issues in their repos. This will be an opt-in beta where users understand it’s experimental. Key goals: ensure the agent generalizes beyond the benchmark (maybe issues without a strict test case, etc.), and evaluate the integration in diverse environments (different OS, different project sizes). We’ll gather user feedback on usability and trust – e.g., do they feel confident applying patches? We will also monitor for any major failures or false positives. If needed, we refine the UI or add safety checks here. By end of Phase 1, we expect to solve real bugs in, say, our internal services or some OSS projects with at least 70-80% success, and have users regularly applying those patches.
- Phase 2: Team Deployment (GA) – Timeline: ~3-4 months from now. After incorporating beta feedback, we roll out to entire engineering team (or release publicly for OSS if that’s the plan). This is the general availability where the plugin is stable, documented, and possibly integrated into the company’s IDE setup by default. We include user documentation, best practices (e.g., “review diffs carefully, here’s how to write good issue descriptions for the agent,” etc.). We also set up support channels for any issues. In this phase, the agent will start being used in day-to-day workflows. We’ll keep monitoring metrics – particularly, we want to see that in production use it consistently hits ~80% success on first or second attempt, and reduces time spent on issues. We also plan a retrospective after a month of full usage to assess ROI (did it truly save engineering hours, which types of issues is it best at, etc.), which will inform further improvements or feature cut if needed.





Each phase has clear entry/exit criteria (alpha success leads to beta, etc.). We expect to iterate quickly in Phase 0/1 when issues are easier to fix, and treat Phase 2 as more about scaling and support.





### C3. IDE Implementation Assumption Details





(The following technical specifics are incorporated into the architecture/design above, but reiterated to ensure nothing is missed.)



We assume the IDE can initiate requests to a local agent service running on the developer’s machine (or a remote server in some setups). Communication will be via JSON-based messages, with support for streaming updates. Specifically:



- Message types: We will define messages like StartSolveRequest (with issue info), AgentStatusUpdate (with fields like phase, message, progress), AgentResult (with final outcome and patch). Also messages for user actions: CancelRequest, PauseRequest, ResumeRequest. The extension and service both understand these.
- Streaming logs: The agent service will stream log events over a WebSocket. As the agent runs, it sends messages for each log line or significant event, which the IDE receives and appends to the Logs/Plan panel in real-time. This gives the “live running commentary” effect. We will ensure chunking so that, for example, a 1000-line test output doesn’t send 1000 separate tiny messages (maybe batch by 5 lines or 1KB at a time). The streaming will include heartbeats or progress so the UI can show a spinner or progress bar.
- Patch application semantics: The agent service doesn’t directly modify open editor buffers. Instead, it sends the diff in a structured format (e.g., unified diff text or a list of file changes) to the IDE extension. The extension then highlights this diff for the user. If user clicks “Apply,” the extension applies changes to the workspace files (it has access to modify files in the IDE). We ensure this operation is atomic and undoable: for instance, the extension could initiate a Git branch or at least stage the diff in git so it can be reverted. If the project is not under git, we implement our own backup. The semantics are: do not auto-apply without user consent, and once applied, track the state so that “Cancel” or “Undo” can restore.
- Cancellation/Pause/Resume: The user can cancel an ongoing run via a button. The extension will send a CancelRequest to the agent service. The agent service then stops generating or executing further steps. Implementation-wise, we will either leverage the LLM API cancellation (Anthropic/OpenAI support aborting requests), or if not, we might run each step in a separate process that can be killed. For pausing, if a user hits “Pause,” the agent should complete the current atomic action (e.g., finish running tests or finish the current model call) and then not proceed to the next step until user hits “Resume.” This can be done by the agent loop checking a flag before each iteration. Resume simply clears that flag and continues. Acceptance: Cancel actually stops within e.g. 5 seconds, and pause truly halts new steps (we’ll test this).
- Artifact bundle export: When requested, the agent service compiles all relevant outputs: the final patch (as diff or patched files), the logs of the session (which we have), and a JSON of environment info (e.g., commit hash of code, agent config used, etc.). It then either sends this to the extension to save as a file, or directly writes a zip file to disk and gives the path to the extension. The artifact ensures reproducibility: another engineer could take it and see what was done and apply the same diff. This is especially useful if the fix is handed off (e.g., attach to an email or issue tracker).





We will keep the architecture IDE-agnostic: while we plan a VS Code extension initially (for example), the agent service and protocol could be used by any editor or even a web UI. We reference VS Code’s UX just as a familiar model (e.g., panels, notifications) but implement everything in a generic way. For instance, the UI is not hardcoded to VS Code APIs – we could have a JetBrains plugin in the future using the same backend.



By fulfilling all the above requirements and design choices, we ensure the Via2 IDE-integrated agent is robust, user-friendly, and effective, allowing developers to harness our orchestration improvements directly in their daily workflow.