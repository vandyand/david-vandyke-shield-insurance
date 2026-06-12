# AI-Driven Ad Creative Optimization: Research Report
# David VanDyke Shield Insurance — Proposed "Genome" Loop Architecture

**Research scope:** Corroborate or refine a proposed evolutionary/AI-driven creative optimization loop
**Researched:** 2026-03-26
**Overall confidence:** MEDIUM (ecosystem is fast-moving; some findings are HIGH, others require field validation)

---

## The Proposed Architecture (Summary)

Two "genomes" under optimization:
- **Ad genome:** image + copy (fitness signal: Meta CTR/CPL)
- **Landing page genome:** copy variants (fitness signal: GA4 booking rate)

Mechanism: LLM-driven structured variant generation with memory of past winners, weekly performance
pull, bi-weekly generation, monthly pruning, human review gate, Thompson sampling-style budget
allocation, 80% Bayesian confidence threshold.

---

## Research Finding 1: State of the Art — AI Ad Creative Tools

**Verdict: The proposed approach is ahead of most SMB tooling but directionally consistent with where the industry is moving.**
**Confidence: HIGH**

### What exists commercially

**Meta Advantage+ Creative (native)**
Meta's own system does automated creative variation, but it operates as a black box. In 2025 Meta
introduced full image variation generation, text overlay AI, and multi-format adaptation from a
single asset. Their GEM (Generative Ads Model) processes thousands of behavioral signals to rank
ads, achieving a measured 5% lift in Instagram conversions and 3% in Facebook Feed conversions
after rollout.

Key limitation for this use case: Advantage+ optimizes within Meta's objective, not against an
external fitness signal like GA4 booking rate. It cannot close the loop to actual booked
appointments. It also surrenders all creative control — which for insurance messaging (compliance,
trust positioning, niche specificity) is a real risk. Meta's own docs note the AI "may not fully
understand nuanced brand messaging."

**AdCreative.ai**
Claims 42% average CTR lift in first month. Uses proprietary AI to generate and score creatives.
Score is a predicted performance number, not a realized fitness signal. Works for volume creative
generation but does not implement a feedback loop — you generate, you manually pick, you run.
No memory of what worked for your specific audience. Pricing: $25-149/month.

**Pencil**
More sophisticated — includes performance prediction, agent-based workflows, image-to-video, and
chat-based iteration. Better DX for revision cycles. Still does not close the loop to actual
downstream conversion events. Enterprise-pricing tier for the advanced features.

**Pattern89 (now part of Shutterstock)**
Was a leading AI creative intelligence tool. After the Shutterstock acquisition the standalone
product was folded in. The original insight (which elements predict performance from visual
analysis) is now embedded in Shutterstock's platform, not independently accessible.

**Madgicx**
Meta-focused platform with automated ad launch, creative scaling, and audience tools. Closer to an
autonomous ad management layer than a creative generation system. Does automated budget allocation
toward winners (relevant to the MAB component).

### What the proposed system does differently

The proposed system is different from all of the above in three meaningful ways:

1. **External fitness signals.** Using GA4 booking rate as the fitness signal for landing page
   variants, not Meta's proxies (link clicks, leads) — this is the right signal. Meta's
   optimization objectives are not aligned with "person who booked a consultation call."

2. **LLM-driven mutation with memory.** No commercial SMB tool maintains explicit memory of
   past winners and encodes that into generation prompts. This is the correct approach: a growing
   context of what angles/hooks/elements have worked vs. failed for this specific insurance agent
   in this specific market.

3. **Human review gate.** All commercial tools either skip this (fully automated) or make it
   cumbersome. Keeping a human gate is the right call for an insurance business where a single
   non-compliant ad can trigger an account suspension.

**Recommendation:** Do not replace the proposed approach with any of these tools. Use them as
inspiration or for bulk asset generation (especially AdCreative.ai for initial image variants),
but the custom loop architecture is more appropriate for this use case.

---

## Research Finding 2: Statistical Approach — Bayesian 80% Confidence at Low Traffic

**Verdict: 80% Bayesian confidence is reasonable for this context with important caveats.**
**Confidence: HIGH (the math is well-established; the caveats are non-negotiable)**

### The core argument for 80% Bayesian confidence

For a local insurance agent with low booking volume, frequentist 95% significance is
mathematically unattainable in reasonable time. With a 2% baseline booking rate (industry
benchmark for insurance landing pages is 1-3%), detecting a 30% relative improvement requires
~3,000 visitors per variant — at 50 visitors/day per niche page, that is 60 days minimum, and
niche pages get less than that.

Bayesian A/B testing with a Beta-Binomial model is the right framework. The posterior gives a
direct probability: "There is an 80% chance variant B has a higher booking rate than variant A."
This is actionable framing. At this scale and decision stakes (not a surgery, not a drug trial),
an 80% posterior probability is a defensible decision threshold.

### The peeking problem — a real risk

**This is the most important caveat in the entire architecture.**

Bayesian A/B testing is NOT immune to the peeking problem. Multiple sources (including a 2025
analysis by Alex Molas) confirm that stopping a Bayesian test early when the posterior hits a
threshold inflates false positive rates substantially. Research shows that peeking after every 100
observations with a 95% threshold as a stopping rule produced false positive rates of ~80%.

The mitigation is straightforward: **pre-commit a minimum sample size before reading results.**
A minimum of ~200 observations per variant is a practical floor that eliminates most false
positives in low-volume scenarios. For this project, that means:

- Do not read landing page test results until each variant has received at least 200 visitors
- Do not stop a test because the posterior hit 80% at 50 visitors per variant
- Run the test for the pre-committed window (suggested: minimum 4 weeks, minimum 200 visitors
  per variant, whichever comes last)

### Expected loss as the stopping criterion

Rather than "posterior probability of winning," use **expected loss** as the stopping rule. Ask:
"If I choose variant B and I'm wrong, how many bookings do I expect to lose per week?" If that
number is small (say, less than 0.5 bookings), then the decision is low-stakes enough to act at
80% confidence. If the expected loss is large, wait longer. This framing is more honest about the
asymmetry of decisions than a single probability threshold.

### Recommended adjustment

Replace the single "80% confidence threshold" with a compound stopping rule:
- Minimum 200 visitors per variant AND minimum 2 weeks runtime
- Expected loss below threshold (calibrate based on actual booking value)
- Posterior probability above 75-80%

All three conditions must be met, not just one.

---

## Research Finding 3: Multi-Armed Bandit for Budget Allocation

**Verdict: Thompson sampling is the right algorithm. The architecture is sound. One structural caveat.**
**Confidence: HIGH**

### Thompson sampling vs. epsilon-greedy

Thompson sampling is superior to epsilon-greedy for this use case. Key differences:
- Epsilon-greedy allocates a fixed percentage (say 20%) to exploration regardless of certainty
- Thompson sampling allocates exploration proportionally to uncertainty — explores more when
  uncertain, exploits more when confident

This is exactly right for ad creative testing where you want to keep 1-2 explore slots while
aggressively funding the winner.

Academic research (ResearchGate, Semantic Scholar) comparing both on marketing datasets confirms
Thompson sampling consistently outperforms epsilon-greedy on regret minimization.

### The structural caveat: Meta's learning phase conflicts with MAB

**This is the most practically important finding for the MAB component.**

Meta's algorithm requires ~50 conversion events per ad set per week to exit the "learning phase."
If you have 3 ads in an ad set and Thompson sampling is routing 80% of budget to the winner,
the 2 explore ads may never accumulate enough conversions to give Meta's system clean optimization
data. Meta's system and your MAB system can work at cross-purposes.

Recommended structural approach to resolve this conflict:

**Option A (preferred for small budgets):** Run each ad in its own separate ad set with its own
small budget. This gives Meta clean learning data per creative. Manually adjust budgets weekly
based on your own Thompson sampling calculation. More manual overhead, more correct.

**Option B:** Use a single ad set with CBO, accept that Meta does its own allocation, and use your
MAB only to decide which ads to *keep or retire*, not to actively shift budget in-flight. This
reduces your control but reduces learning phase conflicts.

For the proposed bi-weekly generation and monthly pruning cadence, **Option B is pragmatically
better** because it doesn't require weekly budget micro-management per ad, and it aligns with the
human-review-gate model.

### Multi-armed bandit and low budget reality

The minimum budget for a meaningful MAB experiment is worth quantifying. If total ad budget is
$30/day across 4 creative variants, each variant gets roughly $7.50/day. At a $15-30 CPL (typical
for insurance), that is 0.25-0.5 leads per day per creative. The bandit algorithm needs enough
signal to update confidently. At this volume, the "bi-weekly generation" cadence is appropriate —
weekly would produce too little signal to act on.

---

## Research Finding 4: Which Creative Elements Drive the Most Variance

**Verdict: Image/visual dominates. The mutation type priority in the proposed architecture is partially misaligned.**
**Confidence: MEDIUM-HIGH (industry consensus, limited RCT evidence)**

### Variance contribution by element

Cross-campaign analysis (reported by multiple agency sources) consistently finds:
- **Creative image/visual:** 60-80% of CTR variance
- **Primary text (body copy / hook):** 15-20% of CTR variance
- **Headline:** 10-15% of CTR variance
- **CTA button text:** 5-8% of CTR variance
- **Description:** 2-5% of CTR variance

The proposed mutation types — hook variation, copy simplification, visual contrast, niche
specificity, crossover — are weighted toward copy mutations. Copy matters, but the image is the
element that creates the largest performance swings.

### Implication for mutation strategy

The proposed system should prioritize visual mutations first, copy mutations second:

**High-priority mutation types (image-level):**
- Visual style shift (professional headshot vs. lifestyle vs. abstract risk imagery)
- Niche visual specificity (contractor tools vs. restaurant kitchen vs. general)
- Contrast and attention pattern (bright vs. muted, text overlay vs. clean)
- Hook-as-image-text (the "hook" can live in a text overlay on the creative, not just body copy)

**Secondary mutation types (copy-level):**
- Hook framing (problem-first vs. solution-first vs. social proof-first)
- Copy simplification (short punchy vs. explanatory)
- Niche specificity in language ("contractors" vs. "business owners" vs. generic)
- CTA variation ("Get a quote" vs. "Book a 15-min call" vs. "See your rate")

### The crossover mutation type

The "crossover" mutation (mixing elements from two winners) is a legitimate genetic algorithm
concept, and there is some practitioner evidence it produces novel performers. However, it
requires a meaningful library of past winners to draw from. Recommend implementing this only in
month 3+, after the system has generated and evaluated enough variants to have real material to
cross.

---

## Research Finding 5: Creative Refresh Cadence and Ad Fatigue

**Verdict: The proposed bi-weekly generation cadence is slightly slower than optimal. Weekly refresh is achievable and better.**
**Confidence: HIGH**

### What the data shows

- **Top-performing brands** refresh creative every 10.4 days on average (MotionApp analysis)
- **Frequency threshold for fatigue:** Cold audiences: frequency >2.5-3 triggers CTR decline;
  >4 triggers significant CPM and CPC increases; >6 shows measurable purchase intent drop
- **Meta's internal finding:** People who see the same ad 6-10 times are 4.1% less likely to
  purchase than those who saw it 2-5 times
- **General refresh recommendation:** 2-4 weeks for Meta, with faster refresh for higher-spend
  accounts (more spend = faster audience saturation)

### For David's specific situation

At $20-30/day total spend, the audience exposure rate is low. This extends ad lifespan
meaningfully. A creative at $25/day in a Michigan local audience will reach saturation much slower
than the same creative at $250/day nationally. The bi-weekly generation cadence is therefore
**more defensible** at low spend than at high spend.

Practical signals to watch (use as triggers for off-cycle refresh regardless of cadence):
- Frequency > 3 in a 7-day window
- CTR drop > 20% week-over-week
- CPL increase > 30% week-over-week without audience or seasonality explanation

### Meta's similarity score risk

Meta now flags ads that are too similar to each other. Running 5 variants where 4 are the same
image with different body copy text will generate a high similarity score, which causes the ads to
compete against each other in the auction (self-competition) and delays learning phase completion.

**Important architectural implication:** Variants must be genuinely different across multiple
dimensions. Four variations of "same image, different copy" is not four genomes — it is one genome
with minor allele variations. The mutation system should enforce diversity by requiring at least
the image to differ between ad set variants.

---

## Research Finding 6: Meta Guidance for Small Budgets and Creative Diversity

**Verdict: Meta's guidance is directionally consistent with the proposed approach but has specific structural requirements.**
**Confidence: HIGH (official Meta guidance)**

### The creative-as-targeting insight

Meta's March 2025 guidance explicitly states: "With AI-enabled advertising tools, the focus has
shifted from niche targeting to creative diversification as the best lever to find relevant
audiences." This is the single most important strategic alignment between Meta's system and the
proposed architecture.

Because insurance falls under the Special Ad Category (Financial Products and Services), you
cannot target by age, gender, ZIP code, interests, or lookalikes seeded from customer lists
(restrictions tightened March 2025). Creative message match is the *only* available targeting
lever. The "genome" approach — systematically mutating niche-specific messages — is exactly the
right response to this constraint.

### The 50-conversions-per-week learning phase requirement

Meta requires approximately 50 optimization events per ad set per week to exit the learning phase.
This is a hard constraint that interacts with the proposed architecture in two ways:

1. **Too many variants kill the learning signal.** If the $25/day budget is split across 5
   variants in one ad set, Meta gets ~10 conversions per creative per week — not enough to learn.

2. **Weekly re-generation resets learning.** Every time you pause, add, or significantly change
   an ad within an ad set, Meta may reset the learning phase for that ad set. The proposed
   bi-weekly generation cadence is wise for this reason — weekly would be too disruptive.

**Structural recommendation:** For a $25-30/day budget, run maximum 2-3 active variants in an ad
set at any given time. More variants dilutes the learning signal below the threshold where Meta's
own optimization can help.

### Advantage+ Creative as a complement, not a replacement

Meta reports an average 9% lower CPA when Advantage+ Creative enhancements are enabled (text
optimization, image cropping, format adaptation). This is "free" improvement on top of your
creative — you keep your copy and image, Meta adapts the framing for different placements. This
should be **enabled** for all production ads and considered a baseline, not an optimization.

The proposed custom loop handles what Advantage+ cannot: generating new creative directions,
tracking downstream conversion to bookings (not leads), maintaining memory of what has worked
for this specific agent.

---

## Research Finding 7: Open-Source Frameworks for the Creative Loop

**Verdict: No purpose-built open-source framework exists for this exact use case. The components exist; the composition does not.**
**Confidence: HIGH (absence confirmed by multiple searches)**

### What exists

There is no open-source "ad creative optimization loop" framework that combines:
- LLM variant generation with structured output
- Fitness signal integration (Meta API + GA4)
- Multi-armed bandit budget allocation
- Memory of past winners

These are four separate problem domains, each with good open-source tooling. The composition is
the novel part.

### Relevant component libraries

**For the LLM generation + memory layer:**
- LangChain / LangGraph — agent orchestration with tool use and structured output
- Instructor (Python) — structured output from LLMs with validation (Pydantic models)
- LlamaIndex — if long-form winner/loser memory needs semantic retrieval

**For the statistical / MAB layer:**
- `pymc` (Python) — Bayesian A/B testing, Beta-Binomial posteriors, expected loss calculation
- `mab` (Python, multiple libraries) — Thompson sampling implementations
- `scipy.stats` — beta distribution math for manual Thompson sampling

**For the data pipeline:**
- Meta Marketing API (Python SDK: `facebook-business`) — pull CTR/CPL per ad
- GA4 Data API (Python: `google-analytics-data`) — pull booking conversion rate per page/variant
- `schedule` or Prefect / Airflow for the weekly/bi-weekly cron triggers

**No integration layer needed at this scale.** A Python script with cron scheduling, a SQLite or
simple JSON store for winner memory, and API calls to Meta + GA4 is sufficient. The proposed
architecture does not need a framework — it needs a well-structured script.

### Closest reference implementation

The "generation-verification-reflection loop" pattern documented in LLM agent memory research
(2025 arxiv survey) is the closest published concept to the proposed architecture. The sequence:
generate variants → deploy → measure fitness → reflect (which elements worked) → regenerate with
memory of reflection → repeat. This is exactly the proposed loop, implemented at the level of
ad copy rather than code generation.

---

## Research Finding 8: Insurance-Specific Creative Constraints

**Verdict: Insurance ads on Meta have compliance constraints that must be wired into the LLM generation prompt.**
**Confidence: HIGH**

### Special Ad Category requirements

Insurance is classified under "Financial Products and Services" in Meta's Special Ad Category
framework. Running insurance ads without selecting this category can trigger account suspension.

When selected, the following targeting options are **unavailable:**
- Age targeting (only 18-65+ available)
- Gender targeting
- ZIP code targeting (minimum 15-mile radius)
- Lookalike audiences seeded from customer lists (as of March 2025)
- Most interest-based detailed targeting

This means **the creative is the only targeting lever.** Niche-specific copy ("Are you a roofing
contractor?") functions as the targeting by causing the right people to self-identify and engage.
This is not a workaround — it is the intended Meta approach for Special Ad Categories.

### Compliance requirements for LLM-generated copy

The LLM generation prompt must include hard guardrails:
- No age-specific language ("seniors," "young families," "retirees")
- No income-specific language ("low-income," "affordable for everyone")
- No language that could be read as discriminatory in access to financial products
- All copy must be reviewed by a human before publish (the proposed human-review gate handles this)
- No promises about pricing or coverage that cannot be substantiated ("cheapest," "best rates")

Recommended: Maintain a compliance blocklist as part of the LLM system prompt. Have the human
reviewer use this checklist explicitly, not just "looks good" review.

---

## Synthesis: What the Research Corroborates vs. Challenges

### Corroborated

| Proposed Element | Research Finding | Confidence |
|-----------------|-----------------|------------|
| Two-genome approach (ad + landing page) | Correct separation of signal sources; GA4 booking rate is better than Meta's proxy signals | HIGH |
| LLM-driven structured variant generation | No competing framework; composition of existing tools is the right approach | HIGH |
| Human-in-the-loop review gate | Mandatory for insurance compliance; Meta account suspension risk is real | HIGH |
| 80% Bayesian confidence (not 95%) | Correct for low traffic; 95% is mathematically unattainable | HIGH |
| Weekly pull, bi-weekly generation cadence | Aligns with Meta learning phase protection and practical signal volume | HIGH |
| Monthly pruning | Correct hygiene; prevents winner memory from stale data accumulating | MEDIUM |
| Thompson sampling for budget allocation | Superior to epsilon-greedy; empirically validated on marketing datasets | HIGH |
| Niche specificity as mutation type | Confirmed most important creative lever given Special Ad Category targeting restrictions | HIGH |

### Challenged or Needs Refinement

| Proposed Element | Challenge | Recommended Adjustment |
|-----------------|-----------|----------------------|
| Hook variation as primary mutation | Image/visual drives 60-80% of CTR variance; hook variation addresses only 15-20% | Prioritize visual mutations first, copy mutations second |
| 80% confidence threshold as single stopping rule | Peeking inflation risk; naive implementation of "stop when posterior hits 80%" inflates FPR dramatically | Compound stopping rule: minimum sample size + minimum runtime + posterior threshold + expected loss |
| Crossover mutation type | Valid concept but requires a large enough winner library to be useful | Defer to month 3+; implement only when 10+ evaluated variants exist |
| MAB budget allocation in-flight | Conflicts with Meta's learning phase algorithm when too many variants compete for budget | Use MAB to decide which ads to retire/keep, not to micro-shift spend weekly; limit active variants to 2-3 per ad set |
| Memory of past winners | Correct concept; implementation detail: winners must be tagged by niche, not just by element type | Winner memory should be structured: niche × element × outcome, not a flat list |
| Mutation types as listed | Good list but missing "visual niche specificity" as an explicit mutation type | Add: visual representation of the target niche (images of contractors, restaurateurs, etc.) |

---

## Recommended Adjustments to the Architecture

### Adjustment 1: Flip the mutation priority order

Current: hook variation → copy simplification → visual contrast → niche specificity → crossover

Recommended:
1. **Visual niche specificity** (new category) — different images representing each niche's work context
2. **Visual contrast** — test attention-grabbing image styles (lifestyle photo vs. graphic vs. testimonial)
3. **Hook variation** — first line of body copy; second-highest variance driver
4. **Niche specificity in copy** — niche-specific language in body and headline
5. **Copy simplification** — length/density variation
6. **Crossover** (month 3+) — mix winning image × winning copy from different lineages

### Adjustment 2: Compound stopping rule for Bayesian decisions

Replace single 80% confidence threshold with:

```
STOP when ALL of the following are true:
  - minimum 200 visitors per variant (landing page) OR minimum 30 lead events per ad (Meta)
  - minimum 3 weeks runtime
  - posterior P(B > A) >= 0.80
  - expected loss < [threshold: calibrate to David's booking value / cost-per-outcome]
```

### Adjustment 3: Active variant count cap

Cap active ad variants per ad set at 2-3 at any given time.

Rationale: At $25-30/day, more variants means less signal per variant means Meta's learning phase
never completes. Generating 5 new variants bi-weekly is fine — but only 2-3 should be live
simultaneously. Retire the lowest performer before adding a new variant.

### Adjustment 4: Tag winner memory by niche × element × outcome

Structure winner memory as a matrix, not a flat list:

```json
{
  "niche": "contractor",
  "element_type": "image",
  "description": "close-up of contractor's hands with tools on blueprints",
  "outcome": "winner",
  "ctr": 3.2,
  "cpl": 18.40,
  "run_period": "2026-01-15 to 2026-02-01",
  "notes": "outperformed generic insurance office image by 2.1x CTR"
}
```

This structured format enables the LLM to reason about what worked at the intersection of niche and
element type, not just "images that worked."

### Adjustment 5: Treat Advantage+ Creative as baseline, not competition

Enable Advantage+ Creative enhancements on all live ads. This gives Meta permission to adapt
format, cropping, and minor text positioning for different placements without changing the core
creative. The 9% average CPA improvement from this is essentially free. Your custom loop handles
strategic creative direction; Advantage+ handles placement-level tactical optimization.

### Adjustment 6: Compliance system prompt layer

Add a compliance blocklist to the LLM generation system prompt and a human checklist to the
review gate. This is not optional for insurance — it is how you avoid account suspension.

---

## Tools/Libraries Worth Knowing About

| Tool | Purpose | Relevance |
|------|---------|-----------|
| `facebook-business` (Python SDK) | Meta Marketing API — pull ad performance | Required for fitness signal |
| `google-analytics-data` (Python) | GA4 Data API v1 — pull booking conversion rate | Required for fitness signal |
| `pymc` (Python) | Bayesian A/B testing, Beta-Binomial posteriors | Statistical engine |
| `instructor` (Python) | Structured LLM output with Pydantic validation | Variant generation |
| Madgicx | Third-party Meta management with creative analytics | Optional reference; shows what automated scaling looks like |
| Pencil | AI ad creative with performance prediction | Optional for bulk initial asset generation |
| AdCreative.ai | Rapid image variant generation from single asset | Useful for generating visual options cheaply before the loop has a winner library |
| MotionApp | Creative analytics for Meta ads | Good reference for creative fatigue metrics; useful if budget grows |

---

## Gaps and Open Questions

1. **Signal volume reality check.** The architecture needs a minimum signal volume to function.
   At $25/day with a $20-25 CPL, the system will generate ~1 lead per day per active campaign.
   At that volume, the Bayesian model will have very wide posterior distributions for weeks. Is
   the team prepared for 6-8 week test windows before actionable signals emerge? This needs an
   honest conversation upfront.

2. **Landing page variant traffic.** GA4 booking rate per variant requires traffic to each
   variant. The A/B infrastructure assigns variants randomly. At 20-30 paid visitors/day per
   niche page, accumulating 200 visitors per variant takes 2-3 weeks per niche. The general
   (non-niche) page will hit threshold fastest; niche pages will take longer.

3. **LLM generation quality for insurance.** LLMs generate generic marketing copy by default.
   The system prompt needs to be carefully engineered to produce insurance-specific, compliance-
   safe, niche-specific copy. This is a prompt engineering problem that needs iteration. Budget
   time for this.

4. **Image generation for visual mutations.** The architecture references "image" as the primary
   mutation type, but who generates the images? LLM text generation is cheap; image generation
   (DALL-E, Midjourney, stock) costs time or money. The image generation step needs a defined
   workflow: either AI-generated visuals (fast, cheap, generic), sourced stock photos (medium
   cost, professional), or custom photography (expensive, highest quality). For insurance SMB,
   professional stock photos of niche contexts (contractors, restaurateurs) are likely the
   right medium-term answer.

5. **GA4 ↔ Meta attribution consistency.** GA4 last-touch attribution and Meta's internal
   conversion tracking will disagree (iOS attribution gaps, cross-device, etc.). The team needs
   to pick one source of truth for the fitness signal and stick to it. Recommendation: GA4 is
   the source of truth for landing page booking rate; Meta is the source of truth for ad-level
   CTR/CPL. Do not try to reconcile them at the individual event level.

---

## Sources

- Meta GEM model: https://engineering.fb.com/2025/11/10/ml-applications/metas-generative-ads-model-gem-the-central-brain-accelerating-ads-recommendation-ai-innovation/
- Meta Advantage+ 2026 AI performance claims: https://about.fb.com/news/2026/01/2026-ai-drives-performance/
- AdCreative.ai review: https://www.bestever.ai/post/adcreativeai-reviews
- Pencil platform: https://trypencil.com/
- Meta Advantage+ pros/cons (Marpipe): https://www.marpipe.com/blog/meta-advantage-plus-pros-cons
- Bayesian peeking problem (2025): https://www.alexmolas.com/2025/10/30/bayesian-ab-test-peeking.html
- Bayesian expected loss stopping: https://towardsdatascience.com/how-to-analyse-a-b-experiments-using-bayesian-expected-loss-b959e21a77ce/
- Thompson sampling vs epsilon-greedy (marketing): https://www.researchgate.net/publication/353262478_Comparing_Epsilon_Greedy_and_Thompson_Sampling_model_for_Multi-Armed_Bandit_algorithm_on_Marketing_Dataset
- MAB for creative testing: https://persona.ly/glossary/performance-metrics/creative-testing-multi-armed-bandit-vs-a-b-testing/
- Creative element variance (image > copy): https://insights.vaizle.com/anatomy-of-a-facebook-ad/
- Creative refresh cadence: https://motionapp.com/blog/ad-fatigue
- Meta creative fatigue and similarity score: https://www.admetrics.io/en/post/meta-creative-fatigue-and-similarity-score-complete-guide
- Meta special ad categories 2025: https://www.data-axle.com/resources/blog/meta-special-ad-categories-rules/
- Meta learning phase: https://motionapp.com/blog/ultimate-guide-creative-testing-2025
- Insurance Facebook ads best practices: https://goadfuel.com/facebook-ads-for-insurance-agents/
- Meta CBO best practices: https://www.adamigo.ai/blog/cbo-best-practices-meta-ads
- Sequential testing and CUPED: https://craftuplearn.com/blog/ab-testing-low-traffic-sequential-testing-smart-baselines
- Multi-armed bandits 2025: https://www.webpronews.com/multi-armed-bandits-revolutionize-digital-marketing-optimization-in-2025/
