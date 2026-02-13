"""Explicit Supabase select column lists.

Keeping these constants centralized avoids accidental `select("*")` usage and
makes query payloads easier to reason about.
"""

RECIPE_SELECT_COLUMNS = (
    "id,title,description,image_url,cooking_time_minutes,difficulty,servings,"
    "ingredients,instructions,priority_score,is_favorite,created_at,updated_at"
)

INVENTORY_SELECT_COLUMNS = (
    "id,device_id,name,quantity,unit,category,expiry_date,image_url,created_at,updated_at"
)

FAVORITE_RECIPE_SELECT_COLUMNS = "id,device_id,recipe_id,title,recipe_data,created_at"

COOKING_HISTORY_SELECT_COLUMNS = "id,device_id,recipe_id,recipe_title,servings,deducted_items,cooked_at"

SCAN_SELECT_COLUMNS = "id,device_id,source_type,status,original_filename,items,raw_text,error_message,created_at,updated_at"

NOTIFICATION_SELECT_COLUMNS = "id,device_id,type,title,message,metadata,is_read,read_at,created_at"

SHOPPING_ITEM_SELECT_COLUMNS = (
    "id,device_id,name,quantity,unit,status,source,recipe_id,recipe_title,"
    "added_to_inventory,purchased_at,created_at,updated_at"
)

INVENTORY_LOG_SELECT_COLUMNS = "id,device_id,item_name,action,quantity_change,metadata,created_at"

PRICE_HISTORY_SELECT_COLUMNS = "id,device_id,scan_id,item_name,unit_price,currency,store_name,purchased_on,source_type,created_at"
