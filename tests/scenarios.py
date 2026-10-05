"""Realistic experiment scenarios (spec section 35). Persona dicts follow the Milestone-2 Persona schema."""


def P(pid, name, age, occ, traits, patterns, psych, goals, pains, tech, bg=""):
    return dict(id=pid, name=name, age=age, occupation=occ, background=bg or f"{name} works as {occ}.",
                personality_traits=traits, behavioral_patterns=patterns, psychological_profile=psych, goals=goals,
                pain_points=pains, tech_savviness=tech, communication_style="plain, direct", persona_summary=f"{name}, {age}, {occ}.")


SCENARIOS = {
    "food_delivery": dict(
        experiment=dict(name="Food delivery app", productDescription="A food delivery application with fast delivery and subscription plans.",
                        targetAudience="Urban adults", researchObjectives="Understand adoption barriers"),
        personas=[
            P("p1", "Aarav", 20, "College student", ["frugal", "social"], ["compares delivery fees", "uses coupons"],
              "Price-sensitive and budget conscious; avoids paying delivery fees.", ["cheap meals"], ["delivery fees"], "high"),
            P("p2", "Meera", 31, "Software engineer", ["busy", "efficient"], ["orders lunch at desk", "values convenience"],
              "Time-poor and values convenience over cost.", ["save time"], ["slow delivery"], "high"),
            P("p3", "Rohan", 38, "Parent of two, homemaker", ["caring", "careful"], ["plans weekly meals"],
              "Cautious about food quality and safety.", ["healthy food for kids"], ["food hygiene"], "medium"),
            P("p4", "Mr. Sharma", 67, "Retired bank clerk", ["traditional", "skeptical"], ["cooks at home", "distrust of apps"],
              "Skeptical of new apps; price-sensitive on fixed pension.", ["simple life"], ["confusing apps"], "low"),
        ],
        questions=[
            dict(questionId="q1", question="What do you like about this product?", type="open_ended"),
            dict(questionId="q2", question="Would you use this product regularly?", type="yes_no"),
            dict(questionId="q3", question="How much would you pay per month for a subscription?", type="numeric"),
            dict(questionId="q4", question="What would make you switch to another product?", type="open_ended"),
        ]),
    "fitness": dict(
        experiment=dict(name="Fitness app", productDescription="A personalised fitness coaching app.", targetAudience="Adults", researchObjectives="Adoption"),
        personas=[
            P("p1", "Beginner Bela", 25, "Office assistant", ["anxious"], ["skips workouts"], "Low confidence; skeptical about gyms.", ["get fit"], ["intimidation"], "medium"),
            P("p2", "Enthusiast Ekta", 28, "Personal trainer", ["driven"], ["tracks macros"], "Convenience of tracking matters; early adopter.", ["PRs"], ["plateaus"], "high"),
            P("p3", "Busy Bhavesh", 40, "Marketing manager", ["busy"], ["short workouts"], "Time-poor; wants convenience.", ["stay healthy"], ["no time"], "high"),
            P("p4", "Older Omkar", 66, "Retired teacher", ["careful"], ["daily walks"], "Skeptical of apps; distrust of data sharing.", ["mobility"], ["joint pain"], "low"),
        ],
        questions=[dict(questionId="q1", question="What do you like about this app?", type="open_ended"),
                   dict(questionId="q2", question="Would you use it?", type="yes_no"),
                   dict(questionId="q3", question="Rate how motivating this feels", type="rating")]),
    "finance": dict(
        experiment=dict(name="Robo-advisor", productDescription="An automated investing product.", targetAudience="Investors", researchObjectives="Trust"),
        personas=[
            P("p1", "Conservative Chandra", 55, "Government officer", ["risk averse"], ["fixed deposits"], "Risk averse and distrust of new fintech.", ["safety"], ["losses"], "low"),
            P("p2", "Young Yash", 24, "Junior analyst", ["curious"], ["starts SIPs"], "Convenience-seeking early adopter.", ["grow savings"], ["fees"], "high"),
            P("p3", "Freelancer Farah", 33, "Freelance designer", ["independent"], ["irregular income"], "Price-sensitive with irregular income.", ["stability"], ["cash flow"], "medium"),
            P("p4", "Experienced Eshan", 47, "Senior executive", ["analytical"], ["reads reports"], "Analytical, values convenience and control.", ["returns"], ["opaque fees"], "high"),
        ],
        questions=[dict(questionId="q1", question="Would you trust this with your money?", type="yes_no"),
                   dict(questionId="q2", question="How do you feel about the fees?", type="likert")]),
    "ecommerce": dict(
        experiment=dict(name="Marketplace", productDescription="An e-commerce marketplace.", targetAudience="Shoppers", researchObjectives="Conversion"),
        personas=[
            P("p1", "Price-hunter Priya", 29, "Sales executive", ["frugal"], ["waits for sales"], "Price-sensitive; checks every discount.", ["deals"], ["shipping cost"], "high"),
            P("p2", "Premium Pranav", 42, "Business owner", ["status-driven"], ["buys premium brands"], "Values convenience and quality over price.", ["quality"], ["fakes"], "high"),
            P("p3", "Occasional Om", 36, "School teacher", ["careful"], ["shops twice a year"], "Skeptical of unknown sellers.", ["reliability"], ["returns"], "medium"),
            P("p4", "Frequent Fiza", 22, "Student", ["social"], ["scrolls daily"], "Early adopter; convenience seeker.", ["trends"], ["delays"], "high"),
        ],
        questions=[dict(questionId="q1", question="What frustrates you about online shopping?", type="open_ended"),
                   dict(questionId="q2", question="Which matters most to you?", type="single_choice", options=["Price", "Speed", "Quality"])]),
}
