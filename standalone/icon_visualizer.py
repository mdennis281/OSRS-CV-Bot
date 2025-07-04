import json
import base64
from pathlib import Path
from flask import Flask, render_template_string, send_file, request
from io import BytesIO

app = Flask(__name__)

# Load the JSON data
ICONS_PATH = Path(__file__).resolve().parent.parent / "data" / "items" / "icons-items-complete.json"
ITEMS_PATH = Path(__file__).resolve().parent.parent / "data" / "items" / "items-cache-data.json"

with ICONS_PATH.open("r") as f:
    ICONS = json.load(f)

with ITEMS_PATH.open("r") as f:
    ITEMS = json.load(f)

# Route to display an individual icon
@app.route("/icon/<int:item_id>")
def get_icon(item_id):
    if str(item_id) in ICONS:
        image_data = base64.b64decode(ICONS[str(item_id)])
        return send_file(BytesIO(image_data), mimetype='image/png')
    return "Icon not found", 404

# Route to display item details
@app.route("/item/<int:item_id>")
def item_detail(item_id):
    item = ITEMS.get(str(item_id))
    if not item:
        return "Item not found", 404
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ item['name'] }}</title>
        <style>
            body { font-family: Arial, sans-serif; background: #222; color: #fff; text-align: center; }
            .container { margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>{{ item['name'] }}</h1>
        <img src="/icon/{{ item['id'] }}" alt="{{ item['name'] }}">
        <p><strong>Tradeable:</strong> {{ 'Yes' if item['tradeable_on_ge'] else 'No' }}</p>
        <p><strong>Members Only:</strong> {{ 'Yes' if item['members'] else 'No' }}</p>
        <p><strong>Cost:</strong> {{ item['cost'] }}</p>
        <p><strong>Low Alch:</strong> {{ item['lowalch'] }}</p>
        <p><strong>High Alch:</strong> {{ item['highalch'] }}</p>
    </body>
    </html>
    """
    return render_template_string(html_template, item=item)

# Route to display all icons with search, filters, and pagination
@app.route("/")
def index():
    search_query = request.args.get("search", "").lower()
    page = int(request.args.get("page", 1))
    per_page = 50
    
    filtered_items = [item for item in ITEMS.values() if search_query in item["name"].lower()]
    total_pages = (len(filtered_items) + per_page - 1) // per_page
    paginated_items = filtered_items[(page - 1) * per_page: page * per_page]
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OSRSBox Icons</title>
        <style>
            body { font-family: Arial, sans-serif; background: #222; color: #fff; text-align: center; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 10px; padding: 20px; }
            .grid img { width: 64px; height: 64px; background: #333; padding: 5px; border-radius: 5px; }
            .grid div { text-align: center; font-size: 12px; }
            input { margin: 5px; padding: 10px; background: #333; color: #fff; border: 1px solid #555; border-radius: 5px; }
            .pagination { margin-top: 20px; }
            .pagination a { margin: 5px; padding: 10px; background: #555; color: #fff; text-decoration: none; border-radius: 5px; }
            .pagination a:hover { background: #777; }
        </style>
        <script>
            function updateSearch() {
                let query = document.getElementById('search').value;
                window.location.href = `/?search=${query}`;
            }
        </script>
    </head>
    <body>
        <h1>OSRSBox Icons</h1>
        <input type="text" id="search" placeholder="Search by name" onkeyup="updateSearch()" value="{{ request.args.get('search', '') }}">
        <div class="grid">
            {% for item in items %}
                <div>
                    <a href="/item/{{ item['id'] }}">
                        <img src="/icon/{{ item['id'] }}" alt="{{ item['name'] }}">
                    </a>
                    <p>{{ item['name'] }}</p>
                </div>
            {% endfor %}
        </div>
        <div class="pagination">
            {% if page > 1 %}
                <a href="/?search={{ search_query }}&page={{ page-1 }}">Previous</a>
            {% endif %}
            {% if page < total_pages %}
                <a href="/?search={{ search_query }}&page={{ page+1 }}">Next</a>
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, items=paginated_items, search_query=search_query, page=page, total_pages=total_pages)

if __name__ == "__main__":
    app.run(debug=True)