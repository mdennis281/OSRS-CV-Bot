
import requests
import json

BASE_URL = "http://services.runescape.com/m=itemdb_oldschool/api/catalogue/"
ITEM_DETAIL_URL = BASE_URL + "detail.json?item={}"

# # Example: Fetch item details for an item ID
# def get_item_icon(item_id):
#     response = requests.get(ITEM_DETAIL_URL.format(item_id))
#     if response.status_code == 200:
#         data = response.json()
#         return data.get("item", {}).get("icon")
#     return None

# # Example usage:
# item_id = 4151  # Abyssal Whip
# icon_url = get_item_icon(item_id)
# print(f"Item {item_id}: {icon_url}")


def get_all_items():
    all_items = {}
    for category in range(40):  # OSRS has ~40 item categories
        for letter in "abcdefghijklmnopqrstuvwxyz":
            try:
                url = f"{BASE_URL}items.json?category={category}&alpha={letter}&page=1"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        all_items[item["id"]] = item["icon"]
            except Exception as e:
                print(f"Error fetching category {category}, letter {letter}: {e}")
            with open('out.json', 'w') as f:
                json.dump(all_items, f, indent=4)
            print(len(all_items), 'items saved.')
                
    return all_items

all_item_images = get_all_items()
print(json.dumps(all_item_images, indent=4))
