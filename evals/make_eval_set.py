"""Generates eval_set.json (30 questions with gold SQL). Run once: python evals/make_eval_set.py"""
import json

E, M, H, T = "easy", "medium", "hard", "trap"
CAT_JOIN = ("FROM order_items i JOIN products p ON i.product_id = p.product_id "
            "JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name")

items = [
    # ---- easy (10) ----
    (E, "number", "How many orders are there in total?", "SELECT COUNT(*) FROM orders"),
    (E, "number", "How many unique customers are there? Count real people using customer_unique_id.",
     "SELECT COUNT(DISTINCT customer_unique_id) FROM customers"),
    (E, "number", "How many sellers are there?", "SELECT COUNT(*) FROM sellers"),
    (E, "number", "How many products are in the products table?", "SELECT COUNT(*) FROM products"),
    (E, "number", "How many orders have the status canceled?",
     "SELECT COUNT(*) FROM orders WHERE order_status = 'canceled'"),
    (E, "number", "What is the average price of an order item? Round to 2 decimals.",
     "SELECT AVG(price) FROM order_items"),
    (E, "number", "What is the total freight_value across all order items? Round to 2 decimals.",
     "SELECT SUM(freight_value) FROM order_items"),
    (E, "number", "What is the highest price of any single order item?", "SELECT MAX(price) FROM order_items"),
    (E, "number", "How many different payment types exist?",
     "SELECT COUNT(DISTINCT payment_type) FROM order_payments"),
    (E, "text", "Which order_status is the most common in the orders table?",
     "SELECT order_status FROM orders GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"),
    # ---- medium (10) ----
    (M, "text", "Which customer_state has the most customers (count customer_id rows)?",
     "SELECT customer_state FROM customers GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"),
    (M, "list", "What are the top 5 customer states by number of customers (count customer_id rows)?",
     "SELECT customer_state FROM customers GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 5"),
    (M, "text", "Which payment type is used most often, by number of payments?",
     "SELECT payment_type FROM order_payments GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"),
    (M, "number", "What is the average payment_value of credit_card payments? Round to 2 decimals.",
     "SELECT AVG(payment_value) FROM order_payments WHERE payment_type = 'credit_card'"),
    (M, "number", "How many orders were placed in 2017 (by order_purchase_timestamp)?",
     "SELECT COUNT(*) FROM orders WHERE strftime('%Y', order_purchase_timestamp) = '2017'"),
    (M, "text", "In which year were the most orders placed (by order_purchase_timestamp)?",
     "SELECT strftime('%Y', order_purchase_timestamp) FROM orders GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"),
    (M, "number", "How many orders have the status delivered?",
     "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered'"),
    (M, "text", "Which seller_state has the most sellers?",
     "SELECT seller_state FROM sellers GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"),
    (M, "number", "On average, how many items are in an order (order_items rows divided by distinct orders)? Round to 2 decimals.",
     "SELECT 1.0 * COUNT(*) / COUNT(DISTINCT order_id) FROM order_items"),
    (M, "number", "How many payments have more than 10 installments?",
     "SELECT COUNT(*) FROM order_payments WHERE payment_installments > 10"),
    # ---- hard (5) ----
    (H, "list", "What are the top 5 product categories by number of items sold? Use the exact English category names from the data.",
     f"SELECT t.product_category_name_english {CAT_JOIN} GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 5"),
    (H, "number", "What is the total revenue (sum of price) for the English category health_beauty? Round to 2 decimals.",
     f"SELECT SUM(i.price) {CAT_JOIN} WHERE t.product_category_name_english = 'health_beauty'"),
    (H, "number", "What percentage of all orders have the status delivered? Round to 2 decimals.",
     "SELECT 100.0 * SUM(order_status = 'delivered') / COUNT(*) FROM orders"),
    (H, "number", "What is the average delivery time in days from order_purchase_timestamp to order_delivered_customer_date, for delivered orders only? Round to 1 decimal.",
     "SELECT AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)) "
     "FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL"),
    (H, "text", "Which customer_state generates the most total payment_value?",
     "SELECT c.customer_state FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
     "JOIN order_payments p ON o.order_id = p.order_id GROUP BY 1 ORDER BY SUM(p.payment_value) DESC LIMIT 1"),
    # ---- trap: the data cannot answer these (5) ----
    (T, "refusal", "What is the profit margin for each product category?", ""),
    (T, "refusal", "What is the average age of the customers?", ""),
    (T, "refusal", "Which products have the highest return rate?", ""),
    (T, "refusal", "What is the gender split of the customers?", ""),
    (T, "refusal", "How much revenue came from each marketing campaign?", ""),
]

out = [{"id": n + 1, "group": g, "type": ty, "question": q, "gold_sql": sql}
       for n, (g, ty, q, sql) in enumerate(items)]
json.dump(out, open("evals/eval_set.json", "w"), indent=2)
print(len(out), "questions written to evals/eval_set.json")
