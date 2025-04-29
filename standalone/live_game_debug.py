from flask import Flask, render_template_string, jsonify
import requests
import threading
import time
from core.item_db import ItemLookup

app = Flask(__name__)
item_lookup = ItemLookup()

data_cache = {
    "inventory": [],
    "equipment": [],
    "stats": []
}

def fetch_data():
    """Background thread to fetch live data."""
    while True:
        try:
            data_cache["equipment"] = requests.get("http://localhost:8080/equip").json()
            data_cache["inventory"] = requests.get("http://localhost:8080/inv").json()
            data_cache["stats"] = requests.get("http://localhost:8080/stats").json()
        except Exception as e:
            print(f"Error fetching data: {e}")
        time.sleep(1)

@app.route("/api/data")
def api_data():
    """API endpoint to serve live data to the UI."""
    return jsonify(data_cache)

@app.route("/")
def index():
    """Serve the main page."""
    items = {
        item.id: {"name": item.name, "icon_b64": item.icon_b64}
        for item in item_lookup._items_by_id.values()
    }

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OSRS Player Dashboard</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background-color: #1e1e2e;
                color: #ffffff;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .container {
                max-width: 1800px;
                width: 100%;
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 20px;
                padding: 20px;
                flex-wrap: wrap;
            }
            .section {
                flex: 1;
                min-width: 300px;
                background-color: #28293e;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                text-align: center;
            }
            .section h2 {
                margin-top: 0;
                color: #0d6efd;
            }
            .grid {
                display: grid;
                gap: 5px;
            }
            .inventory {
                grid-template-columns: repeat(4, 64px);
                justify-content: center;
            }
            .equipment {
                display: block;
            }
            .equipment .row {
                display: flex;
                justify-content: center;
                gap: 10px;
            }

            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
                gap: 10px;
                text-align: center;
            }
            .item {
                position: relative;
                width: 64px;
                height: 64px;
                background-color: #3a3b59;
                border: 1px solid #5a5c8a;
                border-radius: 4px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .item img {
                max-width: 100%;
                max-height: 100%;
                z-index: 2;
            }
            .item .quantity {
                position: absolute;
                top: 2px;
                left: 2px;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                font-size: 10px;
                padding: 2px 4px;
                border-radius: 3px;
            }
            .item .title {
                position: absolute;
                bottom: 2px;
                margin: auto;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                font-size: 8px;
                padding: 2px 4px;
                line-height: 1;
                border-radius: 3px;
            }
            .stats-item {
                background-color: #3a3b59;
                padding: 10px;
                border-radius: 4px;
                border: 1px solid #5a5c8a;
            }
            .stats-item .level {
                font-size: 16px;
                font-weight: bold;
                color: #0d6efd;
            }
            .stats-item .boosted-level {
                font-size: 12px;
                color: #ffffff;
            }
            .stats-item .name {
                margin-top: 5px;
                font-size: 12px;
                color: #cfcfcf;
            }
            @media (max-width: 800px) {
                .container {
                    flex-direction: column;
                    align-items: center;
                }
                .section {
                    width: 100%;
                }
            }
        </style>
        <script>
            const items = {{ items|tojson }};

            async function fetchData() {
                const response = await fetch('/api/data');
                const data = await response.json();

                // Update inventory
                const inventoryContainer = document.querySelector('.inventory');
                inventoryContainer.innerHTML = '';
                data.inventory.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'item';
                    if (item.id > 0 && items[item.id]) {
                        div.innerHTML = `
                            <span class="quantity">${item.quantity}</span>
                            <img src="data:image/png;base64,${items[item.id].icon_b64}" alt="${items[item.id].name}">
                            <span class="title">${items[item.id].name}</span>
                        `;
                    } else {
                        div.textContent = '';
                    }
                    inventoryContainer.appendChild(div);
                });

                // Update equipment
                const equipmentContainer = document.querySelector('.equipment');
                equipmentContainer.innerHTML = '';
                let i = 0;
                let equipItems = [];
                data.equipment.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'item';
                    if (item.id > 0 && items[item.id]) {
                        div.innerHTML = `
                            <span class="quantity">${item.quantity}</span>
                            <img src="data:image/png;base64,${items[item.id].icon_b64}" alt="${items[item.id].name}">
                            <span class="title">${items[item.id].name}</span>
                        `;
                    } else {
                        div.textContent = '?';
                    }
                    
                    equipItems.push(div);
                    i++;
                });
                console.log(equipItems);
                let row1 = document.createElement('div');
                row1.className = 'row';
                row1.appendChild(equipItems[0]);

                let row2 = document.createElement('div');
                row2.className = 'row';
                row2.appendChild(equipItems[1]);
                row2.appendChild(equipItems[2]);
                row2.appendChild(equipItems[13]);

                let row3 = document.createElement('div');
                row3.className = 'row';
                row3.appendChild(equipItems[3]);
                row3.appendChild(equipItems[4]);
                row3.appendChild(equipItems[5]);

                let row4 = document.createElement('div');
                row4.className = 'row';
                row4.appendChild(equipItems[7]);

                let row5 = document.createElement('div');
                row5.className = 'row';
                row5.appendChild(equipItems[9]);
                row5.appendChild(equipItems[10]);
                row5.appendChild(equipItems[12]);

                let row6 = document.createElement('div');
                row6.className = 'row';
                row6.appendChild(equipItems[8]);
                row6.appendChild(equipItems[6]);
                row6.appendChild(equipItems[11]);

                equipmentContainer.appendChild(row1);
                equipmentContainer.appendChild(row2);
                equipmentContainer.appendChild(row3);
                equipmentContainer.appendChild(row4);
                equipmentContainer.appendChild(row5);
                equipmentContainer.appendChild(row6);

                

                // Update stats
                const statsGrid = document.querySelector('.stats-grid');
                statsGrid.innerHTML = '';
                data.stats.forEach(stat => {
                    const div = document.createElement('div');
                    div.className = 'stats-item';
                    div.innerHTML = `
                        <div class="level">${stat.level}</div>
                        <div class="boosted-level">${stat.boostedLevel}</div>
                        <div class="name">${stat.stat}</div>
                    `;
                    statsGrid.appendChild(div);
                });
            }

            setInterval(fetchData, 1000);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="section">
                <h2>Equipment</h2>
                <div class="grid equipment"></div>
            </div>
            <div class="section">
                <h2>Inventory</h2>
                <div class="grid inventory"></div>
            </div>
            <div class="section">
                <h2>Stats</h2>
                <div class="stats-grid"></div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, items=items)

if __name__ == "__main__":
    # Start the background thread to fetch data
    thread = threading.Thread(target=fetch_data, daemon=True)
    thread.start()

    app.run(debug=True)
