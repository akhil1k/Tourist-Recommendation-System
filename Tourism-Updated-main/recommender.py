import os
from groq import Groq

# Get Groq API Key from .env file
def init_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("⚠️ Warning: GROQ_API_KEY not found. AI recommendations will fail.")
        return None
    return Groq(api_key=api_key)

client = init_groq_client()

# Call API
def get_recommendations(destination, city, country):

    if not client:
        return ["Error: AI services are unconfigured. Please configure your GROQ_API_KEY in the .env file."]

    prompt = f"""You are a knowledgeable local travel guide. List the top 10 must-visit tourist attractions strictly located within a 0 to 15 kilometer radius of "{destination}" in {city}, {country}. Do NOT include places that are far away from this specific location.

For each attraction, provide:
• The name of the attraction
• A 4-5 line engaging summary describing why it is worth visiting, briefly mentioning approximately how far it is from {destination}.

Format your response as a simple bullet-point list. Each item should start with the attraction name 
followed by a colon, then the summary. Do not use numbering, use bullet points (•) only.
Do not include any introduction or closing text, just the bullet points."""

    try:
        print(f"\n🔍 Searching recommendations for: {destination}, {city}, {country}")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )

        result_text = response.choices[0].message.content
        if result_text:
            lines = result_text.strip().split("\n")
            recommendations = [line.strip() for line in lines if line.strip()]
            print(f"✅ Successfully got {len(recommendations)} recommendations")
            return recommendations
        else:
            print("⚠️ Groq returned an empty response")
            return ["No recommendations could be generated. Please try again."]

    except Exception as e:
        print(f"\n❌ ERROR in get_recommendations:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        return [f"Error getting recommendations: {str(e)}"]
