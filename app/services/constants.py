AIRPORTS = {
    "RUH": "King Khalid International Airport, Riyadh, Saudi Arabia",
    "JED": "King Abdulaziz International Airport, Jeddah, Saudi Arabia",
    "DMM": "King Fahd International Airport, Dammam, Saudi Arabia",
    "MED": "Prince Mohammad bin Abdulaziz International Airport, Medina, Saudi Arabia",
    "TIF": "Taif Regional Airport, Taif, Saudi Arabia",
    "AHB": "Abha International Airport, Abha, Saudi Arabia",
    "ELQ": "Prince Nayef bin Abdulaziz Regional Airport, Buraidah, Saudi Arabia",
    "YNB": "Yanbu Airport, Yanbu, Saudi Arabia",
    "HAS": "Ha'il Regional Airport, Ha'il, Saudi Arabia",
    "EAM": "Najran Domestic Airport, Najran, Saudi Arabia",
    "AQI": "Al Qaisumah/Hafr Al Batin Airport, Hafr Al Batin, Saudi Arabia",
    "GIZ": "Jizan Regional Airport, Jizan, Saudi Arabia",
    "ULH": "Prince Abdul Majeed bin Abdulaziz Domestic Airport, Al-Ula, Saudi Arabia",
    "URY": "Guriat Domestic Airport, Gurayat, Saudi Arabia",
    "TUU": "Tabuk Regional Airport, Tabuk, Saudi Arabia",
    "WAE": "Wadi Al Dawasir Domestic Airport, Wadi ad-Dawasir, Saudi Arabia",
    "RAE": "Arar Domestic Airport, Arar, Saudi Arabia",
    "DWD": "Dawadmi Domestic Airport, Dawadmi, Saudi Arabia",
}



LAYOVER_PROMPT = """
Create a concise, structured layover plan JSON for the following traveler.
Keep 3-6 recommended_stops, realistic durations, and simple costs.
f"Context:
{json.dumps(context, ensure_ascii=False, indent=2)}
Output ONLY JSON.
"""

LAYOVER_JSON_PROMPT_TMPL = """\
You are a layover planner. Using the context below, produce a JSON layover plan that
matches the provided JSON Schema. If data is unknown, pick sensible placeholders
that still validate the schema. Output ONLY JSON.

CONTEXT:
{context}
"""

