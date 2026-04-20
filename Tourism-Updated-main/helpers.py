import urllib.request
import urllib.parse
import json
import time
import os

# ---------------------------------------------------------
# Directories for persistent disk cache
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_CACHE_DIR = os.path.join(BASE_DIR, 'static', 'cached_images')
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

weather_cache = {}
summary_cache = {}

# ---------------------------------------------------------
# Weather (in-memory cache, 1hr TTL — changes frequently)
# ---------------------------------------------------------
def get_weather(city):
    if city in weather_cache:
        cached_time, weather_str = weather_cache[city]
        if time.time() - cached_time < 3600:
            return weather_str

    # Append ", Uttarakhand" to help wttr.in resolve Indian cities correctly
    search_city = urllib.parse.quote(f"{city}, Uttarakhand, India")

    try:
        # Primary: JSON format for structured data
        url = f"https://wttr.in/{search_city}?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'TourismApp/1.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())
            temp = data['current_condition'][0]['temp_C']
            desc = data['current_condition'][0]['weatherDesc'][0]['value']
            print(f"Weather for {city}: {temp}°C, {desc}")
            weather_str = f"{temp}°C, {desc}"
            weather_cache[city] = (time.time(), weather_str)
            return weather_str
    except Exception:
        pass

    try:
        # Fallback: simple text format (more lenient)
        url = f"https://wttr.in/{search_city}?format=3"
        req = urllib.request.Request(url, headers={'User-Agent': 'TourismApp/1.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            weather_str = response.read().decode().strip().split(":")[-1].strip()
            weather_cache[city] = (time.time(), weather_str)
            return weather_str
    except Exception:
        return "Weather unavailable"

# ---------------------------------------------------------
# Images (persistent disk cache — downloaded once, served
# from /static/cached_images/ forever)
# ---------------------------------------------------------

# Hard-coded overrides for places where Wikipedia search
# returns a disambiguation page or wrong result
IMAGE_OVERRIDES = {
    "Auli": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Auli_Himalayas.jpg/960px-Auli_Himalayas.jpg",
}

def _safe_filename(name):
    """Convert a place name to a safe filename."""
    return "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in name).strip().replace(' ', '_') + ".jpg"

def get_image(name):
    # 1. Check disk cache first (fastest — local static file)
    filename = _safe_filename(name)
    local_path = os.path.join(IMAGE_CACHE_DIR, filename)
    static_url = f"/static/cached_images/{filename}"

    if os.path.exists(local_path):
        return static_url

    # 2. Use manual override URL if defined
    remote_url = IMAGE_OVERRIDES.get(name)

    # 3. Otherwise query Wikipedia API for the image URL
    if not remote_url:
        try:
            query = urllib.parse.quote(name)
            api_url = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={query}&gsrlimit=1&prop=pageimages&pithumbsize=600&format=json"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'TourismApp/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            pages = data.get("query", {}).get("pages", {})
            if pages:
                first = list(pages.values())[0]
                remote_url = first.get("thumbnail", {}).get("source")
        except Exception:
            pass

    # 4. Download and save to disk
    if remote_url:
        try:
            req = urllib.request.Request(remote_url, headers={'User-Agent': 'TourismApp/1.0'})
            with urllib.request.urlopen(req, timeout=5) as img_response:
                with open(local_path, 'wb') as f:
                    f.write(img_response.read())
            return static_url
        except Exception:
            pass

    # 5. Ultimate fallback — return Unsplash URL without caching
    return "https://images.unsplash.com/photo-1488646953014-c8ce956b5c14?w=600&q=80"

# ---------------------------------------------------------
# Wikipedia summary (in-memory cache per session)
# ---------------------------------------------------------
def get_wikipedia_summary(name):
    if name in summary_cache:
        return summary_cache[name]
    try:
        query = urllib.parse.quote(name)
        url = f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro=&explaintext=&titles={query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'TourismApp/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            pages = data['query']['pages']
            extract = list(pages.values())[0].get('extract', 'Description not found.')
            summary_cache[name] = extract
            return extract
    except Exception:
        return "Description unavailable."

# ---------------------------------------------------------
# Related places (static mapping)
# ---------------------------------------------------------
def get_related_places(place):
    mapping = {
        "Rishikesh": ["Haridwar", "Mussoorie"],
        "Haridwar": ["Rishikesh", "Dehradun"],
        "Mussoorie": ["Dehradun", "Dhanaulti"],
        "Nainital": ["Bhimtal", "Almora"],
        "Auli": ["Joshimath", "Badrinath"],
        "Jim Corbett National Park": ["Nainital", "Ranikhet"],
        "Valley of Flowers": ["Hemkund Sahib", "Joshimath"],
        "Char Dham": ["Kedarnath", "Badrinath", "Gangotri", "Yamunotri"]
    }
    return mapping.get(place, ["Rishikesh", "Nainital"])

# ---------------------------------------------------------
# Static data
# ---------------------------------------------------------
popular_places = [
    {"name": "Rishikesh", "category": "Spiritual"},
    {"name": "Haridwar", "category": "Religious"},
    {"name": "Mussoorie", "category": "Hill Station"},
    {"name": "Nainital", "category": "Lake"},
    {"name": "Auli", "category": "Snow"},
    {"name": "Jim Corbett National Park", "category": "Wildlife"},
    {"name": "Valley of Flowers", "category": "Nature"},
    {"name": "Char Dham", "category": "Pilgrimage"}
]

best_time = {
    "Rishikesh": "September – April",
    "Haridwar": "October – March",
    "Mussoorie": "March – June",
    "Nainital": "March – June",
    "Auli": "December – February ❄️",
    "Jim Corbett National Park": "November – June",
    "Valley of Flowers": "July – September 🌸",
    "Char Dham": "May – October"
}

# ---------------------------------------------------------
# Multiple images for gallery (in-memory cache)
# ---------------------------------------------------------
gallery_cache = {}

def get_place_images(name, count=6):
    """Fetch multiple images for a place from Wikipedia in one API call."""
    if name in gallery_cache:
        return gallery_cache[name]

    images = []
    try:
        query = urllib.parse.quote(name)
        api_url = (
            f"https://en.wikipedia.org/w/api.php?action=query"
            f"&titles={query}&generator=images&gimlimit=20"
            f"&prop=imageinfo&iiprop=url&iiurlwidth=800&format=json"
        )
        req = urllib.request.Request(api_url, headers={'User-Agent': 'TourismApp/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        pages = data.get("query", {}).get("pages", {})

        skip_patterns = [
            'icon', 'logo', 'flag', 'commons-logo', 'symbol', 'seal',
            'coat', 'button', '.svg', 'wiki', 'edit', 'question',
            'padlock', 'lock', 'disambig', 'stub', 'crystal', 'folder',
            'red pencil', 'increase', 'decrease', 'ambox', 'no image',
            'placeholder', 'arrow', 'india_location', 'locator',
            'blank', 'transparent', 'caret', 'sort', 'gnome',
            'office-book', 'blue_pencil', 'wiktionary', 'wikiquote',
        ]

        for page in pages.values():
            title = page.get("title", "")
            if any(skip in title.lower() for skip in skip_patterns):
                continue
            if not any(ext in title.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                continue

            img_info = page.get("imageinfo", [{}])[0]
            thumb_url = img_info.get("thumburl") or img_info.get("url")
            if thumb_url and thumb_url not in images:
                images.append(thumb_url)
                if len(images) >= count:
                    break
    except Exception:
        pass

    # Always include the primary cached image at the front
    primary = get_image(name)
    if primary not in images:
        images.insert(0, primary)
    elif images.index(primary) != 0:
        images.remove(primary)
        images.insert(0, primary)

    images = images[:count]

    if images:
        gallery_cache[name] = images

    return images if images else [get_image(name)]


# ---------------------------------------------------------
# Place coordinates for accurate map pins
# ---------------------------------------------------------
place_coordinates = {
    "Rishikesh": [30.0869, 78.2676],
    "Haridwar": [29.9457, 78.1642],
    "Mussoorie": [30.4598, 78.0644],
    "Nainital": [29.3919, 79.4542],
    "Auli": [30.5280, 79.5671],
    "Jim Corbett National Park": [29.5300, 78.7747],
    "Valley of Flowers": [30.7280, 79.6050],
    "Char Dham": [30.7346, 79.0669],
    "Dehradun": [30.3165, 78.0322],
    "Dhanaulti": [30.4320, 78.2570],
    "Bhimtal": [29.3469, 79.5578],
    "Almora": [29.5971, 79.6591],
    "Joshimath": [30.5550, 79.5640],
    "Badrinath": [30.7447, 79.4930],
    "Ranikhet": [29.6439, 79.4332],
    "Hemkund Sahib": [30.6920, 79.6060],
    "Kedarnath": [30.7352, 79.0669],
    "Gangotri": [30.9944, 78.9400],
    "Yamunotri": [31.0117, 78.4583],
}


# ---------------------------------------------------------
# Things to do (curated)
# ---------------------------------------------------------
place_activities = {
    "Rishikesh": [
        {"icon": "🏄", "title": "White Water Rafting", "desc": "Experience thrilling rapids on the Ganges River, from Grade I to Grade IV."},
        {"icon": "🧘", "title": "Yoga & Meditation", "desc": "Join ashrams and yoga centres — the world capital of yoga."},
        {"icon": "🌉", "title": "Visit Laxman Jhula", "desc": "Walk across the iconic 137m suspension bridge over the Ganges."},
        {"icon": "🪂", "title": "Bungee Jumping", "desc": "Take a 83m leap at India's highest bungee jumping platform."},
        {"icon": "🏕️", "title": "Camping by the Ganges", "desc": "Spend a night under the stars at riverside beach camps."},
        {"icon": "🌅", "title": "Ganga Aarti at Triveni Ghat", "desc": "Witness the mesmerising evening prayer ceremony on the riverbank."},
    ],
    "Haridwar": [
        {"icon": "🪔", "title": "Ganga Aarti at Har Ki Pauri", "desc": "Witness the grand evening aarti — a spiritual spectacle of fire and chants."},
        {"icon": "🛕", "title": "Visit Chandi Devi Temple", "desc": "Take a cable car ride to this hilltop temple with panoramic views."},
        {"icon": "🏊", "title": "Holy Dip in Ganges", "desc": "Take a sacred bath at the ancient Brahmakund ghats."},
        {"icon": "🧘", "title": "Shantikunj Ashram", "desc": "Explore the spiritual practices at this renowned ashram."},
        {"icon": "🌳", "title": "Rajaji National Park", "desc": "Spot elephants and tigers in this nearby wildlife sanctuary."},
        {"icon": "🛍️", "title": "Moti Bazaar", "desc": "Shop for religious artefacts, bangles, and Ayurvedic products."},
    ],
    "Mussoorie": [
        {"icon": "🌄", "title": "Gun Hill Point", "desc": "Ride the ropeway to the second-highest peak for Himalayan panoramas."},
        {"icon": "🛍️", "title": "Mall Road Walk", "desc": "Stroll the vibrant stretch with shops, cafes, and colonial charm."},
        {"icon": "💧", "title": "Kempty Falls", "desc": "Swim at this famous 40ft waterfall, just 15km from town."},
        {"icon": "🌸", "title": "Company Garden", "desc": "Enjoy colourful flower beds, fountains, and a mini lake."},
        {"icon": "🏔️", "title": "Lal Tibba", "desc": "See the highest point in Mussoorie with stunning sunrise views."},
        {"icon": "🏛️", "title": "George Everest House", "desc": "Explore the ruins of the Surveyor General's home with valley views."},
    ],
    "Nainital": [
        {"icon": "🚣", "title": "Boating on Naini Lake", "desc": "Paddle across the emerald lake surrounded by seven hills."},
        {"icon": "🔭", "title": "Snow View Point", "desc": "Cable car ride to see the snowy Himalayan range including Nanda Devi."},
        {"icon": "🌳", "title": "Eco Cave Gardens", "desc": "Explore interconnected rocky caves named after animals."},
        {"icon": "🛍️", "title": "Tibetan Market", "desc": "Browse handicrafts, woollen clothes, and candles on Mall Road."},
        {"icon": "🐎", "title": "Tiffin Top Trek", "desc": "A scenic horse ride or trek to Dorothy's Seat for panoramic views."},
        {"icon": "🏛️", "title": "Naina Devi Temple", "desc": "Visit this sacred temple right at the northern shore of the lake."},
    ],
    "Auli": [
        {"icon": "⛷️", "title": "Skiing", "desc": "Glide down Asia's longest ski slope at 2,500–3,000m altitude."},
        {"icon": "🚠", "title": "Asia's Longest Gondola Ride", "desc": "A breathtaking 4km cable car from Joshimath to Auli."},
        {"icon": "🏔️", "title": "Gorson Bugyal Trek", "desc": "Trek through vast alpine meadows with Nanda Devi views."},
        {"icon": "🏕️", "title": "Camping in Meadows", "desc": "Camp in snow-covered meadows surrounded by oak and conifer forests."},
        {"icon": "📸", "title": "Sunrise at Auli", "desc": "Watch golden light hit Nanda Devi, Kamet, and Mana peaks."},
        {"icon": "🛕", "title": "Joshimath Visit", "desc": "Explore the ancient town and Shankaracharya's math nearby."},
    ],
    "Jim Corbett National Park": [
        {"icon": "🐅", "title": "Tiger Safari", "desc": "Spot Royal Bengal Tigers in their natural habitat on a jeep safari."},
        {"icon": "🐘", "title": "Elephant Safari", "desc": "Ride atop elephants through dense sal forests for wildlife viewing."},
        {"icon": "🐦", "title": "Bird Watching", "desc": "Spot over 600 bird species including the Great Hornbill."},
        {"icon": "🌊", "title": "Kosi River Rafting", "desc": "Enjoy gentle rapids perfect for beginners and families."},
        {"icon": "🏡", "title": "Corbett Museum", "desc": "Visit Jim Corbett's residence now preserved as a museum."},
        {"icon": "🌅", "title": "Sitabani Forest", "desc": "A buffer zone perfect for nature walks and photography."},
    ],
    "Valley of Flowers": [
        {"icon": "🌺", "title": "Valley Trek", "desc": "Walk through 87+ sq km of alpine meadows with 600+ flower species."},
        {"icon": "🏔️", "title": "Hemkund Sahib Trek", "desc": "Continue the trail to this glacial lake Sikh shrine at 4,632m."},
        {"icon": "📸", "title": "Wildlife Photography", "desc": "Spot rare Himalayan fauna including blue sheep and musk deer."},
        {"icon": "🦋", "title": "Butterfly Diversity", "desc": "Witness hundreds of butterfly species in this UNESCO World Heritage Site."},
        {"icon": "⛺", "title": "Ghangaria Base Camp", "desc": "Stay at this charming village, the gateway to the valley."},
        {"icon": "❄️", "title": "Glacial Streams", "desc": "Walk beside crystal-clear streams fed by ancient glaciers."},
    ],
    "Char Dham": [
        {"icon": "🛕", "title": "Kedarnath Temple", "desc": "Trek to one of the 12 Jyotirlingas at 3,583m altitude."},
        {"icon": "🛕", "title": "Badrinath Temple", "desc": "Visit the sacred Vishnu temple nestled between Nar and Narayana ranges."},
        {"icon": "🏔️", "title": "Gangotri Glacier", "desc": "Visit the origin of the Ganges at the Gaumukh glacier."},
        {"icon": "🌊", "title": "Yamunotri Hot Springs", "desc": "Bathe in the sacred Surya Kund near the Yamuna's source."},
        {"icon": "🚁", "title": "Helicopter Yatra", "desc": "Complete the pilgrimage with a scenic helicopter tour."},
        {"icon": "🏕️", "title": "Chopta-Tungnath Trek", "desc": "Visit the world's highest Shiva temple en route to Chandrashila."},
    ],
}


# ---------------------------------------------------------
# How to reach (curated)
# ---------------------------------------------------------
place_how_to_reach = {
    "Rishikesh": {
        "air": "Jolly Grant Airport, Dehradun (35 km away). Regular flights from Delhi, Mumbai.",
        "rail": "Rishikesh Railway Station or Haridwar Junction (25 km). Connected to major cities.",
        "road": "Well-connected via NH58. ~230 km from Delhi (5-6 hour drive).",
    },
    "Haridwar": {
        "air": "Jolly Grant Airport, Dehradun (54 km). Taxi available.",
        "rail": "Haridwar Junction — major station with direct trains from Delhi, Mumbai, Kolkata.",
        "road": "NH58 from Delhi (~200 km, 4-5 hours).",
    },
    "Mussoorie": {
        "air": "Jolly Grant Airport, Dehradun (60 km).",
        "rail": "Dehradun Railway Station (34 km). Shared taxis and buses available.",
        "road": "~290 km from Delhi via Dehradun. Scenic hill road drive.",
    },
    "Nainital": {
        "air": "Pantnagar Airport (65 km). Flights from Delhi.",
        "rail": "Kathgodam Railway Station (34 km) — the nearest railhead.",
        "road": "~320 km from Delhi (7-8 hours). Well-maintained highway.",
    },
    "Auli": {
        "air": "Jolly Grant Airport, Dehradun (279 km). Taxi to Joshimath.",
        "rail": "Rishikesh Railway Station (253 km), then road to Joshimath.",
        "road": "Drive to Joshimath (~12 hrs from Delhi), then cable car to Auli.",
    },
    "Jim Corbett National Park": {
        "air": "Pantnagar Airport (80 km).",
        "rail": "Ramnagar Railway Station (12 km from Dhikala gate).",
        "road": "~260 km from Delhi via Moradabad-Kashipur route.",
    },
    "Valley of Flowers": {
        "air": "Jolly Grant Airport, Dehradun (295 km to Govindghat).",
        "rail": "Rishikesh (273 km). Then bus/taxi to Govindghat.",
        "road": "Drive to Govindghat, then 13 km trek via Ghangaria.",
    },
    "Char Dham": {
        "air": "Jolly Grant Airport, Dehradun. Helicopter services available.",
        "rail": "Rishikesh or Haridwar — gateways to the Char Dham circuit.",
        "road": "Well-connected from Haridwar/Rishikesh. Full circuit ~1,600 km.",
    },
}


# ---------------------------------------------------------
# Key facts (curated)
# ---------------------------------------------------------
place_facts = {
    "Rishikesh":                {"elevation": "372 m",        "district": "Dehradun", "known_as": "Yoga Capital of the World",  "ideal_duration": "2–3 Days", "category": "Spiritual"},
    "Haridwar":                 {"elevation": "314 m",        "district": "Haridwar", "known_as": "Gateway to the Gods",        "ideal_duration": "1–2 Days", "category": "Religious"},
    "Mussoorie":                {"elevation": "2,005 m",      "district": "Dehradun", "known_as": "Queen of the Hills",         "ideal_duration": "2–3 Days", "category": "Hill Station"},
    "Nainital":                 {"elevation": "1,938 m",      "district": "Nainital", "known_as": "Lake District of India",      "ideal_duration": "2–3 Days", "category": "Lake"},
    "Auli":                     {"elevation": "2,800 m",      "district": "Chamoli",  "known_as": "Skiing Capital of India",     "ideal_duration": "2–3 Days", "category": "Snow"},
    "Jim Corbett National Park":{"elevation": "385–1,100 m",  "district": "Nainital", "known_as": "India's First National Park", "ideal_duration": "2–3 Days", "category": "Wildlife"},
    "Valley of Flowers":        {"elevation": "3,658 m",      "district": "Chamoli",  "known_as": "UNESCO World Heritage Site",  "ideal_duration": "3–4 Days", "category": "Nature"},
    "Char Dham":                {"elevation": "3,100–3,600 m","district": "Multiple", "known_as": "Sacred Pilgrimage Circuit",   "ideal_duration": "10–12 Days","category": "Pilgrimage"},
}
