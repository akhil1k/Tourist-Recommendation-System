# Future Upgrades: Images and Google Maps Links

This file contains the code required to inject real images (using the free Wikipedia API) and clickable Google Maps directions into the tourist recommendation system. 

When you are ready to upgrade the application, follow the steps below to integrate the code!

## Step 1: Update `app.py`
Add the standard URL parsing libraries and the Wikipedia helper function to the **top** of your `app.py` file:

```python
import urllib.request
import urllib.parse
import json

def get_wikipedia_image(place_name, city):
    """Fetches a thumbnail image from Wikipedia for a given place."""
    try:
        query = f"{place_name} {city}"
        url = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&gsrlimit=1&prop=pageimages&piprop=thumbnail&pithumbsize=400&format=json"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'TourismApp/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        if "query" in data and "pages" in data["query"]:
            pages = data["query"]["pages"]
            first_page_id = list(pages.keys())[0]
            if "thumbnail" in pages[first_page_id]:
                return pages[first_page_id]["thumbnail"]["source"]
        
        # Fallback scenic image if no Wikipedia image is found
        return "https://images.unsplash.com/photo-1488646953014-c8ce956b5c14?w=400&q=80"
    except Exception as e:
        print(f"Error fetching image: {e}")
        return "https://images.unsplash.com/photo-1488646953014-c8ce956b5c14?w=400&q=80"
```

## Step 2: Update the `get_recommendations()` function
Scroll down to your `get_recommendations` function and modify the loop where it splits the response text. It will convert the raw strings into "dictionaries" containing the name, description, image URL, and maps URL:

```python
        result_text = response.choices[0].message.content
        if result_text:
            lines = result_text.strip().split("\n")
            parsed_recommendations = []
            
            for line in lines:
                clean_line = line.strip()
                if not clean_line: continue
                
                if ':' in clean_line:
                    parts = clean_line.split(':', 1)
                    name = parts[0].replace('•', '').replace('*', '').strip()
                    desc = parts[1].strip()
                    img_url = get_wikipedia_image(name, city)
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name + ' ' + city)}"
                    
                    parsed_recommendations.append({
                        "name": name,
                        "description": desc,
                        "image_url": img_url,
                        "maps_url": maps_url
                    })
                else:
                    name = clean_line.replace('•', '').replace('*', '').strip()
                    if name:
                        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name + ' ' + city)}"
                        parsed_recommendations.append({
                            "name": name,
                            "description": "",
                            "image_url": "https://images.unsplash.com/photo-1488646953014-c8ce956b5c14?w=400&q=80",
                            "maps_url": maps_url
                        })

            print(f"✅ Successfully got {len(parsed_recommendations)} recommendations")
            return parsed_recommendations
```

## Step 3: Update `recommend.html`
Replace your current `<ul>` loop in the frontend template (`templates/recommend.html`) with this beautifully styled flexbox layout. It checks if the item is a dictionary (`mapping`) and gracefully renders the image, the bold title, the description, and a stylish Google Maps button.

```html
      {% if recommendations %}
      <div class="output-section">
        <h3>Recommended Places:</h3>
        <ul style="list-style-type: none; padding-left: 0; display: flex; flex-direction: column; gap: 20px;">
          {% for place in recommendations %}
             {% if place is mapping %}
                <li style="background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; gap: 20px; align-items: flex-start;">
                   <img src="{{ place.image_url }}" alt="{{ place.name }}" style="width: 140px; height: 100px; object-fit: cover; border-radius: 6px; flex-shrink: 0;" onerror="this.src='https://images.unsplash.com/photo-1488646953014-c8ce956b5c14?w=400&q=80'">
                   <div>
                      <strong style="font-size: 1.25rem; color: #1e82db; display: block; margin-bottom: 5px;">{{ place.name }}</strong>
                      {% if place.description %}
                         <p style="margin: 0 0 12px 0; color: #555; line-height: 1.5;">{{ place.description }}</p>
                      {% endif %}
                      <a href="{{ place.maps_url }}" target="_blank" style="display: inline-flex; align-items: center; gap: 5px; background: #e8f3fc; color: #1e82db; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 0.9rem; font-weight: 500; border: 1px solid #cce5ff;">
                         📍 View on Google Maps
                      </a>
                   </div>
                </li>
             {% else %}
                <li style="background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 12px;">{{ place }}</li>
             {% endif %}
          {% endfor %}
        </ul>
      </div>
      {% endif %}
```

***

# Future Upgrade: Live Weather Forecast

It is incredibly useful to show the live temperature and weather conditions of the inputted city. You can do this completely for **free using the `wttr.in` API (no API keys required!)**.

## Step 1: Add the Weather Helper in `app.py`
Add this short function near the top of your `app.py` script. It fetches the live weather conditions for the specified city.

```python
def get_weather(city):
    """Fetches real-time weather data for the city using wttr.in (Free API)."""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'TourismApp/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            temp = data['current_condition'][0]['temp_C']
            desc = data['current_condition'][0]['weatherDesc'][0]['value']
            return {"temp": f"{temp}°C", "desc": desc}
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None
```

## Step 2: Update the `/recommend` route in `app.py`
Scroll down to your `@app.route('/recommend')` block and modify the POST logic to fetch the weather and pass it into the HTML template alongside the recommendations:

```python
        # Get live weather info
        weather_info = get_weather(city)
        # Get actual recommendations
        recommendations = get_recommendations(destination, city, country)
        
    # Pass the weather_info and the capitalized city name to the frontend
    return render_template('recommend.html', 
                            recommendations=recommendations, 
                            weather=weather_info, 
                            city=city.title() if request.method == 'POST' else "")
```

## Step 3: Display Weather in `recommend.html`
Open your `templates/recommend.html` file. Place this beautiful weather widget snippet right above the `{% if recommendations %}` block. It dynamically appears only if weather data is successfully fetched.

```html
      {% if weather %}
      <div style="background: linear-gradient(135deg, #1e82db, #6ec1e4); color: white; padding: 15px 25px; border-radius: 8px; margin-bottom: 25px; display: inline-flex; align-items: center; gap: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
        <div style="font-size: 2.5rem;">⛅</div>
        <div>
           <p style="margin: 0; font-size: 0.9rem; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Current Weather in {{ city }}</p>
           <h4 style="margin: 4px 0 0 0; font-size: 1.5rem; font-weight: 600;">{{ weather.temp }} — {{ weather.desc }}</h4>
        </div>
      </div>
      {% endif %}
```

Future updates : add night mode in website
create a user profile and his wishlist or bucket list to save the places he wants to visit

add different categories, for tourist places like natural, historical, religious, etc.
