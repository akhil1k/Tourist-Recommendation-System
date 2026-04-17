import os
import requests
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
def get_recommendations(destination, city, country, category="All"):

    if not client:
        return ["Error: AI services are unconfigured. Please configure your GROQ_API_KEY in the .env file."]

    category_instruction = ""
    if category and category != "All":
        category_instruction = f" Focus strictly on ONLY {category} attractions. Do not include places outside this category."

    prompt = f"""You are a knowledgeable local travel guide. List the top 10 must-visit tourist attractions located within a 0 to 15 kilometer radius of "{destination}" in {city}, {country}.{category_instruction} Do NOT include places that are far away from this specific location.

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
            max_tokens=2048
        )

        result_text = response.choices[0].message.content
        if result_text:
            lines = result_text.strip().split("\n")
            recommendations = []
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # Remove starting bullet if present
                if line.startswith('•'): line = line[1:].strip()
                elif line.startswith('-'): line = line[1:].strip()
                elif line.startswith('*'): line = line[1:].strip()
                
                image_url = None
                place_name = None
                if ':' in line:
                    place_name = line.split(':', 1)[0].replace('*', '').strip()
                
                recommendations.append({"text": line, "image": None, "place_name": place_name})
                
            print(f"✅ Successfully got {len(recommendations)} recommendations securely")
            return recommendations
        else:
            print("⚠️ Groq returned an empty response")
            return [{"text": "No recommendations could be generated. Please try again.", "image": None, "place_name": None}]

    except Exception as e:
        print(f"\n❌ ERROR in get_recommendations:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        return [f"Error getting recommendations: {str(e)}"]
