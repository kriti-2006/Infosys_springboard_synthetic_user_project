"""Ready-made sample experiment scenarios (Milestone 3 brief, section 2C).
Static metadata only -- no fabricated personas/responses. Launching a scenario creates a real
Experiment row with the product/audience/objective pre-filled; personas, surveys and responses
are still produced by the real agents when the user generates/runs them, exactly like any other
experiment. `suggested_questions` is returned so the frontend can pre-fill a survey draft.
"""

SCENARIOS = [
    {
        "slug": "ecommerce-checkout",
        "domain": "E-commerce",
        "title": "One-click checkout rollout",
        "description": "Validate whether shoppers trust and want a one-click checkout option before a storefront ships it.",
        "productDescription": "A one-click checkout feature for an online marketplace that saves payment and shipping details so "
                               "returning shoppers can complete a purchase in a single tap, without re-entering card or address info.",
        "targetAudience": "Online shoppers aged 22-55 who buy at least twice a month across a mix of mobile and desktop.",
        "researchObjectives": "Understand trust concerns around stored payment data and whether speed outweighs those concerns.",
        "suggestedQuestions": [
            {"question": "How do you usually feel about saving your card details on a shopping site?", "type": "open_ended"},
            {"question": "Would you use a one-click checkout if it were offered at your favorite store?", "type": "yes_no"},
            {"question": "How much do you trust this marketplace to keep your payment details secure?", "type": "rating", "scaleMin": 1, "scaleMax": 5},
            {"question": "What would make you hesitate to use one-click checkout?", "type": "open_ended"},
        ],
    },
    {
        "slug": "food-delivery-subscription",
        "domain": "Food delivery",
        "title": "Delivery subscription pricing",
        "description": "Test willingness to pay for a monthly subscription that waives delivery fees on a food app.",
        "productDescription": "A monthly subscription for a food delivery app that waives delivery fees and offers priority support "
                               "for a flat fee, aimed at frequent orderers.",
        "targetAudience": "Urban professionals and students who order food delivery at least once a week.",
        "researchObjectives": "Find the price point where delivery-fee savings justify a subscription, and the biggest adoption barrier.",
        "suggestedQuestions": [
            {"question": "How often do you currently order food delivery in a typical month?", "type": "open_ended"},
            {"question": "Would a monthly subscription that waives delivery fees be worth it for you?", "type": "yes_no"},
            {"question": "Which price feels fair for unlimited free delivery each month?", "type": "single_choice",
             "options": ["$4.99", "$9.99", "$14.99", "$19.99"]},
            {"question": "How satisfied are you with delivery fees today?", "type": "rating", "scaleMin": 1, "scaleMax": 5},
        ],
    },
    {
        "slug": "fitness-habit-coach",
        "domain": "Fitness",
        "title": "AI habit-coaching feature",
        "description": "Explore whether gym-goers want an AI coach that nudges them back after missed workouts.",
        "productDescription": "An AI coaching feature inside a fitness app that notices missed workouts and sends a personalised, "
                               "non-judgmental nudge with a smaller 'easy win' workout to help users restart their habit.",
        "targetAudience": "Fitness app users aged 20-45 who have tried and abandoned workout routines before.",
        "researchObjectives": "Understand whether this reduces the shame/avoidance loop that causes people to quit after missing a workout.",
        "suggestedQuestions": [
            {"question": "What usually happens after you miss a workout you had planned?", "type": "open_ended"},
            {"question": "Would you want an app to notice and nudge you after a missed workout?", "type": "yes_no"},
            {"question": "How motivating vs. guilt-inducing do reminder notifications usually feel to you?", "type": "open_ended"},
            {"question": "How likely are you to restart a routine after missing 3+ days?", "type": "rating", "scaleMin": 1, "scaleMax": 5},
        ],
    },
    {
        "slug": "edtech-placement-prep",
        "domain": "Education",
        "title": "Campus placement-prep AI",
        "description": "Gauge student interest in an AI mock-interview tool ahead of campus placements.",
        "productDescription": "An AI-powered mock interview platform for final-year college students preparing for campus placements, "
                               "offering company-specific interview styles and structured feedback on communication and technical answers.",
        "targetAudience": "Final-year engineering and commerce students at tier-2/tier-3 colleges preparing for campus placements.",
        "researchObjectives": "Validate demand versus free alternatives (friends, YouTube) and identify the most valuable feedback type.",
        "suggestedQuestions": [
            {"question": "How are you currently preparing for placement interviews?", "type": "open_ended"},
            {"question": "Would you pay for an AI mock interview tool with company-specific practice?", "type": "yes_no"},
            {"question": "Which feedback would help you most?", "type": "single_choice",
             "options": ["Communication style", "Technical accuracy", "Confidence/body language cues", "Structured answer format"]},
            {"question": "How anxious do you feel about upcoming placement interviews?", "type": "rating", "scaleMin": 1, "scaleMax": 5},
        ],
    },
    {
        "slug": "productivity-focus-app",
        "domain": "Productivity",
        "title": "Deep-work focus timer",
        "description": "Test a focus-timer app that blocks distracting apps during scheduled deep-work blocks.",
        "productDescription": "A productivity app that blocks distracting apps and notifications during scheduled deep-work blocks, "
                               "then shows a weekly report of focused time versus interruptions.",
        "targetAudience": "Remote and hybrid knowledge workers aged 24-45 who struggle with app-switching during focused work.",
        "researchObjectives": "Understand whether blocking (vs. just tracking) distractions is something people will actually tolerate.",
        "suggestedQuestions": [
            {"question": "What usually breaks your focus during a work session?", "type": "open_ended"},
            {"question": "Would you let an app block distracting apps during work hours?", "type": "yes_no"},
            {"question": "How useful would a weekly focus-vs-interruption report be?", "type": "rating", "scaleMin": 1, "scaleMax": 5},
            {"question": "What would make you turn the blocking feature off?", "type": "open_ended"},
        ],
    },
]

_BY_SLUG = {s["slug"]: s for s in SCENARIOS}


def list_scenarios() -> list[dict]:
    return SCENARIOS


def get_scenario(slug: str) -> dict | None:
    return _BY_SLUG.get(slug)
