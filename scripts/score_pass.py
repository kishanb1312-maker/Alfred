#!/usr/bin/env python3
"""Stage-2 SCORING pass. Reads data/research_merged.json (36 records, all research
already done and local), applies one rubric to all 36, and splits into
data/research_output.json (>= match_threshold) and data/research_dropped.json.

No network. Every evidence field from the merged input is preserved verbatim.
"""
import json
import os
import re

ROOT = "/Users/kishan/Documents/WarmApply"
MERGED = os.path.join(ROOT, "data/research_merged.json")
OUT = os.path.join(ROOT, "data/research_output.json")
DROPPED = os.path.join(ROOT, "data/research_dropped.json")
def _threshold(default=70):
    """Read match_threshold from config/search.yaml so the cutoff has one source of truth."""
    try:
        for line in open(os.path.join(ROOT, "config/search.yaml")):
            m = re.match(r"\s*match_threshold\s*:\s*(\d+)", line)
            if m:
                return int(m.group(1))
    except OSError:
        pass
    return default


THRESHOLD = _threshold()

# job_id -> (score, evidence_strength, rationale, score_delta_reason|None)
S = {
"linkedin_feed:7501981475442188288": (72, "strong",
 "Mid-level UI/UX seat in Mumbai (in config) at 2-5 yrs, squarely his 4+ band; Figma/user-journey/interaction scope matches his record. Discounted for a ~6-person agency incorporated Jan 2026 where the LLM/SaaS pitch is likely client work, and a personal-Gmail application route.",
 None),

"linkedin_feed:7501984578589556736": (82, "strong",
 "Genuine in-house product design at a large consumer company in Bengaluru (in config); UX/interaction/visual/Figma/user-flow scope maps directly onto 4 years of end-to-end product work. No red flags on the record. Held below the top only because D2C solar is not the SaaS/tooling domain his measurable wins sit in, and 2-4 yrs puts him at the top of the band.",
 None),

"linkedin_feed:nynii-uiux-20260906": (58, "medium",
 "Title and Gurugram location fit config, but the 1-3 yr band is a downlevel against his 4+, the company is a ~3-person shop with no careers page and no recoverable posting, and no JD exists to verify scope. 'Immediate joiners preferred' also conflicts with a 30-day notice period.",
 None),

"linkedin_feed:hirexa-tagbin-sruiux-20260904": (62, "medium",
 "Sr. UI/UX at 3+ yrs in Gurugram fits title, seniority and location, but no JD was recoverable and Tagbin's core business is immersive/experiential installation design, so the role may be spatial rather than product UI. Routed through HireXA, a third-party recruiter whose funnel is a talent pool, not a named hiring manager.",
 None),

"linkedin_feed:7502259292465709056": (25, "thin",
 "Unattributable. No employer is named anywhere, location is null, no seniority or experience band is given, and the 'apply' link is a search-results page on an aggregator rather than a requisition. The JD text present is generic boilerplate, so there is nothing to score against and nothing stage 3 could tailor to.",
 "Prior pass scored the boilerplate JD text as if it described a real requisition; it names no employer, no location and no seniority, and the apply link is an aggregator search page, so the record supports no fit judgement at all."),

"linkedin_feed:ius-digital-uiux-20260906": (55, "medium",
 "Remote with a Delhi/NCR residence requirement and a 2+ yr bar are both workable, and he does have landing-page and campaign-visual experience. But the snippet-only scope spans UI/UX plus social creatives plus emailers plus short-form video editing at a ~9-person shop, which is a generalist marketing seat rather than product design, and video editing is outside his record. Apollo places the company in Lucknow against a Delhi/NCR requirement, unresolved.",
 None),

"linkedin_feed:7502246950474289152": (55, "strong",
 "Real JD and a clean skills list (Figma, wireframing, IA, design systems, usability testing), but the 1-3 yr band and the stated INR 30,000-50,000/month are both below a 4-year profile whose stated expectation is INR 65,000/month. IT outsourcing plus staffing means client-project churn, not product ownership, and the posting states no work mode.",
 None),

"linkedin_feed:scale-studio-freelance-20260906": (42, "thin",
 "Not a booked engagement. This is a signup to a freelance 'core network' talent pool with no rate, no engagement length and no project detail, at a studio whose only confirmable web presence is a LinkedIn page and whose contact address is a free Gmail. The application mechanic is a public comment. Freelance bench recruitment also does not match a 30-day-notice full-time search.",
 "Prior pass treated this as a design role on title alone; the evidence shows a talent-pool signup with no rate, no scope and no verifiable company website, so there is no position to score."),

"linkedin_feed:7502258840076279809": (45, "medium",
 "Misrepresented role. The title says Product Designer but the JD's deliverables are design rationale, critiques and case studies written as AI training and evaluation data, so it would not build a design portfolio. Bulk hire of 15 openings on an hourly contract with no stated length, minimum hours or guaranteed volume, funnelled through a separate talent portal. Design experience is only the entry ticket. PROBABLE DUPLICATE of linkedin_easy_apply:4460474532 (Crossing Hurdles) - same AI-data gig through a second intermediary; do not approve both.",
 "Prior pass scored the title and the design-experience prerequisite; role_reality shows the actual deliverable is written model-evaluation data, not shipped design, on unguaranteed hourly contract terms."),

"linkedin_easy_apply:4463336034": (40, "strong",
 "Hard degree gate he does not meet: the JD makes a BDes/MDes from a Tier 1 institution (NIT/NIFT/IIT) mandatory and explicitly deprioritises Tier 2, while his education is an Arena Animation graphic-design diploma and a partial GTU computer-engineering diploma. It also requires prior employment at a 'top B2C product company'. The craft brief and the Pune location are an excellent fit, but he is filtered at screening regardless; Associate grade at 1+ yrs is a further downlevel and pay mismatch, with 200+ applicants already in.",
 "Prior pass scored the craft and location fit; the mandatory Tier-1 design-degree gate and the top-B2C-employer screen are disqualifying for this candidate's actual education and employment record."),

"linkedin_easy_apply:4461124006": (80, "strong",
 "The closest domain match in the batch: SaaS dashboards, workflows and data-heavy interfaces, Figma-native, full lifecycle ownership with direct engineering partnership, at 3+ yrs and India-remote (in config). That is the same shape of work as his 4 years on WordPress product tooling and backend settings design. Discounted for an unverifiable company footprint (Apollo has no record, the site 403s) and unstated US time-zone overlap.",
 None),

"linkedin_easy_apply:4463720473": (52, "strong",
 "Seniority floor of 6-10 years of core UI/UX sits two-plus years above his 4+, so he is under-banded for the req rather than merely stretched. Compounded by a staffing-agency posting for an unnamed US client, mandatory US/UK shifts worked from India, strictly work-from-office, and agency-mediated resume handling. The work is also multi-account agency/services design, not product design.",
 "Prior pass sat this at the threshold on title match; the 6-10 year floor is a hard band mismatch and the unnamed-client agency route, night shifts and strict WFO each subtract independently."),

"linkedin_easy_apply:4450814559": (86, "strong",
 "Strongest brief in the batch alongside Corporater: genuine mid-to-senior in-house product design on AI-agent B2B SaaS at 4+ yrs, exactly his band, hybrid Bengaluru (in config). Research with operators, rapid prototyping, dashboards and configuration tooling, design-system contribution and direct engineering partnership all map onto his record, and the JD's explicit 'especially high bar' for hands-on AI use matches his AI-augmented positioning (Claude Code, ChatGPT, Gemini) directly. Held under 90 because the entity is a ~2-month-old spinout with unverifiable headcount and funding, and supply-chain/logistics domain experience is preferred and he has none.",
 None),

"linkedin_easy_apply:4462884183": (58, "strong",
 "Real JD and an India-remote role at 2+ yrs, and he does have landing-page and campaign experience. But the actual scope is the employer's own recruiting funnel and marketing sites (application flow, coding-challenge portal, cohort microsites, Squarespace, A/B testing), which is growth/marketing UX rather than product design. ~8 employees means a design team of one, and no compensation or India employment structure is stated for a US federal contractor.",
 None),

"linkedin_easy_apply:4460474532": (45, "strong",
 "Misrepresented role. Every deliverable in the JD is a written artifact (research syntheses, usability reports, UX audit write-ups, rationale documents) with no mention of shipping UI, Figma, prototypes or engineers, which is the standard shape of expert AI-training/model-evaluation work; Crossing Hurdles is an intermediary and the end client is never named. Hourly at 10-40 hrs/week with no guaranteed hours, no benefits and no contract length, and NDA'd output that cannot go in a portfolio. PROBABLE DUPLICATE of linkedin_feed:7502258840076279809 (micro1) - same underlying AI-data gig through a second intermediary; do not approve both.",
 "Prior pass sat this at the threshold on the UX title and the headline rate; role_reality shows written model-evaluation deliverables via an unnamed end client on unguaranteed hourly terms, which is not the product design work being searched for."),

"linkedin_easy_apply:4462805585": (70, "strong",
 "Marginal keep, exactly at threshold. Genuine end-to-end UX/UI (research through hi-fi UI and design system), Figma-centric, 3-7 yrs which comfortably contains his 4+, onsite Mumbai (in config), and a stated 10-13 LPA budget well above his 7.8 LPA expectation. The drags are real but not disqualifying: TalentClub is a 2-10 person recruitment consultancy and the end client is never named, work is from the client's premises with a possible agency-payroll arrangement, and the JD's stricter line asks for 'strong expertise in Insurance platforms' which he does not have.",
 None),

"linkedin_easy_apply:4462810219": (30, "strong",
 "Explicit background exclusion that matches this candidate exactly. The JD states 'Candidates primarily from SaaS, B2B, agency, or services backgrounds will not be considered' as an automatic reject filter, and his entire four-year record is SaaS/B2B product tooling at POSIMYTH. Independently, the 6+ yr senior bar is above his 4+. Also a staffing-agency posting for an unnamed Gurugram employer with no compensation stated and no confirmation it is a direct permanent hire.",
 "Prior pass scored the senior product-design brief on craft; the JD carries a hard exclusion of SaaS/B2B/agency/services backgrounds, which is precisely this candidate's record, so the skills match cannot convert."),

"indeed:d661945fa9025477": (70, "medium",
 "Marginal keep, exactly at threshold, and resting on company evidence rather than role evidence. Title and Pune location fit config and his relocation preference, and Left Right Mind is a confirmed, established design-led consultancy with a real careers page and verified inbox, so a UI/UX req there is very likely a genuine design seat. But NO job description was recovered from any source, so seniority, scope and compensation are unverified, and the consultancy model means client-services work across accounts rather than owning one product. NOTE FOR STAGE 3: full_job_description is null - tailoring must work from the title and company profile only.",
 "Prior pass scored this like a verified role; no JD exists on this record, so seniority, scope and compensation are all unverified and the score has been brought down to reflect company-level evidence only."),

"indeed:b56a37d7847496c9": (76, "medium",
 "Genuine end-to-end product UX on an internal analytics/marketplace SaaS product - research, wireframing, prototyping and Figma dev handoff - in hybrid Pune (in config), and a SaaS domain that matches his record well. Discounted because the recovered JD is for the 'Senior UX Designer' variant at 6-8 yrs rather than the plain 'UX Designer' title on this req, so the quoted bar may not apply, and the aggregator listing was already flagged as over two months old and possibly filled.",
 None),

"indeed:dbd46ce01ac8664e": (38, "medium",
 "Not a design role on the evidence available. The req title is a Genpact internal delivery-grade code ('N 4A') for a DEVELOPER on application-development platforms with UI/UX_Workflow as the skill track, and the associated skill tags found were Azure, Oracle, CSS and Visual Basic - a developer stack. No JD could be verified from any authoritative source, and banded delivery-pool reqs staff a client pool rather than a named product team. He is not a developer.",
 "Prior pass left room for this being a design seat; the title is a banded Genpact Developer requisition with UI/UX only as a skill track, and the associated stack is developer tooling, so the fit is lower than the title's 'UI/UX' substring suggests."),

"indeed:102b06ca61d54eac": (88, "strong",
 "Top of the batch. A 1,901-character first-party JD from the company's own careers page describing the full design lifecycle - Figma, design systems, usability testing, partnering with PMs and engineers on enterprise SaaS - at 3+ yrs in Bengaluru (in config). Design systems and enterprise SaaS product work are the two strongest, most-evidenced parts of his four-year record. No red flags at all on this record, which is unique in the batch. Only practical cost: no contact email exists (the Teamtailor page offers a form only), so this is portal-only.",
 None),

"indeed:95d6ae64ea3ca8ab": (84, "strong",
 "A 2,725-character first-party JD, the most detailed in the batch, and unusually well suited to this candidate specifically: the posting is explicitly portfolio-first and states it does not require formal credentials or a set number of years, which neutralises the education gate that sinks the Bajaj and Vodafone reqs. It wants funnel analytics, product ideation and a 'PM hat' alongside UX craft and explicitly rejects pure-visual candidates - and his record carries product metrics and measurable activation growth (114% and 75% active users), not just visuals. Bengaluru (in config). Discounted for a ~20-person 2024 startup where he would likely be the only designer with no design mentorship, and an explicitly 'high-velocity, no job titles' culture that is a genuine scope-creep signal.",
 None),

"indeed:a905e5a19b589281": (66, "medium",
 "Title and Bengaluru location fit, and healthcare data/AI SaaS is an adjacent domain, but the score can only rest on the title and a company profile: no job description was recovered from any source, so seniority, scope and stack are entirely unverified. Company size could not be established at all (Apollo returns 0 employees and a null industry for the domain). A reported mandatory 4-days-in-office policy and regulated-healthcare compliance work are further unconfirmed drags.",
 "Prior pass scored a SaaS product-design title as if the role were verified; there is no JD on this record and the company's size and industry could not be established, so the evidence supports only a title-level judgement."),

"indeed:8cbe54869fc82e28": (66, "medium",
 "Linde is a large, stable, independently confirmed employer with a real Bengaluru AI/Digital hub, and a software UI/UX reading of the title is plausible - but it is inference, not evidence: no JD was recoverable, so role_reality is unverified. The 'Senior' banding at a large enterprise typically implies more than four years, and industrial gases is unrelated to his product record. No contact email exists; the careers routes are portal-only.",
 None),

"indeed:5e1f4e8854226c87": (48, "strong",
 "Hard degree gate plus an unresolvable seniority band. The first-party JD hard-requires an engineering degree (MBA/Master's preferred) and his education is an Arena Animation graphic-design diploma and a PARTIAL, uncompleted GTU computer-engineering diploma, so an ATS screen on the degree field rejects him. The seniority signal is also incoherent in a way that excludes him either way: the AGM label is an Assistant General Manager managerial grade (typically 8-12 years) while the JD text states only 2-3 years - he is under-banded for the grade and over-banded for the stated years. The craft brief itself (research, personas, usability testing, Figma/Zeplin handoff for consumer and enterprise apps) is genuinely strong and Mumbai is in config, which is why this is not lower.",
 None),

"indeed:938d25f1bc48ce69": (35, "thin",
 "Company identity is unresolved. 'Sourceo' is a short, collision-prone name and the only match found is a Singapore recruiting-tech startup, not a Mumbai employer, so it cannot be confirmed who is hiring. No JD text of any kind was recoverable. If the match is correct the poster is a candidate-sourcing vendor, meaning the Mumbai req is likely placed for an undisclosed client rather than being an in-house design hire. Title and city are the only real evidence.",
 "Prior pass scored the title and city as if the employer were known; the company could not be identified at all and no JD exists, so this record supports no confident fit judgement."),

"indeed:9fda6bab6ffc05ec": (38, "strong",
 "Misrepresented role, verified from the employer's own careers page. Nominally UI/UX, but the work described is agency web/graphic design - producing 'complete PSD web pages' for developers in a Photoshop-first handoff - with no product thinking, research or design-system work anywhere in the JD, and the posting's own occupation code is '27-1024.00 Graphic designer'. Experience is explicitly 'not mandatory', making it an entry-level agency seat. The unconfirmed 22K-48K/month band would also be well under his stated expectation.",
 "Prior pass scored the UI/UX title; the first-party JD describes PSD-based graphic/web production classified under a graphic-designer occupation code at an entry-level bar, not the mid-level product design being searched for."),

"indeed:8937fb51b0a511c7": (8, "strong",
 "Definitively not a UI/UX or software design role, verified from the employer's own job board: this is 3D CGI and photorealistic rendering for Amazon listing imagery (Blender/C4D/3ds Max/KeyShot, modelling SKUs from CAD, main images and A+ Content), with zero overlap with interaction or digital product design. Compensation is stated as USD 500 per month for a full-time permanent role, and the fixed 9:00-15:00 CST core hours are roughly 19:30-01:30 IST. The hiring entity is a ~7-person hotel/real-estate firm running an unrelated Amazon side-business.",
 None),

"indeed:44b36be0804070dd": (52, "medium",
 "Title and remote work mode fit config, but the context is a caution rather than a reassurance and there is no JD to offset it. Delphic Global is an IT outsourcing and team-augmentation shop with no visible design function - every one of the nine roles visible on its Built In profile is engineering - so a 'Product Designer' here would most likely be billed out as a client-project UI designer rather than owning a product. Its own scale claims are inconsistent (201-500 self-reported against an Apollo estimate of ~83), and the name is collision-prone.",
 "Prior pass scored the title and a remote product-design opening; there is no JD, the employer is an outsourcing shop with no visible design function, and its published scale claims do not reconcile, so the confident reading is not supported."),

"indeed:79908746d3cbb389": (12, "thin",
 "Almost certainly not a software design role, and the employer is unresolved. '3D Product Designer' with no qualifiers points at physical-product CGI/visualisation - the same category as the Texas Hotel Management req in this batch, whose recovered JD turned out to be Blender/KeyShot rendering - and no evidence was found pointing the other way. No JD, no careers page and no corroborating listing on any board; the only India-based 'Bolder Technologies' is a 9-person API-integration shop with no 3D or design capability, so the posting entity cannot be confirmed.",
 None),

"wellfound:4664550": (25, "strong",
 "Hard geographic exclusion. The posting is remote only within Europe and Beirut and explicitly states no relocation is allowed and no visa sponsorship is available, so an India-based candidate is outside the stated hiring region regardless of fit. The engagement is also 'initially project-based' contract-to-hire rather than a firm full-time offer, the 1-4 yr band is junior/mid, and it expects front-end literacy and solo work alongside a single developer.",
 "Prior pass discounted for geography but still scored it as a live option; the posting's region restriction combined with an explicit no-relocation, no-sponsorship statement makes it infeasible for this candidate, not merely inconvenient."),

"wellfound:4681308": (56, "strong",
 "Compensation floor is the decisive drag. The stated 2.4L-4.8L per annum is roughly 20k-40k/month against a profile expectation of 7.8 LPA / 65k per month - between one-half and one-third of his floor - and the posting adds an explicit exclusivity clause barring any concurrent freelance or consultancy work. Role, remote-everywhere mode and the 2-4 yr requirement otherwise fit him well, and he does genuinely carry the full stated scope (product UI, design systems, brand identity, marketing graphics, user research). The posting also contradicts itself on experience, with a 1-year header against a 2-4 year requirements section, at a ~12-person services studio where portfolio work will be client-owned.",
 "Prior pass scored the role and remote fit; the stated 2.4L-4.8L band is far below the profile's own 7.8 LPA expectation and the exclusivity clause removes the usual freelance offset, so this cannot convert into a viable offer."),

"wellfound:3771670": (18, "strong",
 "Hard geographic blocker. The JD requires residing in New York or commuting to the NYC office three days a week (Tue-Thu) and the company hires remotely only within the United States, so it is not open to an India-based candidate - Wellfound's 'Remote - New York' label understates this materially. The 4-6 yr band would otherwise have been workable. The role also blends product design with pre-sales/RFP prototyping and marketing asset production, and the company serves government/defense customers, which may carry unstated clearance or citizenship expectations.",
 "Prior pass already discounted for location but kept scoring it as a stretch; a US-only hiring policy plus a 3-day NYC in-office minimum is a disqualifying constraint, not a stretch."),

"wellfound:4670266": (12, "strong",
 "Two independent hard blockers. The posting states it hires remotely in the United States only and that relocation is not allowed, so an India-based candidate is excluded outright; and the bar is 10+ years with staff/principal-level experience owning platform and permissions-model design, which is roughly two and a half times his 4+ years. Wellfound's bare 'Remote' label hides the US-only restriction stated in the JD body.",
 "Prior pass already scored it low; the combination of a US-only hiring restriction and a 10+ year staff/principal bar makes it categorically infeasible rather than a long shot."),

"wellfound:4571300": (8, "strong",
 "Disqualifying on role type and compensation. This is an unpaid volunteer student internship - the posting states no salary and explicitly no equity - with 'no experience required' and responsibilities that stop at flows, IA and usability testing under a separate UI designer, a severe seniority mismatch for a designer with four years and measurable product outcomes. The team is described as ~20-30 college students across continents, it requires the candidate to own a graphic tablet, and the Hawaii-to-Wellington time-zone spread implies meetings at unworkable hours from India.",
 "Prior pass scored it as a weak but real option; an unpaid student internship is not a position this search can convert, so it belongs near the floor."),

"wellfound:253579": (60, "strong",
 "Genuinely open to an India-based candidate (onsite or remote, worldwide) and a real UX/UI product role spanning dapp product screens and marketing websites, which is a shape he has done. It falls short on three grounds: web3/blockchain domain familiarity is preferred and is entirely absent from his record; the compensation structure puts one third of pay in PNK tokens vested over three years behind a one-year cliff with the remaining two thirds converted to crypto, so effectively all of it carries volatility risk and a third is illiquid for at least twelve months; and the very old job id relative to the rest of the batch suggests an evergreen or long-stale posting refreshed rather than newly opened. The posting also contradicts itself, tagging 'no experience required' against a scope that includes strategic core-product feature decisions.",
 None),
}


def main():
    with open(MERGED) as f:
        merged = json.load(f)

    assert len(merged) == 36, f"expected 36 merged records, got {len(merged)}"
    ids = [r["job_id"] for r in merged]
    assert len(set(ids)) == 36, "duplicate job_id in merged input"
    missing = set(ids) - set(S)
    extra = set(S) - set(ids)
    assert not missing, f"unscored job_ids: {missing}"
    assert not extra, f"invented job_ids: {extra}"

    keepers, dropped = [], []
    for rec in merged:
        score, strength, rationale, delta_reason = S[rec["job_id"]]
        out = dict(rec)  # preserve every evidence field verbatim
        out["evidence_strength"] = strength
        out["match"] = {
            "score": score,
            "rationale": rationale,
            "meets_threshold": score >= THRESHOLD,
            "evidence_strength": strength,
        }
        # dual-channel fields
        has_email = bool(rec.get("contact_email"))
        out["apply_portal"] = True
        out["cold_email"] = has_email
        out["email_source"] = rec.get("email_source") or "none"
        out["verified_mailbox"] = bool(rec.get("email_verified")) and has_email
        if delta_reason:
            out["score_delta_reason"] = delta_reason
        prior = (rec.get("prior_scores") or {}).get("retry_pass")
        out["prior_scores"] = dict(rec.get("prior_scores") or {})
        out["prior_scores"]["scoring_pass"] = score
        if prior is not None:
            out["prior_scores"]["delta_vs_retry_pass"] = score - prior

        if score >= THRESHOLD:
            keepers.append(out)
        else:
            out["drop_reason"] = rationale
            dropped.append(out)

    keepers.sort(key=lambda r: -r["match"]["score"])
    dropped.sort(key=lambda r: -r["match"]["score"])

    with open(OUT, "w") as f:
        json.dump(keepers, f, indent=2, ensure_ascii=False)
    with open(DROPPED, "w") as f:
        json.dump(dropped, f, indent=2, ensure_ascii=False)

    print(f"keepers  {len(keepers)}  -> {OUT}")
    print(f"dropped  {len(dropped)}  -> {DROPPED}")
    print(f"total    {len(keepers) + len(dropped)}")


if __name__ == "__main__":
    main()
