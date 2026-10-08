import os
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "adk-workshop-sosta-app-dev")
DATABASE_ID = os.getenv("FIRESTORE_FOOD_KB_DB", "adk-agent-dev-food-kb-fs")
COLLECTION_NAME = "stop_food_kb"

print(f"Connecting to Firestore database '{DATABASE_ID}'...")

# Initialize the Firestore client targeting the specific database
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ==========================================
# MOCK DATA (TRANSLATED)
# ==========================================
# Using the stop name as the Document ID for direct lookups
mock_data = {
    # ----------------------------------------------------
    # A1 Autostrada del Sole (North to South)
    # ----------------------------------------------------
    "Somaglia Ovest": {
        "products": [
            {"product_name": "Apollo Sandwich", "quantity": 35},
            {"product_name": "Lombard Piadina", "quantity": 22},
            {"product_name": "Espresso Coffee", "quantity": 180},
            {"product_name": "Fruit Salad", "quantity": 14}
        ],
        "reviews": [
            "Quick pit stop right after Leaving Milan. Apollo sandwich was fresh.",
            "Plenty of seating and clean restrooms.",
            "Coffee line moves fast even during morning rush.",
            "Great selection of packaged local cheeses to take home."
        ]
    },
    "Fiorenzuola d'Arda": {
        "products": [
            {"product_name": "Camogli Sandwich", "quantity": 50},
            {"product_name": "Piacenza Mortadella Focaccia", "quantity": 30},
            {"product_name": "Gluten-Free Croissant", "quantity": 12},
            {"product_name": "Cappuccino", "quantity": 210}
        ],
        "reviews": [
            "Love the bridge structure spanning over the highway! Classic architecture.",
            "Mortadella focaccia was warm and generous with portion size.",
            "A bit noisy during lunchtime, but overall a great experience.",
            "Good gluten-free baked goods available at the dedicated counter."
        ]
    },
    "Secchia Ovest": {
        "products": [
            {"product_name": "Rustichella Sandwich", "quantity": 45},
            {"product_name": "Vegan Salad", "quantity": 12},
            {"product_name": "Espresso Coffee", "quantity": 200},
            {"product_name": "Balsamic Vinegar Glazed Panino", "quantity": 18}
        ],
        "reviews": [
            "The Rustichella was heated to perfection.",
            "The vegan salad was fresh and full of ingredients, I highly recommend it!",
            "The coffee was a bit burnt today, but the staff is always friendly.",
            "Great stop for anyone looking for vegan options on the highway."
        ]
    },
    "Cantagallo": {
        "products": [
            {"product_name": "Capri Sandwich", "quantity": 25},
            {"product_name": "Ligurian Focaccia", "quantity": 40},
            {"product_name": "Plain Croissant", "quantity": 50},
            {"product_name": "Bolognese Lasagna", "quantity": 15}
        ],
        "reviews": [
            "The focaccia was a bit hard and dry, maybe from yesterday.",
            "The Capri sandwich with mozzarella and tomato is my go-to stop.",
            "Very crowded place but fast service at the croissant counter.",
            "I love this station, the bakery products are excellent."
        ]
    },
    "Badia al Pino Est": {
        "products": [
            {"product_name": "Tuscan Prosciutto Panino", "quantity": 28},
            {"product_name": "Rustichella Sandwich", "quantity": 32},
            {"product_name": "Fresh Orange Juice", "quantity": 20},
            {"product_name": "Pistachio Croissant", "quantity": 35}
        ],
        "reviews": [
            "The Tuscan ham panino was incredible—real local flavors.",
            "Very clean facilities and friendly staff.",
            "Espresso machine was down briefly, but fixed fast.",
            "Pistachio croissant is a must-try!"
        ]
    },
    "Fabro Ovest": {
        "products": [
            {"product_name": "Bufalina Sandwich", "quantity": 22},
            {"product_name": "Wild Mushroom Risotto", "quantity": 10},
            {"product_name": "Gluten-Free Muffin", "quantity": 6},
            {"product_name": "Espresso Coffee", "quantity": 140}
        ],
        "reviews": [
            "Nice peaceful stop surrounded by Umbrian hills.",
            "Risotto at the self-service restaurant exceeded expectations.",
            "Restrooms were very clean.",
            "Limited vegan options, but good gluten-free pastries."
        ]
    },
    "Teano Ovest": {
        "products": [
            {"product_name": "Buffalo Mozzarella Ciabatta", "quantity": 40},
            {"product_name": "Neapolitan Sfogliatella", "quantity": 60},
            {"product_name": "Camogli Sandwich", "quantity": 20},
            {"product_name": "Espresso Coffee", "quantity": 250}
        ],
        "reviews": [
            "Best espresso on the A1 highway—authentic Southern roast!",
            "The warm sfogliatella pastry was divine.",
            "Buffalo mozzarella tasted incredibly fresh.",
            "Gets very crowded on summer weekends, budget extra time."
        ]
    },

    # ----------------------------------------------------
    # A8 / A4 Northern Belt & Lakes
    # ----------------------------------------------------
    "Villoresi Est": {
        "products": [
            {"product_name": "Ham and Lactose-Free Cheese Sandwich", "quantity": 15},
            {"product_name": "Rice Salad", "quantity": 20},
            {"product_name": "Gluten-Free Focaccia", "quantity": 10},
            {"product_name": "Local Charcuterie Board", "quantity": 12}
        ],
        "reviews": [
            "Finally a place with excellent gluten-free focaccia! Highly recommended for celiacs.",
            "The lactose-free sandwich was good, but the charcuterie board was the real star.",
            "Beautiful building (volcano-shaped!), and great options for my intolerances.",
            "Fast service, even though there was a long line at the counter."
        ]
    },
    "Villoresi Ovest": {
        "products": [
            {"product_name": "Milano Salami Panino", "quantity": 30},
            {"product_name": "Rustichella Sandwich", "quantity": 40},
            {"product_name": "Fresh Fruit Smoothie", "quantity": 18},
            {"product_name": "Cappuccino", "quantity": 160}
        ],
        "reviews": [
            "Classic 1950s modernist architecture—an icon of Italian highway design.",
            "Sandwiches were fresh and well-stocked.",
            "Easy access to high-speed EV chargers right outside.",
            "Staff at the bar area were exceptionally efficient."
        ]
    },
    "Brianza Nord": {
        "products": [
            {"product_name": "Apollo Sandwich", "quantity": 25},
            {"product_name": "Quinoa & Avocado Bowl", "quantity": 14},
            {"product_name": "Gluten-Free Toast", "quantity": 8},
            {"product_name": "Espresso Coffee", "quantity": 170}
        ],
        "reviews": [
            "Great healthy options like the avocado bowl.",
            "Spacious dining layout with plug points for laptops.",
            "A bit busy around 8 AM, but service was smooth.",
            "Clean bathrooms and helpful personnel."
        ]
    },
    "Novara Nord": {
        "products": [
            {"product_name": "Piedmontese Beef Panino", "quantity": 20},
            {"product_name": "Camogli Sandwich", "quantity": 35},
            {"product_name": "Chocolate Croissant", "quantity": 45},
            {"product_name": "Sparkling Water 50cl", "quantity": 120}
        ],
        "reviews": [
            "Beef panino was tasty and rich.",
            "Good stop when heading towards Turin or France.",
            "Ultra-fast chargers worked flawlessly.",
            "Clean facilities and good coffee quality."
        ]
    },
    "Scaligera Ovest": {
        "products": [
            {"product_name": "Verona Sopressa Sandwich", "quantity": 22},
            {"product_name": "Caprese Salad", "quantity": 16},
            {"product_name": "Plain Croissant", "quantity": 40},
            {"product_name": "Espresso Coffee", "quantity": 150}
        ],
        "reviews": [
            "Sopressa salami sandwich was excellent.",
            "Fresh ingredients in the Caprese salad.",
            "Plenty of parking space for trucks and cars.",
            "Bathrooms could use a bit more frequent cleaning during peak times."
        ]
    },

    # ----------------------------------------------------
    # Rome Ring (GRA) & Central Region
    # ----------------------------------------------------
    "Flaminia Est": {
        "products": [
            {"product_name": "Camogli Sandwich", "quantity": 30},
            {"product_name": "Fresh Orange Juice", "quantity": 15},
            {"product_name": "Gluten-Free Muffin", "quantity": 8}
        ],
        "reviews": [
            "The Camogli is a timeless classic, always good.",
            "Bad experience, there were no hot sandwiches available.",
            "Fantastic to find gluten-free options! The muffin was delicious.",
            "Fresh juice made on the spot, much appreciated."
        ]
    },
    "Casilina Interna": {
        "products": [
            {"product_name": "Porchetta di Ariccia Panino", "quantity": 35},
            {"product_name": "Rustichella Sandwich", "quantity": 25},
            {"product_name": "Maritozzo with Cream", "quantity": 30},
            {"product_name": "Espresso Coffee", "quantity": 190}
        ],
        "reviews": [
            "The Porchetta sandwich is absolute perfection!",
            "Super convenient stop on the Rome ring road.",
            "Maritozzo was soft, fresh, and filled with real cream.",
            "Can get very crowded during weekday commuter hours."
        ]
    },
    "Feronia Est": {
        "products": [
            {"product_name": "Bufalina Sandwich", "quantity": 28},
            {"product_name": "Caesar Salad", "quantity": 15},
            {"product_name": "Vegan Croissant", "quantity": 10},
            {"product_name": "Cappuccino", "quantity": 140}
        ],
        "reviews": [
            "Clean, modern interior layout.",
            "Vegan croissant tasted just as good as a regular one.",
            "Friendly cashiers and fast ordering counter.",
            "Good EV charging station availability."
        ]
    },
    "La Macchia Ovest": {
        "products": [
            {"product_name": "Ciociaria Ham Panino", "quantity": 20},
            {"product_name": "Apollo Sandwich", "quantity": 30},
            {"product_name": "Fresh Orange Juice", "quantity": 18},
            {"product_name": "Espresso Coffee", "quantity": 160}
        ],
        "reviews": [
            "Great stop halfway between Rome and Naples.",
            "Orange juice maker was freshly replenished.",
            "Sandwich bread was soft and properly toasted.",
            "Bathrooms were sparkling clean."
        ]
    },

    # ----------------------------------------------------
    # A14 Adriatic Coast
    # ----------------------------------------------------
    "Sillaro Ovest": {
        "products": [
            {"product_name": "Romagna Piadina (Squacquerone & Rocket)", "quantity": 45},
            {"product_name": "Rustichella Sandwich", "quantity": 30},
            {"product_name": "Fruit Bowl", "quantity": 12},
            {"product_name": "Espresso Coffee", "quantity": 175}
        ],
        "reviews": [
            "Hands down the best piadina on the entire Adriatic highway network!",
            "Squacquerone cheese was warm and creamy.",
            "Quick service despite a long line at noon.",
            "Spacious outdoor seating area available."
        ]
    },
    "Rubicone Est": {
        "products": [
            {"product_name": "Romagna Piadina Ham & Cheese", "quantity": 40},
            {"product_name": "Camogli Sandwich", "quantity": 22},
            {"product_name": "Gluten-Free Cookie", "quantity": 15},
            {"product_name": "Cappuccino", "quantity": 130}
        ],
        "reviews": [
            "Classic Romagna hospitality from the counter staff.",
            "Piadina prepared right in front of you.",
            "Clean and tidy restrooms.",
            "Good range of regional wine and food souvenirs."
        ]
    },
    "Esino Est": {
        "products": [
            {"product_name": "Marche Porchetta Sandwich", "quantity": 25},
            {"product_name": "Capri Sandwich", "quantity": 20},
            {"product_name": "Plain Croissant", "quantity": 35},
            {"product_name": "Espresso Coffee", "quantity": 145}
        ],
        "reviews": [
            "Crispy skin on the porchetta panino—delicious!",
            "Decent coffee, fast service.",
            "Convenient location before hitting the Ancona ports.",
            "Restroom turnstiles accept contactless card payments."
        ]
    },
    "Tower Torre Cerrano East": {
        "products": [
            {"product_name": "Abruzzo Pecorino & Salame Panino", "quantity": 24},
            {"product_name": "Rustichella Sandwich", "quantity": 35},
            {"product_name": "Fresh Orange Juice", "quantity": 16},
            {"product_name": "Espresso Coffee", "quantity": 180}
        ],
        "reviews": [
            "Stunning ocean view from the dining windows!",
            "Pecorino sandwich had great local flavor.",
            "Modern service tower bridging across the highway.",
            "Great spot to take a relaxing 20-minute break."
        ]
    },

    # ----------------------------------------------------
    # South & Islands (A2 / A18)
    # ----------------------------------------------------
    "Salerno Nord": {
        "products": [
            {"product_name": "Campanian Mozzarella Ciabatta", "quantity": 38},
            {"product_name": "Babà Pastry", "quantity": 25},
            {"product_name": "Apollo Sandwich", "quantity": 18},
            {"product_name": "Espresso Coffee", "quantity": 230}
        ],
        "reviews": [
            "The Babà was soaked in rum just right—authentic local pastry!",
            "Fresh mozzarella made all the difference in the ciabatta.",
            "Coffee strong and hot, perfect pick-me-up for long drives.",
            "Busy location near the Amalfi coast exit."
        ]
    },
    "Campotenese Ovest": {
        "products": [
            {"product_name": "Calabrian Nduja & Cheese Panino", "quantity": 20},
            {"product_name": "Camogli Sandwich", "quantity": 15},
            {"product_name": "Gluten-Free Rice Crisp", "quantity": 10},
            {"product_name": "Espresso Coffee", "quantity": 110}
        ],
        "reviews": [
            "Spicy Nduja panino woke me up better than coffee!",
            "High altitude mountain feel, cooler air outside.",
            "Quiet and relaxed stop along the A2 highway.",
            "Friendly staff and prompt service."
        ]
    },
    "Lamezia Ovest": {
        "products": [
            {"product_name": "Spicy Soppressata Panino", "quantity": 26},
            {"product_name": "Rustichella Sandwich", "quantity": 28},
            {"product_name": "Bergamot Iced Tea", "quantity": 22},
            {"product_name": "Espresso Coffee", "quantity": 165}
        ],
        "reviews": [
            "Bergamot tea was unique and refreshing.",
            "Good selection of Calabrian regional products to buy.",
            "Clean facilities and short wait times.",
            "High-speed chargers available in the parking area."
        ]
    },
    "Aci Sant'Antonio Ovest": {
        "products": [
            {"product_name": "Sicilian Cannolo", "quantity": 50},
            {"product_name": "Arancino with Meat Ragù", "quantity": 40},
            {"product_name": "Capri Sandwich", "quantity": 15},
            {"product_name": "Espresso Coffee", "quantity": 220}
        ],
        "reviews": [
            "Cannolo filled fresh right when you order! Unbelievable quality for a highway stop.",
            "Crispy Arancino with rich ragù filling.",
            "Stunning view of Mount Etna in the background.",
            "Can get crowded with tourists, but line moves fast."
        ]
    },
    "Gelso Bianco Nord": {
        "products": [
            {"product_name": "Sicilian Pistachio Cannolo", "quantity": 45},
            {"product_name": "Pistachio Croissant", "quantity": 35},
            {"product_name": "Catania Tomato & Mozzarella Focaccia", "quantity": 25},
            {"product_name": "Granita with Brioche", "quantity": 30}
        ],
        "reviews": [
            "The almond granita with warm brioche is heavenly in the summer heat.",
            "Pistachio cream in the croissant is top notch.",
            "Spacious and clean station near Catania.",
            "Excellent selection of Sicilian sweets."
        ]
    }
}

# ==========================================
# EXECUTION
# ==========================================
def seed_database():
    print(f"Populating collection '{COLLECTION_NAME}'...")
    
    # Get a reference to the collection
    collection_ref = db.collection(COLLECTION_NAME)
    
    success_count = 0
    for stop_name, data in mock_data.items():
        try:
            # Using the stop_name as the Document ID
            doc_ref = collection_ref.document(stop_name)
            
            # Prepare payload
            payload = {
                "stop_name": stop_name,
                "products": data["products"],
                "reviews": data["reviews"]
            }
            
            doc_ref.set(payload)
            print(f"  -> Inserted data for: {stop_name}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Failed to insert data for {stop_name}: {e}")
            
    print(f"✅ Successfully seeded {success_count} documents into Firestore!")

if __name__ == "__main__":
    seed_database()